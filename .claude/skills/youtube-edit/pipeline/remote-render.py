#!/usr/bin/env python3
"""remote-render.py: the work Mac's side of rendering on the home Mac (the render host).

The home Mac's Video folder is mounted on this Mac as a network share (for example /Volumes/Video). This script copies
the render bundle into <host>/videos/_render-inbox/<name>/, waits while the home Mac's render agent (render-host.sh)
runs render-mac.sh on it, copies the finished video back and delivers it here, then removes the bundle from the home
Mac. No AI runs on either side.

  python3 remote-render.py --check --host /Volumes/Video            exit 0 = the home Mac can take a render, 3 = not
  python3 remote-render.py --project videos/NAME --host /Volumes/Video [--keep] [--poll 20] [--timeout-h 8]

The bundle is what render-mac.sh reads: render.json, storyboard.json, cut-list.json, chapters/notes files, the face
file named by render.json's face_raw, and public/ without the files the render rebuilds (input-video.mp4 when face_raw
is set, face-crop.mp4 when face_crop is set, the HyperFrames cache). A 9.6 GB project folder sends about 1.5 GB.
"""
import argparse, json, os, shutil, socket, sys, time

ap = argparse.ArgumentParser()
ap.add_argument("--host", required=True, help="the home Mac's Video folder as mounted here")
ap.add_argument("--project", help="videos/NAME on this Mac")
ap.add_argument("--check", action="store_true", help="only say whether the home Mac can take a render")
ap.add_argument("--keep", action="store_true", help="leave the bundle on the home Mac after a successful render")
ap.add_argument("--poll", type=float, default=20.0)
ap.add_argument("--timeout-h", type=float, default=8.0)
ap.add_argument("--max-heartbeat-age", type=float, default=300.0, help="seconds; the home agent touches it every minute")
a = ap.parse_args()

HOST = os.path.abspath(os.path.expanduser(a.host))
HINBOX = os.path.join(HOST, "videos", "_render-inbox")


def say(*m):
    print(time.strftime("%H:%M:%S"), *m, flush=True)


