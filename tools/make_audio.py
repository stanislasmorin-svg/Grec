"""Create audio/<date>.mp3 for every lesson that has none, with a natural Greek voice (edge-tts).
Runs in GitHub Actions (needs internet). Usage: python3 tools/make_audio.py
"""
import asyncio, json, os, re
import edge_tts

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RX = re.compile(r"\*\*(.+?)\*\*\s*\((.+?)\)")
VOICE = "el-GR-AthinaNeural"

async def main():
    lessons = json.load(open(os.path.join(ROOT, "lessons.json"), encoding="utf-8"))
    os.makedirs(os.path.join(ROOT, "audio"), exist_ok=True)
    for s in lessons:
        out = os.path.join(ROOT, "audio", s["date"] + ".mp3")
        if os.path.exists(out):
            continue
        text = s["title"] + ".\n\n" + "\n\n".join(RX.sub(r"\1", p) for p in s["paragraphs"])
        await edge_tts.Communicate(text, VOICE, rate="-10%").save(out)
        print("audio créé :", out)

asyncio.run(main())
