#!/usr/bin/env python3
"""import-render.py: bring a render from the home Mac back into its project after a hand-off.

  python3 import-render.py videos/NAME FILE.mp4 [chapters.txt]

FILE is the finished video from the home Mac's videos/_render-inbox/NAME/out/ (dragged over by hand, e.g. through
Screen Sharing). A chapters.txt next to FILE comes along when not named. The video is checked (it opens, has picture
and sound, and lasts about as long as the composition plus any bookends), copied into the project and delivered to
render.json's "deliver" folder, as a local render would be. Exit 1 when the check fails.
"""
import json, os, re, shutil, subprocess, sys

if len(sys.argv) < 3:
    sys.exit(__doc__)
W = os.path.abspath(sys.argv[1].rstrip("/"))
src = os.path.abspath(os.path.expanduser(sys.argv[2]))
chap = os.path.abspath(os.path.expanduser(sys.argv[3])) if len(sys.argv) > 3 else os.path.join(os.path.dirname(src), "chapters.txt")
name = os.path.basename(W)
if not os.path.isfile(os.path.join(W, "render.json")):
    sys.exit("%s has no render.json (is this the right project?)" % W)
if not os.path.isfile(src):
    sys.exit("no such file: %s" % src)
cfg = json.load(open(os.path.join(W, "render.json")))

# ---- the check ------------------------------------------------------------------------------------------------------
pr = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height:format=duration",
                     "-of", "json", src], capture_output=True, text=True)
try:
    j = json.loads(pr.stdout or "{}")
except ValueError:
    j = {}
kinds = [s.get("codec_type") for s in j.get("streams", [])]
dur = float(j.get("format", {}).get("duration") or 0)
problems = []
if "video" not in kinds:
    problems.append("no picture")
if "audio" not in kinds:
    problems.append("no sound")
vid = next((s for s in j.get("streams", []) if s.get("codec_type") == "video"), {})
expect = None
idx = os.path.join(W, "public", "index.html")
if os.path.isfile(idx):
    m = re.search(r'data-composition-id="[^"]*" data-start="0" data-duration="([0-9.]+)"', open(idx, errors="replace").read())
    if m:
        expect = float(m.group(1))
if expect and cfg.get("bookends"):
    expect += 3 + 15 - 0.1                                     # the 3 s sting and the 15 s end card, roughly
if expect and abs(dur - expect) > max(3.0, 0.03 * expect):
    problems.append("%.1f s long, expected about %.1f s (is it %s's render?)" % (dur, expect, name))
print("%s: %sx%s, %.1f s%s" % (os.path.basename(src), vid.get("width", "?"), vid.get("height", "?"), dur,
                                ", expected about %.1f s" % expect if expect else ""))
if problems:
    sys.exit("not imported: " + "; ".join(problems))

# ---- deliver --------------------------------------------------------------------------------------------------------
deliver = os.path.expanduser(cfg.get("deliver") or "~/Movies/YouTube Renders/%s" % cfg.get("name", name))
os.makedirs(deliver, exist_ok=True)
items = [src] + ([chap] if os.path.isfile(chap) else [])
for f in items:
    for d in (W, deliver):
        dst = os.path.join(d, os.path.basename(f))
        if os.path.abspath(dst) != f:
            shutil.copyfile(f, dst)
print("DELIVERED\t%s" % deliver)
