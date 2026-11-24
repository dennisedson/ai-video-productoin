#!/usr/bin/env python3
"""thumbnail.py: YouTube thumbnails in the video's profile brand (profiles/<profile>/thumbnail/index.html).

  python3 thumbnail.py frames --project videos/NAME     candidate frames for the writing step: youtube/frames.jpg
                                                          (a 4x3 sheet, each tile stamped with its time) + frames.json
  python3 thumbnail.py page   --project videos/NAME [--option N] [--face FILE] [--mode cutout|photo|none]
                                                          fill and stage the template only (youtube/thumb-N/), to look at
  python3 thumbnail.py render --project videos/NAME [--option N]
                                                          the thumbnails: youtube/thumbnail-N.jpg (3840x2160, < 50 MB,
                                                          for desktop upload) and thumbnail-N-mobile.jpg (1280x720,
                                                          < 2 MB, for the app), a sheet thumbnails.jpg, thumbnails.json

The options are metadata.json's "thumbnail": {"options": [{"headline": "Claude runs|my CRM", "key": "Claude",
"eyebrow": "HubSpot Is Going Headless", "t": 41.2}, ...]}: "|" breaks the line, "key" is the one word in the accent
colour, "face" (optional) a headshot instead of a frame ("dennis.jpg": the video's folder first, for a guest, then
shared/img/headshots/; "frame" for the video; default: the profile's thumbnail/config.json "face", else "frame"; a PNG
that is already cut out is used as it is), "t" the frame on the transcript's clock (the flat cut for an edited video, the video itself for a
metadata-only one). The frame comes from the 4K camera file for an edited video (cut-map.json maps the time; the
video's grade is applied as apply-cut.py does), from the finished file for a metadata-only one. The face is cut out
with `hyperframes remove-background`; if that fails, the photo fades into the background instead (thumbnails.json
says which). The still is a HyperFrames snapshot at twice the density (3840x2160, the same layout); a short 4K render
is the fallback.
"""
import argparse, glob, html, json, os, re, shutil, subprocess, sys

SK = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
ap = argparse.ArgumentParser()
ap.add_argument("cmd", choices=["frames", "page", "render"])
ap.add_argument("--project", required=True)
ap.add_argument("--option", type=int, help="1-based; default every option")
ap.add_argument("--face", help="page: an image to place as the face")
ap.add_argument("--mode", default="cutout", choices=["cutout", "photo", "none"])
a = ap.parse_args()
W = os.path.abspath(a.project.rstrip("/"))
NAME = os.path.basename(W)
Y = os.path.join(W, "youtube")
os.makedirs(Y, exist_ok=True)
GRADES = {"none": "", "blacks": "curves=master='0/0 0.13/0.05 1/1'",                     # as apply-cut.py GRADES
          "punchier": "curves=master='0/0 0.14/0.04 0.3/0.23 0.6/0.6 0.9/0.93 1/1',eq=saturation=0.98"}


def load(p, d=None):
    try:
        return json.load(open(p))
    except (OSError, ValueError):
        return d


def run(cmd, quiet=False):
    if not quiet:
        print("   $ " + " ".join(str(c) for c in cmd[:7]) + (" ..." if len(cmd) > 7 else ""), flush=True)
    return subprocess.run([str(c) for c in cmd], capture_output=quiet, text=True)


story = load(os.path.join(W, "storyboard.json"), {}) or {}
source = load(os.path.join(Y, "source.json"), {}) or {}
render_cfg = load(os.path.join(W, "render.json"), {}) or {}
PROFILE = story.get("profile") or source.get("profile") or "hubspot"
PD = os.path.join(SK, "profiles", PROFILE)
TPL = os.path.join(PD, "thumbnail", "index.html")
ROOT = os.path.abspath(os.path.join(SK, "..", "..", ".."))
HEADSHOTS = os.path.join(ROOT, "shared", "img", "headshots")    # git-ignored: each Mac keeps its own copy
IMG = (".png", ".jpg", ".jpeg", ".webp", ".heic", ".tif", ".tiff")


