#!/usr/bin/env python3
"""start_cut.py NAME: name the recordings in a scaffolded video's raw/ the way the cut stage expects.

The file with an audio stream (the largest, if several) becomes raw/talking-head.<ext>; the first without audio
becomes raw/screenshare-vfr.<ext>. Files already named that way are kept. Prints the roles; exit 1 when there is no
camera file. `yt start NAME` runs this, then the cut stage (the inbox does the same for a drop).
"""
import json, os, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core

VID = (".mp4", ".mov", ".m4v")


def has_audio(p):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "json", p],
                         capture_output=True, text=True).stdout or "{}"
    return "audio" in [s.get("codec_type") for s in json.loads(out).get("streams", [])]


def assign(name):
    raw = os.path.join(core.video_dir(name), "raw")
    files = sorted(f for f in os.listdir(raw) if f.lower().endswith(VID)) if os.path.isdir(raw) else []
    face = next((f for f in files if f.startswith("talking-head.")), None)
    screen = next((f for f in files if f.startswith("screenshare")), None)
    rest = [f for f in files if f not in (face, screen) and not f.startswith(("camera-original", "screenshare"))]
    cams = sorted(((os.path.getsize(os.path.join(raw, f)), f) for f in rest if has_audio(os.path.join(raw, f))), reverse=True)
    scr = [f for f in rest if f not in [c[1] for c in cams]]
    if not face and cams:
        f = cams.pop(0)[1]; face = "talking-head" + os.path.splitext(f)[1].lower()
        os.replace(os.path.join(raw, f), os.path.join(raw, face))
    if not screen and scr:
        f = scr.pop(0); screen = "screenshare-vfr" + os.path.splitext(f)[1].lower()
        os.replace(os.path.join(raw, f), os.path.join(raw, screen))
    if not face:
        print("no camera file in raw/ (the file with the mic's audio)"); sys.exit(1)
    v = core.load_video(name)
    if not v.get("legacy"):
        v["phase"] = "cut"; core.save_video(name, v)
    print("camera %s%s" % (face, (", screen %s" % screen) if screen else ""))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    assign(sys.argv[1])
