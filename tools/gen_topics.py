"""Record Ava clips for every topic in index.html (study cards, quiz questions, explanations).

usage: python tools/gen_topics.py index.html audio/topics
Clips: audio/topics/<topic-id>/c000.mp3 (card), q000.mp3 (question), e000.mp3 (explanation).
A card's optional 3rd element is its spoken version (for symbols like > or −).
Math topics generate their problems in the app, so only their cards are recorded.
Existing clips are skipped — delete a topic's folder to re-record it after editing its text.
"""
import asyncio, json, os, re, sys
import edge_tts

SRC, OUT = sys.argv[1], sys.argv[2]
VOICE = "en-US-AvaNeural"

html = open(SRC, encoding="utf-8").read()
blob = html.split("const TOPICS = ", 1)[1].split("// END TOPICS", 1)[0].strip().rstrip(";")
topics = json.loads(blob)

def speakable(q):
    q = re.sub(r"_{2,}", "blank", q)
    return q.replace("LORD", "Lord")          # all-caps would be spelled out

jobs = []
for t in topics:
    d = t["id"]
    for i, card in enumerate(t["cards"]):
        spoken = card[2] if len(card) > 2 else f"{card[0]}. {card[1]}"
        jobs.append((f"{d}/c{i:03d}.mp3", speakable(spoken)))
    for i, q in enumerate(t.get("quiz", [])):
        jobs.append((f"{d}/q{i:03d}.mp3", speakable(q[0])))
        jobs.append((f"{d}/e{i:03d}.mp3", speakable(q[3])))
print(len(topics), "topics,", len(jobs), "clips")

sem = asyncio.Semaphore(6)
async def one(path, text):
    dest = os.path.join(OUT, path)
    if os.path.exists(dest) and os.path.getsize(dest) > 1000:
        return
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    async with sem:
        for attempt in range(4):
            try:
                await edge_tts.Communicate(text, VOICE, rate="-5%").save(dest)
                return
            except Exception:
                await asyncio.sleep(2 * (attempt + 1))
        print("FAILED", path)

async def main():
    await asyncio.gather(*(one(*j) for j in jobs))
asyncio.run(main())
print("done")
