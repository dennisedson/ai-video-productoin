#!/usr/bin/env python3
"""card-check.py: does the face card in a tutorial-layout render ever go blank while it should show your face?

With two render workers Chrome sometimes captured the card before its video frame was ready: the card flashed empty
(the wash showing through) ~80 times in 67 s, and verify-render.py cannot see it (the wash is not black). This decodes
the card region at low resolution and counts frames whose picture is nearly flat inside the given windows.
Usage: python3 card-check.py --render out.mp4 --card 48,48,1232,2112 --windows "0-34.9,64.4-78.4,228-" [--max 0]
--card is x0,y0,x1,y1 in the render's pixels (the layout's face card at 4K: left 48,48,1232,2112; right 2608,48,3792,2112).
Exit 1 when more blank frames than --max are found.
"""
import argparse, subprocess, sys, numpy as np
ap = argparse.ArgumentParser()
ap.add_argument("--render", required=True); ap.add_argument("--card", required=True); ap.add_argument("--windows", required=True)
ap.add_argument("--max", type=int, default=0); ap.add_argument("--flat", type=float, default=12.0)
a = ap.parse_args()
x0, y0, x1, y1 = [int(v) for v in a.card.split(",")]
W, H = 60, max(2, round(60 * (y1 - y0) / (x1 - x0) / 2) * 2)
fps = 30.0
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", a.render, "-vf", "crop=%d:%d:%d:%d,scale=%d:%d,format=gray" % (x1 - x0, y1 - y0, x0, y0, W, H),
                      "-f", "rawvideo", "-"], capture_output=True).stdout
fr = np.frombuffer(raw, np.uint8).reshape(-1, H, W).astype(np.float32)
flat = fr.std(axis=(1, 2)) < a.flat
wins = []
for w in a.windows.split(","):
    lo, hi = w.split("-")
    wins.append((float(lo), float(hi) if hi else len(fr) / fps))
bad = [i for i in np.flatnonzero(flat) if any(lo + 0.7 <= i / fps <= hi - 0.7 for lo, hi in wins)]   # skip the 0.6 s layout moves
print("%s: %d frames, %d blank face-card frame(s) inside the face windows%s" % (a.render, len(fr), len(bad),
      (": " + ", ".join("%.2f" % (i / fps) for i in bad[:20]) + (" ..." if len(bad) > 20 else "")) if bad else ""))
sys.exit(1 if len(bad) > a.max else 0)
