"""Record Ava (en-US-AvaNeural) clips for one word list in index.html.

usage: python tools/gen_audio.py index.html audio/<list-folder> <JS_ARRAY_NAME>
Makes w/ (word), slow/ (slow word), d/ (definition), s/ (sentence) clips named by row index.
MAIN_WORDS also makes the shared letter / intro / retry clips in audio/.
Existing clips are skipped, so it is safe to re-run.
"""
import asyncio, json, os, sys
import edge_tts

SRC = sys.argv[1]
OUT = sys.argv[2]
NAME = sys.argv[3] if len(sys.argv) > 3 else "MAIN_WORDS"
EXTRAS = NAME == "MAIN_WORDS"
VOICE = "en-US-AvaNeural"
SAY = {"lead": "leed", "live": "liv", "DNA": "D. N. A."}   # pronounce the intended word

html = open(SRC, encoding="utf-8").read()
rows = []
for line in html.split(f"const {NAME} = [", 1)[1].splitlines()[1:]:
    s = line.strip()
    if s.startswith("]"):
        break
    if s.startswith('["'):
        rows.append(json.loads(s.rstrip(",")))
print(len(rows), "words")

jobs = []
for i, row in enumerate(rows):
    w, d, s = row[:3]                 # 4th element marks vocabulary words
    n = f"{i:03d}"
    spoken = SAY.get(w, w)
    jobs += [(f"w/{n}.mp3", spoken + ".", "-5%"),
             (f"slow/{n}.mp3", spoken + ".", "-45%"),
             (f"d/{n}.mp3", d, "-5%"),
             (f"s/{n}.mp3", s, "-5%")]
if EXTRAS:
    for c in "abcdefghijklmnopqrstuvwxyz":
        jobs.append((f"letters/{c}.mp3", c.upper() + ".", "-5%"))
    jobs.append(("letters/enye.mp3", "N with a tilde.", "-5%"))
    jobs.append(("intro.mp3", "Your word is:", "-5%"))
    jobs.append(("listen.mp3", "Spell it out loud.", "-5%"))
    jobs.append(("retry.mp3", "Now you spell it.", "-5%"))

sem = asyncio.Semaphore(6)
async def one(path, text, rate):
    dest = os.path.join(OUT, path)
    if os.path.exists(dest) and os.path.getsize(dest) > 1000:
        return
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    async with sem:
        for attempt in range(4):
            try:
                await edge_tts.Communicate(text, VOICE, rate=rate).save(dest)
                return
            except Exception:
                await asyncio.sleep(2 * (attempt + 1))
        print("FAILED", path)

async def main():
    await asyncio.gather(*(one(*j) for j in jobs))
asyncio.run(main())
print("done", len(jobs))
