#!/usr/bin/env python3
"""screen-cut.py: the screen file of a two-file tutorial, cut exactly like the face flat cut, sped up over waits you
talk through, cropped to the window you work in, as public/screen.mp4 (1920x1080, 30 fps CFR, no audio, dense keyframes).

The two files were recorded together, so every face segment in cut-map.json is reused at the same source times on the
screen file and the two stay in sync. A ramp speeds the screen up over a wait that happens under speech: the screen
covers [src_start, src_end] in (src_end - src_start) / speed seconds, runs ahead of the voice by the time it saved, and
gives that time back at the next audio cut at least 1 s longer than the lead (its screen side is shortened by the lead).
The output is padded or trimmed to the face cut's flat duration.

ramps.json : [{"src_start": 57.06, "src_end": 58.26, "speed": 4, "why": "white page loading under the voice"}]
--src-crops: the window crop per stretch of the SOURCE screen file (preferred: the window changes at a source frame),
             "T:x,y,w,h;T:x,y,w,h" (T = source second the window comes forward; w:h 16:9, enclosing the window;
             screen-windows.py suggests both, and the frame-difference spike gives T to the frame). Each crop is scaled
             to 1920x1080, so windows of different sizes can each get their own crop.
--crops    : the same in FLAT time with one --crop-size for all ("T:x,y;T:x,y"), the older form.
Writes <out> and screen-map.json beside cut-map.json (flat <-> source time for every piece, with its speed).

Convert a variable-frame-rate recording to 30 fps first:
  ffmpeg -i screen.mp4 -vf fps=30 -an -c:v libx264 -preset veryfast -crf 16 -g 30 -pix_fmt yuv420p raw/screenshare.mp4
Usage:
  python3 screen-cut.py --screen raw/screenshare.mp4 --cut-map cut-map.json [--ramps ramps.json]
                        [--src-crops "0:177,0,2560,1440;65.9:0,24,2246,1264"] --out public/screen.mp4
"""
import argparse, json, os, subprocess
ap = argparse.ArgumentParser()
ap.add_argument("--screen", required=True); ap.add_argument("--cut-map", required=True)
ap.add_argument("--ramps", default=""); ap.add_argument("--crops", default=""); ap.add_argument("--crop-size", default="")
ap.add_argument("--src-crops", default="")
ap.add_argument("--out", required=True); ap.add_argument("--crf", type=int, default=16)
a = ap.parse_args()
cm = json.load(open(a.cut_map))
ramps = json.load(open(a.ramps)) if a.ramps else []
segs = [(float(s["src_start"]), float(s["src_end"])) for s in cm["segments"]]
flat_d = float(cm["flat_duration"])
snap = lambda t: round(t * 30) / 30

pieces, lead = [], 0.0          # (src_a, src_b, speed)
for i, (s0, s1) in enumerate(segs):
    if lead > 0 and i > 0 and s0 - segs[i - 1][1] > lead + 1.0:   # this cut repays the lead
        lead = 0.0
    t, left = s0 + lead, s1 - s0
    for r in ramps:
        ra, rb, k = float(r["src_start"]), float(r["src_end"]), float(r["speed"])
        if ra < s1 and rb > s0:
            ra = max(ra, t)
            if rb - ra < 0.2:
                continue
            if ra > t:
                pieces.append((t, ra, 1.0)); left -= ra - t
            pieces.append((ra, rb, k)); left -= (rb - ra) / k
            lead += (rb - ra) - (rb - ra) / k; t = rb
    pieces.append((t, t + left, 1.0))
if lead > 0.05:
    print("WARN the screen ends %.2f s ahead of the voice: no later cut was long enough to repay a ramp" % lead)

