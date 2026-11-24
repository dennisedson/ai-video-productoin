#!/usr/bin/env python3
"""drive.py: copy a finished video and its YouTube files to the team's Google Drive folder (Drive for desktop).

  python3 drive.py videos/NAME [--dry-run] [--month YYYY-MM] [--no-video]

Where: the profile's youtube.json "drive": {"root": <path under the Drive mount>, "series": {<campaign>: <folder>}}.
The mount is ~/Library/CloudStorage/GoogleDrive-*/ (the one where root exists); DRIVE_ROOT (an absolute path, e.g. in
pipeline/config.sh) overrides it on a Mac whose Drive sits elsewhere. Files land in <root>/<year>/<month>/<series>/:
the month folder is the existing one whose name starts with the month's number ("11_November", "05-May"), else a new
"MM_Month"; a video outside a named series goes straight into the month folder. The month is when the video was
finished (state.json: done or youtube-ready), else today; --month overrides it.

What: the finished video(s) at the top of videos/NAME/, youtube/thumbnail-N.jpg, captions.srt and YOUTUBE.md; all but
the video are prefixed with NAME ("agentcli-captions.srt"). A file already there with the same size is skipped (a video
uploaded by hand counts, under any name in that folder). Copies go to a temporary name first, so Drive never syncs a
half-written file. Writes youtube/drive.json (where everything went).
"""
import argparse, glob, json, os, re, shutil, sys, time

ap = argparse.ArgumentParser()
ap.add_argument("project"); ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--month", default="")
ap.add_argument("--no-video", action="store_true", help="leave the video out (the published one is already in Drive under another name)")
a = ap.parse_args()
W = os.path.abspath(a.project.rstrip("/")); NAME = os.path.basename(W); Y = os.path.join(W, "youtube")
SK = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
load = lambda p, d=None: json.load(open(p)) if os.path.isfile(p) else d

if not os.path.isdir(W):
    sys.exit("no video folder %s" % W)
tl = load(os.path.join(Y, "timeline.json"), {}) or {}
src = load(os.path.join(Y, "source.json"), {}) or {}
story = load(os.path.join(W, "storyboard.json"), {}) or {}
meta = load(os.path.join(Y, "metadata.json"), {}) or {}
prof = tl.get("profile") or story.get("profile") or src.get("profile") or ""
ycfg = load(os.path.join(SK, "profiles", prof, "youtube.json"), {}) if prof else {}
dcfg = (ycfg or {}).get("drive") or {}
if not dcfg.get("root") and not os.environ.get("DRIVE_ROOT"):
    sys.exit("the %s profile has no Drive folder (youtube.json \"drive\": {\"root\": ...})" % (prof or "(no)"))

root = os.environ.get("DRIVE_ROOT", "").strip()
if root:
    root = os.path.expanduser(root)
else:
    mounts = sorted(m for m in glob.glob(os.path.expanduser("~/Library/CloudStorage/GoogleDrive-*")) if " (" not in os.path.basename(m))
    hits = [os.path.join(m, dcfg["root"]) for m in mounts if os.path.isdir(os.path.join(m, dcfg["root"]))]
    if not hits:
        sys.exit("Google Drive folder not found: %s under %s (is Drive for desktop running and signed in? or set DRIVE_ROOT)"
                 % (dcfg["root"], ", ".join(mounts) or "no ~/Library/CloudStorage/GoogleDrive-* mount"))
    root = hits[0]
if not os.path.isdir(root):
    sys.exit("Drive folder not found: %s" % root)

# ---- the month ------------------------------------------------------------------------------------------------------
if a.month:
    m = re.fullmatch(r"(\d{4})-(\d{1,2})", a.month)
    if not m:
        sys.exit("--month YYYY-MM")
    year, mon = int(m.group(1)), int(m.group(2))
else:
    st = load(os.path.join(W, "state.json"), {}) or {}
    when = [h["at"] for h in st.get("history", []) if h.get("stage") in ("done", "youtube-ready")]
    t = time.strptime(when[-1][:10], "%Y-%m-%d") if when else time.localtime()
    year, mon = t.tm_year, t.tm_mon
ydir = os.path.join(root, str(year))
mname = None
if os.path.isdir(ydir):
    for d in sorted(os.listdir(ydir)):
        if os.path.isdir(os.path.join(ydir, d)) and re.match(r"0?%d(\D|$)" % mon, d):
            mname = d; break
if not mname:
    mname = "%02d_%s" % (mon, time.strftime("%B", time.strptime(str(mon), "%m")))
series = (dcfg.get("series") or {}).get(meta.get("campaign") or "", "")
dest = os.path.join(ydir, mname, series) if series else os.path.join(ydir, mname)

# ---- the files ------------------------------------------------------------------------------------------------------
files = []                                                  # (source, name in Drive, is the video)
for f in sorted(glob.glob(os.path.join(W, "*.mp4")) + glob.glob(os.path.join(W, "*.mov"))):
    files.append((f, os.path.basename(f), True))
if not a.no_video and not any(v for _, _, v in files):
    sys.exit("no finished video at the top of %s (import the render first: yt import %s VIDEO)" % (W, NAME))
for f in sorted(glob.glob(os.path.join(Y, "thumbnail-[0-9].jpg")) + glob.glob(os.path.join(Y, "thumbnail-[0-9][0-9].jpg"))):
    files.append((f, "%s-%s" % (NAME, os.path.basename(f)), False))
if a.no_video:
    files = [x for x in files if not x[2]]
for n in ("captions.srt", "YOUTUBE.md"):
    if os.path.isfile(os.path.join(Y, n)):
        files.append((os.path.join(Y, n), "%s-%s" % (NAME, n), False))

there = {}                                                  # size -> names already in the folder (videos uploaded by hand)
if os.path.isdir(dest):
    for n in os.listdir(dest):
        p = os.path.join(dest, n)
        if os.path.isfile(p):
            there.setdefault(os.path.getsize(p), []).append(n)

print("Drive: %s" % os.path.relpath(dest, os.path.dirname(root)))
done, copied = [], 0
for s, n, is_video in files:
    size = os.path.getsize(s); target = os.path.join(dest, n)
    if os.path.isfile(target) and os.path.getsize(target) == size:
        print("  same   %s" % n); done.append({"file": n, "status": "already there"}); continue
    if is_video and size in there:
        print("  same   %s (already there as %s)" % (n, there[size][0])); done.append({"file": there[size][0], "status": "already there"}); continue
    print("  %s %s (%.1f MB)" % ("would copy" if a.dry_run else "copy  ", n, size / 1e6))
    if a.dry_run:
        continue
    os.makedirs(dest, exist_ok=True)
    tmp = os.path.join(dest, ".%s.part" % n)
    shutil.copyfile(s, tmp); os.replace(tmp, target)
    copied += 1; done.append({"file": n, "status": "copied"})
if not a.dry_run:
    json.dump({"folder": dest, "at": time.strftime("%Y-%m-%d %H:%M"), "files": done}, open(os.path.join(Y, "drive.json"), "w"), indent=1)
print("%s: %d copied, %d already there" % ("dry run" if a.dry_run else "done", copied, sum(1 for d in done if d["status"] != "copied")))
