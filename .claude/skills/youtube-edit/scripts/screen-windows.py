#!/usr/bin/env python3
"""screen-windows.py: where the app windows sit in a screen recording, over time, and a 16:9 crop for each.

Light window content against a desktop: each sampled frame is reduced to the runs of columns that are mostly light
(> --light grey level in more than half the rows of the band), and each run's row extent. Prints, per change, the
runs and a 16:9 crop enclosing each one (whole window kept, wallpaper at the sides when the window is narrower than
16:9), plus a contact sheet. Decide which run is the window you work in by looking at the sheet; the crop goes into
screen-cut.py --crops (in FLAT time: map source times through screen-map.json or cut-map.json).
Usage: python3 screen-windows.py --video raw/screenshare.mp4 [--every 1.0] [--sheet snaps/screen-windows.png]
"""
import argparse, subprocess, numpy as np
ap = argparse.ArgumentParser()
ap.add_argument("--video", required=True); ap.add_argument("--every", type=float, default=1.0)
ap.add_argument("--light", type=int, default=200); ap.add_argument("--sheet", default="")
a = ap.parse_args()
w, h = [int(v) for v in subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
        "-of", "csv=p=0:s=x", a.video], capture_output=True, text=True).stdout.strip().split("x")]
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", a.video, "-vf", "fps=1/%g,format=gray" % a.every, "-f", "rawvideo", "-"],
                     capture_output=True).stdout
fr = np.frombuffer(raw, np.uint8).reshape(-1, h, w)
def runs(f):
    band = f[int(h * .05):int(h * .9)] > a.light
    col = band.mean(axis=0) > 0.5
    out, s = [], None
    for x in range(w + 1):
        on = x < w and col[x]
        if on and s is None: s = x
        if not on and s is not None:
            if x - s > w * 0.04:
                rows = np.flatnonzero((f[:, s:x] > a.light).mean(axis=1) > 0.5)
                out.append((s, x, int(rows.min()) if len(rows) else 0, int(rows.max()) if len(rows) else h))
            s = None
    return out
def crop16x9(x0, x1, y0, y1):
    cw, ch = x1 - x0 + 2 * 16, y1 - y0 + 2 * 16
    if cw / ch > 16 / 9: ch = cw * 9 / 16
    else: cw = ch * 16 / 9
    cw, ch = min(w, int(round(cw / 2)) * 2), min(h, int(round(ch / 2)) * 2)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    x, y = int(min(max(0, cx - cw / 2), w - cw)) // 2 * 2, int(min(max(0, cy - ch / 2), h - ch)) // 2 * 2
    return cw, ch, x, y
prev = None
for i, f in enumerate(fr):
    r = runs(f)
    key = [(round(s / 40), round(e / 40)) for s, e, _, _ in r]
    if key != prev:
        print("%7.1f s  " % (i * a.every) + "  ".join("window x %d-%d y %d-%d -> crop %dx%d at %d,%d" % ((s, e, t, b) + crop16x9(s, e, t, b)) for s, e, t, b in r))
        prev = key
if a.sheet:
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a.video, "-vf", "fps=1/%g,scale=640:-2,tile=4x8" % max(a.every, 2.5),
                    "-frames:v", "1", a.sheet], check=True)
    print("sheet:", a.sheet)
