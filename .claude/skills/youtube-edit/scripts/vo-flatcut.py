#!/usr/bin/env python3
"""vo-flatcut.py: the AI voiceover route's flat cut. <project>/edl.json + <project>/vo/<voice>/<id>.wav
-> <project>/public/input-video.mp4 (1920x1080, 30 fps, BT.709, CRF 16, a keyframe every 30 frames) + <project>/vo-map.json.

Each piece is cut from the silent screen recording, cropped to one pane, blurred where listed, sped up or frozen,
and placed on a 1920x1080 canvas. Each segment's voiceover clip starts at segment start + vo_at. A segment is never
shorter than its voiceover plus 0.25 s: the last piece is held (frame freeze) to make up any shortfall.
edl.json: {"source": "raw/x.mp4", "canvas": {"w":1920,"h":1080,"bg":"0x042729","x":480,"y":50},
  "crops": {"R": [x,y,w,h], ...}, "blurs": {"name": [x,y,w,h], ...} (SOURCE pixels),
  "segments": [{"id": "S1" (= the voice clip's name), "chapter": "Setup", "vo_at": 0.3,
                "pieces": [{"crop":"R","in":13.0,"out":24.0,"speed":2.0,"blur":["name"]}, {"crop":"R","freeze":245.5,"dur":9.0}]},
               {"id": "gap1", "note": "agent works", "pieces": [...]}]}   (a segment with no clip is silent)
Usage: python3 vo-flatcut.py --project videos/<p> [--voice af_heart]
"""
import argparse, json, os, subprocess, shutil

FPS = 30
ap = argparse.ArgumentParser(); ap.add_argument("--project", required=True); ap.add_argument("--voice", default="af_heart")
a = ap.parse_args()
here = os.path.abspath(a.project)
edl = json.load(open(os.path.join(here, "edl.json")))
src = os.path.join(here, edl["source"]); cv = edl["canvas"]
work = os.path.join(here, "work", "pieces"); shutil.rmtree(work, ignore_errors=True); os.makedirs(work)
os.makedirs(os.path.join(here, "public"), exist_ok=True)

def dur_of(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p],
                                capture_output=True, text=True).stdout)

def vf_for(p):
    x, y, w, h = edl["crops"][p["crop"]]
    chain = []
    # blurs are in SOURCE pixels; apply before the crop
    for i, b in enumerate(p.get("blur", [])):
        bx, by, bw, bh = edl["blurs"][b]
        chain.append(f"split[m{i}][b{i}];[b{i}]crop={bw}:{bh}:{bx}:{by},gblur=sigma=10:steps=3[bb{i}];[m{i}][bb{i}]overlay={bx}:{by}")
    chain.append(f"crop={w}:{h}:{x}:{y}")
    chain.append(f"pad={cv['w']}:{cv['h']}:{cv['x']}:{cv['y']}:color={cv['bg']}")
    chain.append("format=yuv420p")
    return ",".join(chain)

enc = ["-c:v", "libx264", "-crf", "16", "-preset", "fast", "-g", "30", "-keyint_min", "30", "-pix_fmt", "yuv420p",
       "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-color_range", "tv", "-an"]

def render(p, out, frames):
    if "freeze" in p:
        cmd = ["ffmpeg", "-y", "-v", "error", "-ss", f"{p['freeze']:.3f}", "-i", src, "-frames:v", "1",
               "-vf", vf_for(p), os.path.join(work, "still.png")]
        subprocess.run(cmd, check=True)
        cmd = ["ffmpeg", "-y", "-v", "error", "-loop", "1", "-framerate", str(FPS), "-i", os.path.join(work, "still.png"),
               "-frames:v", str(frames), *enc, out]
    else:
        sp = p.get("speed", 1.0)
        span = p["out"] - p["in"]
        vf = f"setpts=(PTS-STARTPTS)/{sp},fps={FPS}," + vf_for(p) + f",tpad=stop_mode=clone:stop_duration=2"
        cmd = ["ffmpeg", "-y", "-v", "error", "-ss", f"{p['in']:.3f}", "-t", f"{span + 0.2:.3f}", "-i", src,
               "-vf", vf, "-frames:v", str(frames), *enc, out]
    subprocess.run(cmd, check=True)

files, vomap, t = [], [], 0.0
for seg in edl["segments"]:
    vo = os.path.join(here, "vo", a.voice, seg["id"] + ".wav")
    vo_d = dur_of(vo) if os.path.exists(vo) else 0.0
    plan = []
    for p in seg["pieces"]:
        d = p["dur"] if "freeze" in p else (p["out"] - p["in"]) / p.get("speed", 1.0)
        plan.append([p, round(d * FPS)])
    need = round((seg.get("vo_at", 0) + vo_d + 0.25) * FPS) if vo_d else 0
    have = sum(n for _, n in plan)
    if need > have:                      # hold the last piece's final frame for the shortfall
        plan[-1][1] += need - have
        print(f"  {seg['id']}: held last piece +{(need - have) / FPS:.2f}s to fit the voiceover")
    seg_start = t
    for i, (p, n) in enumerate(plan):
        out = os.path.join(work, f"{len(files):03d}-{seg['id']}-{i}.mp4")
        render(p, out, n); files.append(out); t += n / FPS
    if vo_d:
        vomap.append({"id": seg["id"], "file": vo, "start": round(seg_start + seg["vo_at"], 3), "dur": round(vo_d, 3),
                      "seg_start": round(seg_start, 3), "seg_end": round(t, 3), "chapter": seg.get("chapter")})
    else:
        vomap.append({"id": seg["id"], "start": None, "seg_start": round(seg_start, 3), "seg_end": round(t, 3),
                      "note": seg.get("note")})
    print(f"{seg['id']:5s} {seg_start:7.2f}-{t:7.2f}  ({t - seg_start:5.2f}s)  vo {vo_d:5.2f}s")

lst = os.path.join(work, "list.txt")
open(lst, "w").write("".join(f"file '{f}'\n" for f in files))
silent = os.path.join(here, "work", "video-silent.mp4")
subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", silent], check=True)

# voiceover track: every clip delayed to its start, mixed without normalisation, padded to the video length
total = dur_of(silent)
inputs, fl = [], []
vo_items = [v for v in vomap if v.get("start") is not None]
for i, v in enumerate(vo_items):
    inputs += ["-i", v["file"]]
    ms = int(round(v["start"] * 1000))
    fl.append(f"[{i + 1}:a]aresample=48000,aformat=channel_layouts=mono,adelay={ms}:all=1[v{i}]")
mix = "".join(f"[v{i}]" for i in range(len(vo_items)))
fl.append(f"{mix}amix=inputs={len(vo_items)}:normalize=0:duration=longest,apad=whole_dur={total:.3f},"
          f"atrim=0:{total:.3f},aformat=channel_layouts=stereo[a]")
out = os.path.join(here, "public", "input-video.mp4")
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", silent, *inputs, "-filter_complex", ";".join(fl),
                "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-ar", "48000",
                "-movflags", "+faststart", out], check=True)
json.dump({"duration": round(total, 3), "segments": vomap}, open(os.path.join(here, "vo-map.json"), "w"), indent=1)
print(f"\n{out}: {total:.2f}s, {len(vo_items)} voiceover clips")
