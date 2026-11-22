#!/usr/bin/env python3
"""camera-check.py: is the camera footage flat or washed out, and which grade fixes it? Run it on the raw face file
before Checkpoint A; show the creator the sheet; the chosen grade goes to apply-cut.py --grade.

Reads the colour tags and measures five frames (signalstats on limited-range luma): YMIN, the 10th and 90th percentile
(YLOW / YHIGH) and the average saturation. Lifted blacks (YMIN above ~24; 16 is true black) read as washed out. Writes a
sheet of one frame as recorded and with each grade preset (the same filters apply-cut.py uses, after the BT.601->709
conversion when the file is BT.601).
Usage: python3 camera-check.py --video raw/talking-head.mp4 [--crop 1110:1936:1505:0] [--at 60] [--sheet snaps/grade-options.png]
"""
import argparse, json, re, subprocess, sys
ap = argparse.ArgumentParser()
ap.add_argument("--video", required=True); ap.add_argument("--crop", default="")
ap.add_argument("--at", type=float, default=0.0); ap.add_argument("--sheet", default="")
a = ap.parse_args()
GRADES = {"blacks": "curves=master='0/0 0.13/0.05 1/1'",
          "punchier": "curves=master='0/0 0.14/0.04 0.3/0.23 0.6/0.6 0.9/0.93 1/1',eq=saturation=0.98"}
p = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                               "stream=color_space,color_primaries,color_transfer,color_range,pix_fmt:format=duration",
                               "-of", "json", a.video], capture_output=True, text=True).stdout)
st, dur = p["streams"][0], float(p["format"]["duration"])
cs = st.get("color_space", "unknown")
matrix = {"smpte170m": "bt601-6-525", "bt470bg": "bt601-6-625"}.get(cs, "")
print("colour: space %s, primaries %s, transfer %s, range %s, %s" % (cs, st.get("color_primaries"), st.get("color_transfer"),
      st.get("color_range"), st.get("pix_fmt")))
if matrix:
    print("  BT.601 file: apply-cut.py converts it to BT.709 (relabelling alone shifts skin and reds)")
if st.get("color_range") == "pc":
    print("  WARN full-range file: check the levels by eye before grading")
crop = ("crop=%s," % a.crop) if a.crop else ""
vals = []
for i in range(5):
    t = dur * (i + 1) / 6
    out = subprocess.run(["ffmpeg", "-v", "info", "-ss", "%.2f" % t, "-i", a.video, "-frames:v", "1", "-vf",
                          crop + "scale=640:-2,signalstats,metadata=print", "-f", "null", "-"], capture_output=True, text=True).stderr
    g = lambda k: float(re.findall(r"signalstats\.%s=([0-9.]+)" % k, out)[-1])
    vals.append((t, g("YMIN"), g("YLOW"), g("YHIGH"), g("SATAVG")))
    print("  %6.1f s  black %3.0f  10%% %3.0f  90%% %3.0f  saturation %4.1f" % vals[-1])
ymin = sorted(v[1] for v in vals)[len(vals) // 2]; ylow = sorted(v[2] for v in vals)[len(vals) // 2]
if ymin > 24:
    print("lifted blacks (black %.0f, 10%% %.0f; 16 is true black): offer --grade blacks (subtle) or punchier" % (ymin, ylow))
else:
    print("levels look normal: --grade none")
if a.sheet:
    cs_f = ("colorspace=all=bt709:iall=%s:fast=1," % matrix) if matrix else ""
    lab = "scale=420:-2,drawtext=fontsize=30:fontcolor=white:box=1:boxcolor=black@0.6:x=8:y=8:text="
    t = a.at or dur / 3
    fc = ("[0:v]%ssplit=3[o][b][p];[o]%s'as recorded'[O];[b]%s%s,%s'blacks'[B];[p]%s%s,%s'punchier'[P];[O][B][P]hstack=3"
          % (crop.rstrip(",") + "," if crop else "", lab, cs_f, GRADES["blacks"], lab, cs_f, GRADES["punchier"], lab))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "%.2f" % t, "-i", a.video, "-frames:v", "1", "-filter_complex", fc, a.sheet], check=True)
    print("sheet:", a.sheet)