src_crops = []
if a.src_crops:
    if a.crops:
        raise SystemExit("use --src-crops or --crops, not both")
    for item in a.src_crops.split(";"):
        t, box = item.split(":"); src_crops.append((float(t), [int(v) for v in box.split(",")]))
    src_crops.sort(); src_crops[0] = (-1.0, src_crops[0][1])
    split = []
    for x0, x1, k in pieces:          # a piece that spans a window change becomes two, each with its own crop
        cuts_in = [t for t, _ in src_crops if x0 < t < x1]
        edges = [x0] + cuts_in + [x1]
        split += [(edges[i], edges[i + 1], k) for i in range(len(edges) - 1) if edges[i + 1] - edges[i] > 1e-3]
    pieces = split
box_at = lambda t: [b for s, b in src_crops if s <= t + 1e-6][-1]
parts, labels = [], []
for j, (x0, x1, k) in enumerate(pieces):
    crop = ",crop=%d:%d:%d:%d,scale=1920:1080:flags=lanczos,setsar=1" % tuple(box_at(x0)[2:] + box_at(x0)[:2]) if src_crops else ""
    parts.append("[0:v]trim=start=%.6f:end=%.6f,setpts=(PTS-STARTPTS)/%g%s[p%d]" % (snap(x0), snap(x1), k, crop, j)); labels.append("[p%d]" % j)
fc = ";".join(parts) + ";" + "".join(labels) + "concat=n=%d:v=1:a=0,fps=30,tpad=stop=30:stop_mode=clone" % len(pieces)
frames = int(round(flat_d * 30))
if src_crops:
    fc += "[v]"
elif a.crops:
    cw, ch = [int(v) for v in a.crop_size.lower().split("x")]
    cuts = []
    for item in a.crops.split(";"):
        t, xy = item.split(":"); x, y = xy.split(",")
        cuts.append((int(round(float(t) * 30)), int(x), int(y)))
    cuts.sort(); cuts[0] = (0,) + cuts[0][1:]
    fc += ",split=%d%s" % (len(cuts), "".join("[s%d]" % i for i in range(len(cuts))))
    outs = []
    for i, (f0, x, y) in enumerate(cuts):
        f1 = cuts[i + 1][0] if i + 1 < len(cuts) else frames
        fc += ";[s%d]trim=start_frame=%d:end_frame=%d,setpts=PTS-STARTPTS,crop=%d:%d:%d:%d[c%d]" % (i, f0, f1, cw, ch, x, y, i)
        outs.append("[c%d]" % i)
    fc += ";%sconcat=n=%d:v=1:a=0,scale=1920:1080:flags=lanczos,setsar=1[v]" % ("".join(outs), len(outs))
else:
    fc += ",scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:-1:-1,setsar=1[v]"
os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", a.screen, "-filter_complex", fc, "-map", "[v]", "-an", "-frames:v", str(frames),
                "-c:v", "libx264", "-preset", "veryfast", "-crf", str(a.crf), "-g", "15", "-keyint_min", "15", "-pix_fmt", "yuv420p",
                "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-color_range", "tv",
                "-movflags", "+faststart", a.out], check=True)
pos, rows = 0.0, []
for x0, x1, k in pieces:
    d = (snap(x1) - snap(x0)) / k
    rows.append({"flat_start": round(pos, 3), "flat_end": round(pos + d, 3), "src_start": round(snap(x0), 3), "src_end": round(snap(x1), 3), "speed": k})
    pos += d
json.dump({"flat_duration": flat_d, "pieces": rows, "crops": a.crops, "crop_size": a.crop_size, "src_crops": a.src_crops},
          open(os.path.join(os.path.dirname(os.path.abspath(a.cut_map)), "screen-map.json"), "w"), indent=2)
got = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames", "-show_entries", "stream=nb_read_frames",
                      "-of", "csv=p=0", a.out], capture_output=True, text=True).stdout.strip()
print("%s: %s frames (face cut %d), %d pieces, %d ramp(s)" % (a.out, got, frames, len(rows), sum(1 for r in rows if r["speed"] != 1)))