def _transparent_edges(f):
    """True when at least a tenth of the image is (nearly) transparent: a headshot that is already a cutout."""
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", f, "-vf", "alphaextract,scale=64:64", "-f", "rawvideo",
                        "-pix_fmt", "gray", "-"], capture_output=True)
    return bool(r.stdout) and sum(1 for v in r.stdout if v < 48) >= len(r.stdout) // 10


def headshots():
    return sorted(f for f in os.listdir(HEADSHOTS) if f.lower().endswith(IMG)) if os.path.isdir(HEADSHOTS) else []


def default_face():
    """The profile's default face: "frame" (from the video) or a headshot file name (thumbnail/config.json)."""
    return ((load(os.path.join(PD, "thumbnail", "config.json"), {}) or {}).get("face") or "frame").strip()


def face_file(name):
    """A headshot named in an option or the profile: the video's folder (a guest), then shared/img/headshots/."""
    for base in (W, HEADSHOTS, ROOT):
        f = os.path.join(base, name)
        if os.path.isfile(f):
            return f
    return None


def review_video():
    """The video to pick frames from on the transcript's clock."""
    if source.get("video"):
        return os.path.join(W, source["video"])
    for f in ("public/input-video.mp4", "review/cut-review.mp4"):
        if os.path.isfile(os.path.join(W, f)):
            return os.path.join(W, f)
    return None


def full_frame_source(t):
    """(file, seconds, filter) for the sharpest graded frame at transcript time t."""
    if source.get("video"):
        return os.path.join(W, source["video"]), t, ""
    cm = load(os.path.join(W, "cut-map.json"), {}) or {}
    raw = render_cfg.get("face_raw") or ""
    raw = os.path.join(W, raw) if raw else (sorted(glob.glob(os.path.join(W, "raw", "talking-head.*"))) or [""])[0]
    for s in cm.get("segments", []):
        if s["flat_start"] <= t < s["flat_end"] and raw and os.path.isfile(raw):
            src_space = (cm.get("matrix") or "").split(" -> ")[0]          # "smpte170m -> bt709", as apply-cut.py writes it
            matrix = {"smpte170m": "bt601-6-525", "bt470bg": "bt601-6-625"}.get(src_space, "")
            grade = GRADES.get(render_cfg.get("grade") or cm.get("grade") or "none", "")
            vf = ",".join(f for f in ("colorspace=all=bt709:iall=%s:fast=1" % matrix if matrix else "", grade, cm.get("vf") or "") if f)
            return raw, s["src_start"] + (t - s["flat_start"]), vf
    return review_video(), t, ""                              # no map: the review cut (sharp enough at 1080p+)


def options():
    m = load(os.path.join(Y, "metadata.json"), {}) or {}
    opts = (m.get("thumbnail") or {}).get("options") or []
    if a.option:
        if not 1 <= a.option <= len(opts):
            sys.exit("no thumbnail option %d (metadata.json has %d)" % (a.option, len(opts)))
        return [(a.option, opts[a.option - 1])]
    return list(enumerate(opts, 1))


def headline_html(o):
    key = (o.get("key") or "").strip().lower()
    done, lines = False, []
    for ln in (o.get("headline") or "").split("|"):
        words = []
        for w in ln.split():
            bare = re.sub(r"[^\w'-]", "", w).lower()
            if key and not done and bare == key:
                words.append("<em>%s</em>" % html.escape(w)); done = True
            else:
                words.append(html.escape(w))
        lines.append('<div class="ln">%s</div>' % " ".join(words))
    return "".join(lines)