def host_problem():
    """None when the home Mac can take a render, else why not."""
    if not os.path.isdir(HOST):
        return "%s is not mounted" % HOST
    if not os.path.isfile(os.path.join(HOST, ".claude/skills/youtube-edit/scripts/render-mac.sh")):
        return "%s is mounted but is not the Video folder (no render-mac.sh)" % HOST
    hb = os.path.join(HINBOX, ".host-alive")
    if not os.path.isfile(hb):
        return "the render agent is not installed on the home Mac (install.sh --serve-renders there)"
    age = time.time() - os.path.getmtime(hb)
    if age > a.max_heartbeat_age:
        return "the home Mac's render agent last checked in %d min ago (asleep, logged out, or stopped)" % (age // 60)
    return None


if a.check:
    p = host_problem()
    print(p or "home Mac ready: %s" % HOST)
    sys.exit(3 if p else 0)

if not a.project:
    sys.exit("--project is required unless --check")
W = os.path.abspath(a.project.rstrip("/"))
cfg = json.load(open(os.path.join(W, "render.json")))
name = os.path.basename(W)
p = host_problem()
if p:
    say("cannot render on the home Mac:", p)
    sys.exit(3)


# ---- 1. the bundle -------------------------------------------------------------------------------------------------
def bundle_files():
    """(relative path, size) of every file render-mac.sh needs."""
    out = []
    for f in sorted(os.listdir(W)):                       # top level: the small json/md/txt files only
        fp = os.path.join(W, f)
        if os.path.isfile(fp) and f.lower().endswith((".json", ".txt", ".md")) and not f.startswith("assembly-") \
                and f not in ("state.json", "status.json", "job.json"):
            out.append(f)
    face = cfg.get("face_raw") or ""
    if face:
        if not os.path.isfile(os.path.join(W, face)):
            sys.exit("render.json face_raw %s does not exist" % face)
        out.append(face)
    skip = set()
    if face:
        skip.add("public/input-video.mp4")
    elif not os.path.isfile(os.path.join(W, "public", "input-video.mp4")):
        sys.exit("no face_raw in render.json and no public/input-video.mp4")
    if cfg.get("face_crop"):
        skip.add("public/face-crop.mp4")
    pub = os.path.join(W, "public")
    for root, dirs, files in os.walk(pub):
        rel_root = os.path.relpath(root, W)
        dirs[:] = [d for d in dirs if not (rel_root == "public" and d == ".hyperframes")]
        for f in files:
            rel = os.path.join(rel_root, f)
            if rel not in skip and not f.startswith("._") and f != ".DS_Store":
                out.append(rel)
    return [(r, os.path.getsize(os.path.join(W, r))) for r in out]


files = bundle_files()
total = sum(s for _, s in files)
os.makedirs(HINBOX, exist_ok=True)
job = os.path.join(HINBOX, name)
partial = job + ".partial"
for d in (partial, job):                                  # a previous job with this name is replaced
    if os.path.exists(d):
        shutil.rmtree(d)
say("sending %d files, %.2f GB, to %s" % (len(files), total / 1e9, job))
t0, done = time.time(), 0
for rel, size in files:
    dst = os.path.join(partial, rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(os.path.join(W, rel), dst)
    done += size
    if size > 200e6:
        say("  %s (%.2f GB) copied, %.0f%% sent" % (rel, size / 1e9, 100 * done / max(total, 1)))
json.dump({"name": name, "from": socket.gethostname(), "sent_at": time.strftime("%Y-%m-%d %H:%M:%S"),
           "files": len(files), "bytes": total}, open(os.path.join(partial, "job.json"), "w"), indent=1)
os.rename(partial, job)                                    # the home agent only takes whole folders
mb = total / 1e6 / max(time.time() - t0, 0.001)
say("sent in %d s (%.0f MB/s); waiting for the home Mac to pick it up" % (time.time() - t0, mb))


# ---- 2. wait --------------------------------------------------------------------------------------------------------
status_path = os.path.join(job, "status.json")
deadline = time.time() + a.timeout_h * 3600
last, lost_since, st = None, None, {}
while True:
    try:
        st = json.load(open(status_path)) if os.path.exists(status_path) else {"stage": "queued"}
        if not os.path.isdir(job):
            raise OSError("job folder gone")
        lost_since = None
    except (OSError, ValueError) as e:
        if isinstance(e, ValueError):                      # caught mid-write; read again next poll
            time.sleep(a.poll); continue
        lost_since = lost_since or time.time()
        if time.time() - lost_since > 600:
            say("lost the home Mac for 10 min (%s). The render may still finish there: %s" % (e, job))
            sys.exit(1)
        time.sleep(a.poll); continue
    line = "%s %s" % (st.get("stage"), st.get("step", ""))
    if line != last:
        say("home Mac:", line.strip()); last = line
    if st.get("stage") in ("done", "failed"):
        break
    if time.time() > deadline:
        say("gave up after %.1f h; the job is still on the home Mac: %s" % (a.timeout_h, job))
        sys.exit(1)
    time.sleep(a.poll)

for f in ("render.log", "render-host.log", "VERIFY.md"):   # the logs come back either way
    if os.path.isfile(os.path.join(job, f)):
        shutil.copyfile(os.path.join(job, f), os.path.join(W, "render-remote.log" if f == "render.log" else f))
if st["stage"] == "failed":
    say("the render failed on the home Mac: %s" % st.get("error", "?"))
    say("log: %s/render-remote.log. The bundle stays on the home Mac (%s); run yt run %s render again to resend it,"
        % (W, job, name))
    say("or resume there: bash .claude/skills/youtube-edit/scripts/render-mac.sh videos/_render-inbox/%s --from STEP" % name)
    sys.exit(1)


# ---- 3. fetch and deliver -------------------------------------------------------------------------------------------
outdir = os.path.join(job, "out")
outs = sorted(f for f in os.listdir(outdir) if not f.startswith("."))
if not any(f.endswith(".mp4") for f in outs):
    say("the home Mac says done but out/ has no video: %s" % outdir); sys.exit(1)
deliver = os.path.expanduser(cfg.get("deliver") or "~/Movies/YouTube Renders/%s" % cfg.get("name", name))
os.makedirs(deliver, exist_ok=True)
t0 = time.time()
for f in outs:
    src = os.path.join(outdir, f)
    shutil.copyfile(src, os.path.join(W, f))              # the project folder keeps a copy, as a local render would
    shutil.copyfile(src, os.path.join(deliver, f))
    if os.path.getsize(src) != os.path.getsize(os.path.join(deliver, f)):
        say("size mismatch copying %s back" % f); sys.exit(1)
say("fetched %s in %d s; delivered to %s" % (", ".join(outs), time.time() - t0, deliver))
if not a.keep:
    shutil.rmtree(job)
    say("removed the bundle from the home Mac")
print("DELIVERED\t%s" % deliver)
