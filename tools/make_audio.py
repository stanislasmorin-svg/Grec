"""Create the missing MP3 files, with a natural voice, for every language in build.LANGS:
- <dossier de la langue>/audio/<date>.mp3 : le texte du cours ;
- <dossier de la langue>/audio/ex/<hash>.mp3 : chaque phrase d'exemple, précédée d'1 s de souffle inaudible
  (sinon on n'entend pas le début sur certains téléphones / casques).
Tries Microsoft's neural voice (edge-tts) first, then Google's voice (gTTS). Silence is added with ffmpeg.
Runs in GitHub Actions (needs internet). Usage: python3 tools/make_audio.py
"""
import asyncio, json, os, re, subprocess, sys, tempfile, traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build import LANGS, ROOT, ex_audio_name

RX = re.compile(r"\*\*(.+?)\*\*\s*\((.+?)\)")
SEM = None

async def speak(text, out, L, rate):
    async with SEM:
        try:
            import edge_tts
            await edge_tts.Communicate(text, L["voice"], rate=rate).save(out)
            if os.path.getsize(out) > 1000:
                return "edge"
        except Exception:
            print(f"échec edge : {text[:40]}", file=sys.stderr); traceback.print_exc()
        try:
            from gtts import gTTS
            await asyncio.to_thread(lambda: gTTS(text, lang=L["gtts"]).save(out))
            if os.path.getsize(out) > 1000:
                return "google"
        except Exception:
            print(f"échec google : {text[:40]}", file=sys.stderr); traceback.print_exc()
        if os.path.exists(out):
            os.remove(out)
        return None

def add_silence(src, dst):
    # 1 s d'amorce avant la phrase. Ce n'est pas un silence parfait mais un souffle très faible (-60 dB,
    # inaudible) : beaucoup de téléphones et de casques Bluetooth restent en veille pendant un silence
    # numérique pur et coupent alors la première syllabe.
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", src,
                    "-f", "lavfi", "-i", "anoisesrc=r=24000:c=pink:a=0.001",
                    "-filter_complex",
                    "[0:a]aresample=24000,aformat=channel_layouts=mono,adelay=1000:all=1[v];"
                    "[1:a]aformat=channel_layouts=mono,atrim=0:1.2[n];"
                    "[v][n]amix=inputs=2:duration=first:normalize=0",
                    "-ac", "1", "-b:a", "64k", dst], check=True)

async def example(text, dst, L, tmpdir, stats):
    raw = os.path.join(tmpdir, os.path.basename(dst))
    if await speak(text, raw, L, "-10%"):
        try:
            await asyncio.to_thread(add_silence, raw, dst)
            stats["ex"] += 1
            return
        except Exception:
            traceback.print_exc()
    stats["ex_fail"] += 1

async def main():
    global SEM
    SEM = asyncio.Semaphore(6)
    failed = False
    for lang, L in LANGS.items():
        path = os.path.join(ROOT, L["file"])
        if not os.path.exists(path):
            continue
        lessons = json.load(open(path, encoding="utf-8"))
        outdir = os.path.join(ROOT, L["out"], "audio")
        os.makedirs(os.path.join(outdir, "ex"), exist_ok=True)
        # 1. texte du cours
        for s in lessons:
            out = os.path.join(outdir, s["date"] + ".mp3")
            if os.path.exists(out):
                continue
            text = s["title"] + ".\n\n" + "\n\n".join(RX.sub(r"\1", p) for p in s["paragraphs"])
            who = await speak(text, out, L, "-10%")
            print(f"audio {'créé (' + who + ')' if who else 'ÉCHEC'} :", out)
            failed |= not who
        # 2. phrases d'exemple (avec 1 s de silence au début)
        stats = {"ex": 0, "ex_fail": 0}
        jobs, seen = [], set()
        with tempfile.TemporaryDirectory() as tmpdir:
            for s in lessons:
                for pairs in s.get("examples", {}).values():
                    for p in pairs:
                        if not p or not p[0].strip():
                            continue
                        dst = os.path.join(outdir, "ex", ex_audio_name(lang, p[0]))
                        if os.path.exists(dst) or dst in seen:
                            continue
                        seen.add(dst)
                        jobs.append(example(p[0], dst, L, tmpdir, stats))
            await asyncio.gather(*jobs)
        print(f"{lang} : {stats['ex']} phrase(s) d'exemple créée(s), {stats['ex_fail']} échec(s)")
    sys.exit(1 if failed else 0)

asyncio.run(main())