def stage_page(i, o, face, mode):
    if not os.path.isfile(TPL):
        sys.exit("the %s profile has no thumbnail template (%s)" % (PROFILE, TPL))
    d = os.path.join(Y, "thumb-%d" % i)
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(os.path.join(d, "vendor"))
    shutil.copytree(os.path.join(PD, "fonts"), os.path.join(d, "fonts"))
    if os.path.isdir(os.path.join(PD, "assets")):
        shutil.copytree(os.path.join(PD, "assets"), os.path.join(d, "assets"))
    shutil.copy(os.path.join(SK, "assets", "vendor", "gsap.min.js"), os.path.join(d, "vendor", "gsap.min.js"))
    face_src = ""
    if face and mode != "none":
        face_src = "face" + os.path.splitext(face)[1].lower()
        shutil.copy(face, os.path.join(d, face_src))
    page = open(TPL).read()
    for k, v in {"EYEBROW": html.escape(o.get("eyebrow", "")), "HEADLINE": headline_html(o),
                 "FACE_MODE": mode if face_src else "none", "FACE_SRC": face_src}.items():
        page = page.replace("{{%s}}" % k, v)
    left = re.findall(r"\{\{[A-Z_]+\}\}", page)
    if left:
        sys.exit("thumbnail template: unfilled %s" % ", ".join(sorted(set(left))))
    open(os.path.join(d, "index.html"), "w").write(page)
    hj = os.path.join(W, "public", "hyperframes.json")
    if os.path.isfile(hj):
        shutil.copy(hj, os.path.join(d, "hyperframes.json"))
    return d


