"""Create audio/<date>.mp3 for every lesson that has none, with a natural Greek voice.
Tries Microsoft's neural voice (edge-tts) first, then Google's voice (gTTS).
Runs in GitHub Actions (needs internet). Usage: python3 tools/make_audio.py
"""
import asyncio, json, os, re, sys, traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RX = re.compile(r"\*\*(.+?)\*\*\s*\((.+?)\)")

def with_edge(text, out):
    import edge_tts
    asyncio.run(edge_tts.Communicate(text, "el-GR-AthinaNeural", rate="-10%").save(out))

def with_google(text, out):
    from gtts import gTTS
    gTTS(text, lang="el").save(out)

def main():
    lessons = json.load(open(os.path.join(ROOT, "lessons.json"), encoding="utf-8"))
    os.makedirs(os.path.join(ROOT, "audio"), exist_ok=True)
    failed = False
    for s in lessons:
        out = os.path.join(ROOT, "audio", s["date"] + ".mp3")
        if os.path.exists(out):
            continue
        text = s["title"] + ".\n\n" + "\n\n".join(RX.sub(r"\1", p) for p in s["paragraphs"])
        for name, fn in (("edge", with_edge), ("google", with_google)):
            try:
                fn(text, out)
                if os.path.getsize(out) > 1000:
                    print(f"audio créé ({name}) :", out)
                    break
                raise RuntimeError("fichier vide")
            except Exception:
                print(f"échec {name} pour {s['date']} :", file=sys.stderr)
                traceback.print_exc()
                if os.path.exists(out):
                    os.remove(out)
        else:
            failed = True
    sys.exit(1 if failed else 0)

main()