# ---- frames: candidates for the writing step ---------------------------------------------------------------------
if a.cmd == "frames":
    src = review_video()
    if not src or not os.path.isfile(src):
        sys.exit("no video to take frames from")
    dur = float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", src], quiet=True).stdout.strip() or 0)
    words = load(os.path.join(W, "transcript.json"), []) or []
    starts, prev = [], None
    for w in words:                                       # sentence starts, a beat in, spread over the video
        if prev is None or prev["text"].endswith((".", "?", "!")):
            starts.append(w["start"] + 0.8)
        prev = w
    starts = [t for t in starts if 1.0 < t < dur - 3]
    gap = max(dur / 14.0, 4.0)
    picked = []
    for t in starts:
        if not picked or t - picked[-1] >= gap:
            picked.append(t)
    if len(picked) < 12:                                  # top up evenly
        picked = sorted(set(round(x, 1) for x in picked + [dur * (k + 0.5) / 12 for k in range(12)]))
        while len(picked) > 12:
            d = [picked[k + 1] - picked[k] for k in range(len(picked) - 1)]
            picked.pop(d.index(min(d)) + 1)
    fd = os.path.join(Y, "frames"); shutil.rmtree(fd, ignore_errors=True); os.makedirs(fd)
    tiles = []
    for t in picked[:12]:
        f = os.path.join(fd, "t%06.1f.jpg" % t)
        stamp = "%d\\:%02d (%.1f s)" % (int(t) // 60, int(t) % 60, t)
        fsrc, ft, fvf = full_frame_source(t)              # the camera itself when there is one, as the thumbnail will use
        pre = (fvf + ",") if fvf else ""
        r = run(["ffmpeg", "-y", "-v", "error", "-ss", "%.3f" % ft, "-i", fsrc, "-frames:v", "1", "-vf",
                 pre + "scale=640:360:force_original_aspect_ratio=decrease,pad=640:360:(ow-iw)/2:(oh-ih)/2,"
                 "drawtext=text='%s':x=14:y=12:fontsize=30:fontcolor=white:box=1:boxcolor=black@0.65:boxborderw=8" % stamp,
                 "-q:v", "3", f], quiet=True)
        if r.returncode != 0:                             # no drawtext: plain frame
            run(["ffmpeg", "-y", "-v", "error", "-ss", "%.3f" % ft, "-i", fsrc, "-frames:v", "1", "-vf",
                 pre + "scale=640:360:force_original_aspect_ratio=decrease,pad=640:360:(ow-iw)/2:(oh-ih)/2", "-q:v", "3", f], quiet=True)
        if os.path.isfile(f):
            tiles.append({"t": round(t, 1), "file": os.path.relpath(f, Y)})
    json.dump(tiles, open(os.path.join(Y, "frames.json"), "w"), indent=1)
    if len(tiles) >= 4:
        n = len(tiles); cols = 4
        lay = "|".join("%d_%d" % ((k % cols) * 640, (k // cols) * 360) for k in range(n))
        cmd = ["ffmpeg", "-y", "-v", "error"]
        for tl in tiles:
            cmd += ["-i", os.path.join(Y, tl["file"])]
        cmd += ["-filter_complex", "".join("[%d:v]scale=640:360[s%d];" % (k, k) for k in range(n)) +
                "".join("[s%d]" % k for k in range(n)) + "xstack=inputs=%d:layout=%s:fill=black" % (n, lay),
                "-q:v", "3", os.path.join(Y, "frames.jpg")]
        run(cmd, quiet=True)
    print("frames: %d candidates -> youtube/frames.jpg" % len(tiles))
    sys.exit(0)

# ---- page: stage one option to look at -------------------------------------------------------------------------------
if a.cmd == "page":
    for i, o in options() or [(1, {"headline": "Your headline|goes here", "key": "headline", "eyebrow": "Series"})]:
        d = stage_page(i, o, a.face, a.mode)
        print("staged %s" % d)
    sys.exit(0)

# ---- render ---------------------------------------------------------------------------------------------------------
opts = options()
if not opts:
    sys.exit("metadata.json has no thumbnail options yet")
if not os.path.isfile(TPL):
    print("the %s profile has no thumbnail template: no thumbnails" % PROFILE); sys.exit(3)
results = load(os.path.join(Y, "thumbnails.json"), {}) or {}
made = 0
for i, o in opts:
    work = os.path.join(Y, "thumb-work-%d" % i); shutil.rmtree(work, ignore_errors=True); os.makedirs(work)
    want = (o.get("face") or default_face()).strip()
    frame = os.path.join(work, "frame.png")
    if want != "frame":                                   # a headshot instead of a frame from the video
        hs = face_file(want)
        if not hs:
            print("thumbnail %d: no headshot %s (looked in the video's folder and shared/img/headshots/)" % (i, want)); continue
        run(["ffmpeg", "-y", "-v", "error", "-i", hs, "-frames:v", "1", frame], quiet=True)   # any format -> PNG, alpha kept
        if not os.path.isfile(frame) and sys.platform == "darwin":                            # HEIC: sips reads it
            run(["sips", "-s", "format", "png", hs, "--out", frame], quiet=True)
    else:
        src, st, vf = full_frame_source(float(o.get("t", 0)))
        run(["ffmpeg", "-y", "-v", "error", "-ss", "%.3f" % st, "-i", src, "-frames:v", "1"] + (["-vf", vf] if vf else []) + [frame])
    if not os.path.isfile(frame):
        print("thumbnail %d: no face image (%s)" % (i, want if want != "frame" else "frame at %.1f s" % float(o.get("t", 0)))); continue
    mode, face = "photo", frame                           # the cutout, if remove-background manages it
    matte, cut = os.path.join(work, "matte.png"), os.path.join(work, "face.png")
    has_alpha = lambda f: bool(re.search(r"rgba|bgra|argb|abgr|yuva|ya8|ya16|gbrap", run(["ffprobe", "-v", "error",
        "-show_entries", "stream=pix_fmt", "-of", "csv=p=0", f], quiet=True).stdout)) if os.path.isfile(f) else False
    if want != "frame" and has_alpha(frame) and _transparent_edges(frame):
        shutil.copy(frame, matte); r = subprocess.CompletedProcess([], 0)           # already cut out
    else:
        r = run(["npx", "--yes", "hyperframes", "remove-background", frame, "-o", matte])
    pf = run(["ffprobe", "-v", "error", "-show_entries", "stream=pix_fmt", "-of", "csv=p=0", matte], quiet=True).stdout if os.path.isfile(matte) else ""
    if r.returncode == 0 and re.search(r"rgba|bgra|argb|abgr|yuva|ya8|ya16|gbrap", pf):   # it has an alpha channel
        bb = run(["ffmpeg", "-v", "info", "-i", matte, "-vf", "alphaextract,bbox=min_val=40", "-f", "null", "-"], quiet=True).stderr
        m = re.findall(r"x1:(\d+) x2:(\d+) y1:(\d+) y2:(\d+)", bb)
        if m:                                             # crop to the person, so the template can stand them in the frame
            x1, x2, y1, y2 = (int(v) for v in m[-1])
            if (x2 - x1) > 200 and (y2 - y1) > 300:
                run(["ffmpeg", "-y", "-v", "error", "-i", matte, "-vf", "crop=%d:%d:%d:%d" % (x2 - x1 + 1, y2 - y1 + 1, x1, y1), cut], quiet=True)
                if os.path.isfile(cut):
                    mode, face = "cutout", cut
    d = stage_page(i, o, face, mode)
    big, small = os.path.join(Y, "thumbnail-%d.jpg" % i), os.path.join(Y, "thumbnail-%d-mobile.jpg" % i)
    snap = os.path.join(work, "snap")                     # one still at 2x density: 3840x2160, same layout
    run(["npx", "--yes", "hyperframes", "snapshot", d, "--at", "0.2", "--no-end", "--zoom", "0,0,1920,1080", "--zoom-scale", "2", "-o", snap])
    png = (sorted(glob.glob(os.path.join(snap, "frame-*.png"))) or [""])[0]
    if not png:                                           # no snapshot: render it as a short 4K clip and keep a frame
        mp4 = os.path.join(work, "thumb.mp4")
        run(["npx", "--yes", "hyperframes", "render", d, "--resolution", "4k", "--video-bitrate", "80M", "--workers", "1", "-o", mp4])
        png = mp4 if os.path.isfile(mp4) else ""
    if not png:
        print("thumbnail %d: the still failed" % i); continue
    run(["ffmpeg", "-y", "-v", "error"] + (["-ss", "0.2"] if png.endswith(".mp4") else []) + ["-i", png, "-frames:v", "1",
         "-vf", "scale=3840:2160:flags=lanczos", "-q:v", "2", big], quiet=True)
    for q in (2, 3, 4, 6, 8):                             # the app's 2 MB limit
        run(["ffmpeg", "-y", "-v", "error", "-i", big, "-vf", "scale=1280:720:flags=lanczos", "-q:v", str(q), small], quiet=True)
        if os.path.isfile(small) and os.path.getsize(small) < 2_000_000:
            break
    results[str(i)] = {"headline": o.get("headline"), "key": o.get("key"), "eyebrow": o.get("eyebrow"), "t": o.get("t"), "face": want,
                       "mode": mode, "file": os.path.basename(big), "mobile": os.path.basename(small),
                       "mb": round(os.path.getsize(big) / 1e6, 2) if os.path.isfile(big) else None,
                       "mobile_mb": round(os.path.getsize(small) / 1e6, 2) if os.path.isfile(small) else None}
    made += 1
    print("thumbnail %d: %s (%s), %s MB; mobile %s MB" % (i, os.path.basename(big), mode, results[str(i)]["mb"], results[str(i)]["mobile_mb"]))
json.dump(results, open(os.path.join(Y, "thumbnails.json"), "w"), indent=1)
done = [os.path.join(Y, results[k]["mobile"]) for k in sorted(results) if os.path.isfile(os.path.join(Y, results[k]["mobile"]))]
if done:                                                  # a side-by-side sheet to compare them
    cmd = ["ffmpeg", "-y", "-v", "error"]
    for f in done:
        cmd += ["-i", f]
    cmd += ["-filter_complex", "".join("[%d:v]scale=640:360[s%d];" % (k, k) for k in range(len(done))) +
            ("".join("[s%d]" % k for k in range(len(done))) + "hstack=inputs=%d" % len(done) if len(done) > 1 else "[s0]null"),
            "-q:v", "3", os.path.join(Y, "thumbnails.jpg")]
    run(cmd, quiet=True)
sys.exit(0 if made == len(opts) else 1)
