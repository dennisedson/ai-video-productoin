#!/usr/bin/env python3
"""remote-render.py: the work Mac's side of rendering on the home Mac (the render host).

The host is the home Mac's Video folder, reached one of two ways:
  /Volumes/Video                 mounted as a network share (SMB) on this Mac
  user@host:/path/to/Video       over SSH (Remote Login on the home Mac, a key on this Mac); an ~/.ssh/config alias
                                 works as the host. Use this when the network or company software blocks file sharing.
This script copies the render bundle into <host>/videos/_render-inbox/<name>/, waits while the home Mac's render agent
(render-host.sh) runs render-mac.sh on it, copies the finished video back and delivers it here, then removes the
bundle from the home Mac. No AI runs on either side.

  python3 remote-render.py --check --host HOST          exit 0 = the home Mac can take a render, 3 = not
  python3 remote-render.py --project videos/NAME --host HOST [--keep] [--poll 20] [--timeout-h 8]
  python3 remote-render.py --project videos/NAME --zip ~/Desktop   the hand-off: the same bundle as one zip
                                 (<name>-render.zip) to carry over by hand, e.g. dragged through Screen Sharing into
                                 the home Mac's videos/_render-inbox/; import the result with import-render.py

The bundle is what render-mac.sh reads: render.json, storyboard.json, cut-list.json, chapters/notes files, the face
file named by render.json's face_raw, and public/ without the files the render rebuilds (input-video.mp4 when face_raw
is set, face-crop.mp4 when face_crop is set, the HyperFrames cache).
"""
import argparse, io, json, os, re, shlex, shutil, socket, subprocess, sys, tarfile, tempfile, time

ap = argparse.ArgumentParser()
ap.add_argument("--host", help="the home Mac's Video folder: a mounted path, or user@host:/path for SSH")
ap.add_argument("--zip", metavar="DIR", help="write the bundle as DIR/<name>-render.zip for a hand-off, then stop")
ap.add_argument("--project", help="videos/NAME on this Mac")
ap.add_argument("--check", action="store_true", help="only say whether the home Mac can take a render")
ap.add_argument("--keep", action="store_true", help="leave the bundle on the home Mac after a successful render")
ap.add_argument("--poll", type=float, default=20.0)
ap.add_argument("--timeout-h", type=float, default=8.0)
ap.add_argument("--max-heartbeat-age", type=float, default=300.0, help="seconds; the home agent touches it every minute")
a = ap.parse_args()


def say(*m):
    print(time.strftime("%H:%M:%S"), *m, flush=True)


class Lost(Exception):
    """The home Mac can't be reached right now (the share dropped, SSH failed)."""


SKILL_REL = ".claude/skills/youtube-edit/scripts/render-mac.sh"
INBOX_REL = "videos/_render-inbox"


def heartbeat_problem(age):
    if age > a.max_heartbeat_age:
        return "the home Mac's render agent last checked in %d min ago (asleep, logged out, or stopped)" % (age // 60)
    return None


class MountedHost:
    """The home Mac's Video folder mounted as a share at a local path."""

    def __init__(self, path):
        self.root = os.path.abspath(os.path.expanduser(path))
        self.inbox = os.path.join(self.root, INBOX_REL)
        self.label = self.root

    def problem(self):
        if not os.path.isdir(self.root):
            return "%s is not mounted" % self.root
        if not os.path.isfile(os.path.join(self.root, SKILL_REL)):
            return "%s is mounted but is not the Video folder (no render-mac.sh)" % self.root
        hb = os.path.join(self.inbox, ".host-alive")
        if not os.path.isfile(hb):
            return "the render agent is not installed on the home Mac (install.sh --serve-renders there)"
        return heartbeat_problem(time.time() - os.path.getmtime(hb))

    def send(self, W, files, name, job_info):
        os.makedirs(self.inbox, exist_ok=True)
        job, partial = os.path.join(self.inbox, name), os.path.join(self.inbox, name + ".partial")
        for d in (partial, job):                          # a previous job with this name is replaced
            if os.path.exists(d):
                shutil.rmtree(d)
        total, done = sum(s for _, s in files), 0
        try:
            for rel, size in files:
                dst = os.path.join(partial, rel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copyfile(os.path.join(W, rel), dst)
                done += size
                if size > 200e6:
                    say("  %s (%.2f GB) copied, %.0f%% sent" % (rel, size / 1e9, 100 * done / max(total, 1)))
            json.dump(job_info, open(os.path.join(partial, "job.json"), "w"), indent=1)
            os.rename(partial, job)                        # the home agent only takes whole folders
        except OSError as e:
            raise Lost("the copy to the share broke off (%s)" % e)

    def status(self, name):
        job = os.path.join(self.inbox, name)
        try:
            if not os.path.isdir(job):
                raise Lost("job folder gone")
            p = os.path.join(job, "status.json")
            return json.load(open(p)) if os.path.exists(p) else {"stage": "queued"}
        except ValueError:
            return {"stage": "queued"}                     # caught mid-write; the next poll reads it
        except OSError as e:
            raise Lost(str(e))

    def fetch(self, name, rels, dest):
        """Copy files from the job folder (relative paths; missing ones skipped) into dest. Returns the copied names."""
        got = []
        for rel in rels:
            src = os.path.join(self.inbox, name, rel)
            if os.path.isfile(src):
                shutil.copyfile(src, os.path.join(dest, os.path.basename(rel))); got.append(os.path.basename(rel))
        return got

    def list_out(self, name):
        d = os.path.join(self.inbox, name, "out")
        return sorted(f for f in os.listdir(d) if not f.startswith(".")) if os.path.isdir(d) else []

    def remove(self, name):
        shutil.rmtree(os.path.join(self.inbox, name), ignore_errors=True)


class SSHHost:
    """The home Mac's Video folder over SSH: user@host:/path. Needs a key (BatchMode: never a password prompt)."""

    OPTS = ["-o", "BatchMode=yes", "-o", "ConnectTimeout=8", "-o", "ServerAliveInterval=15",
            "-o", "ServerAliveCountMax=4"]

    def __init__(self, spec):
        self.dest, path = spec.split(":", 1)
        self.root = path.rstrip("/") or "/"
        self.inbox = self.root + "/" + INBOX_REL
        self.label = spec

    def _cmd(self, script):
        return ["ssh"] + self.OPTS + [self.dest, "/bin/sh -c " + shlex.quote(script)]

    def run(self, script, check=True):
        try:
            r = subprocess.run(self._cmd(script), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except OSError as e:
            raise Lost("ssh: %s" % e)
        if r.returncode == 255:                            # ssh itself failed: unreachable, refused, no key
            raise Lost("can't reach %s over SSH (%s)" % (self.dest, r.stderr.decode(errors="replace").strip()[-200:]))
        if check and r.returncode != 0:
            raise RuntimeError("on the home Mac: %s" % r.stderr.decode(errors="replace").strip()[-300:])
        return r

    def problem(self):
        q = shlex.quote
        hb = q(self.inbox + "/.host-alive")
        script = ("test -f %s || { echo NOTVIDEO; exit 0; }; test -f %s || { echo NOAGENT; exit 0; }; "
                  "now=$(date +%%s); m=$(stat -c %%Y %s 2>/dev/null || stat -f %%m %s); echo AGE $((now - m))"
                  % (q(self.root + "/" + SKILL_REL), hb, hb, hb))
        try:
            out = self.run(script).stdout.decode().strip()
        except (Lost, RuntimeError) as e:
            return str(e)
        if out == "NOTVIDEO":
            return "%s on %s is not the Video folder (no render-mac.sh)" % (self.root, self.dest)
        if out == "NOAGENT":
            return "the render agent is not installed on the home Mac (install.sh --serve-renders there)"
        m = re.match(r"AGE (-?\d+)", out)
        if not m:
            return "unexpected answer from the home Mac: %r" % out[:200]
        return heartbeat_problem(float(m.group(1)))

    def send(self, W, files, name, job_info):
        q = shlex.quote
        job, partial = self.inbox + "/" + name, self.inbox + "/" + name + ".partial"
        self.run("rm -rf %s %s && mkdir -p %s" % (q(job), q(partial), q(partial)))
        p = subprocess.Popen(self._cmd("COPYFILE_DISABLE=1 tar xf - -C %s" % q(partial)), stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        total, done = sum(s for _, s in files), 0
        try:                                               # one tar stream: the media straight from disk, then job.json
            with tarfile.open(fileobj=p.stdin, mode="w|") as tf:
                for rel, size in files:
                    tf.add(os.path.join(W, rel), arcname=rel, recursive=False)
                    done += size
                    if size > 200e6:
                        say("  %s (%.2f GB) sent, %.0f%% of the bundle" % (rel, size / 1e9, 100 * done / max(total, 1)))
                data = json.dumps(job_info, indent=1).encode()
                ti = tarfile.TarInfo("job.json"); ti.size = len(data); ti.mtime = time.time()
                tf.addfile(ti, io.BytesIO(data))
            p.stdin.close()
        except (BrokenPipeError, OSError) as e:
            p.kill(); p.wait()
            raise Lost("the SSH copy broke off (%s)" % e)
        err = p.stderr.read().decode(errors="replace"); rc = p.wait()
        if rc == 255:
            raise Lost("the SSH copy broke off (%s)" % err.strip()[-200:])
        if rc != 0:
            raise RuntimeError("tar on the home Mac failed: %s" % err.strip()[-300:])
        self.run("mv %s %s" % (q(partial), q(job)))       # the home agent only takes whole folders

    def status(self, name):
        q = shlex.quote
        job = self.inbox + "/" + name
        out = self.run("test -d %s || { echo GONE; exit 0; }; cat %s 2>/dev/null || echo '{\"stage\": \"queued\"}'"
                       % (q(job), q(job + "/status.json"))).stdout.decode().strip()
        if out == "GONE":
            raise Lost("job folder gone")
        try:
            return json.loads(out)
        except ValueError:
            return {"stage": "queued"}                     # caught mid-write; the next poll reads it

    def fetch(self, name, rels, dest):
        """Copy files from the job folder (relative paths; missing ones skipped) into dest, streamed through tar."""
        q = shlex.quote
        script = "cd %s && for f in %s; do [ -f \"$f\" ] && COPYFILE_DISABLE=1 tar cf - \"$f\"; done; true" % (
            q(self.inbox + "/" + name), " ".join(q(r) for r in rels))
        p = subprocess.Popen(self._cmd(script), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        got = []
        try:                                               # concatenated archives: read member by member, ignore zeros
            with tarfile.open(fileobj=p.stdout, mode="r|", ignore_zeros=True) as tf:
                for m in tf:
                    if not m.isfile() or os.path.basename(m.name).startswith("._"):   # macOS tar metadata
                        continue
                    with tf.extractfile(m) as src, open(os.path.join(dest, os.path.basename(m.name)), "wb") as out:
                        shutil.copyfileobj(src, out, 8 << 20)
                    got.append(os.path.basename(m.name))
        except tarfile.ReadError:
            pass                                           # nothing to read: none of the files exist
        err = p.stderr.read().decode(errors="replace"); rc = p.wait()
        if rc == 255:
            raise Lost("the SSH copy back broke off (%s)" % err.strip()[-200:])
        return got

    def list_out(self, name):
        r = self.run("ls -1 %s 2>/dev/null || true" % shlex.quote(self.inbox + "/" + name + "/out"))
        return sorted(f for f in r.stdout.decode().split("\n") if f and not f.startswith("."))

    def remove(self, name):
        self.run("rm -rf %s" % shlex.quote(self.inbox + "/" + name), check=False)


def make_host(spec):
    # user@host:/path or alias:/path is SSH; a path (absolute, ~, or relative) is a mounted share
    if not spec.startswith(("/", "~", ".")) and re.match(r"^[^/:]+:", spec):
        return SSHHost(spec)
    return MountedHost(spec)


if not a.host and not a.zip:
    sys.exit("--host is required (or --zip DIR for a hand-off)")
if a.host == "handoff" and a.check:
    print("renders are handed off by hand: yt run NAME render makes the bundle zip (yt bundle NAME), yt import brings it back")
    sys.exit(0)
host = make_host(a.host) if a.host and not a.zip else None

if a.check:
    p = host.problem()
    print(p or "home Mac ready: %s" % host.label)
    sys.exit(3 if p else 0)

if not a.project:
    sys.exit("--project is required unless --check")
W = os.path.abspath(a.project.rstrip("/"))
cfg = json.load(open(os.path.join(W, "render.json")))
name = os.path.basename(W)
if host:
    p = host.problem()
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
info = {"name": name, "from": socket.gethostname(), "sent_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "files": len(files), "bytes": total}

if a.zip:                                                  # the hand-off: one zip, job.json last (the home Mac checks it)
    import zipfile
    outdir = os.path.abspath(os.path.expanduser(a.zip)); os.makedirs(outdir, exist_ok=True)
    out = os.path.join(outdir, "%s-render.zip" % name); tmpz = out + ".partial"
    info["via"] = "handoff"
    say("packing %d files, %.2f GB" % (len(files), total / 1e9))
    t0 = time.time()
    with zipfile.ZipFile(tmpz, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as z:   # video doesn't compress
        for rel, size in files:
            z.write(os.path.join(W, rel), arcname=name + "/" + rel)
        z.writestr(name + "/job.json", json.dumps(info, indent=1))
    os.replace(tmpz, out)
    say("packed in %d s: %s (%.2f GB)" % (time.time() - t0, out, os.path.getsize(out) / 1e9))
    print("BUNDLE\t%s" % out)
    sys.exit(0)
say("sending %d files, %.2f GB, to %s" % (len(files), total / 1e9, host.label))
t0 = time.time()
try:
    host.send(W, files, name, info)
except Lost as e:
    say("cannot render on the home Mac: %s" % e)
    sys.exit(3)
mb = total / 1e6 / max(time.time() - t0, 0.001)
say("sent in %d s (%.0f MB/s); waiting for the home Mac to pick it up" % (time.time() - t0, mb))


# ---- 2. wait --------------------------------------------------------------------------------------------------------
deadline = time.time() + a.timeout_h * 3600
last, lost_since, st = None, None, {}
while True:
    try:
        st = host.status(name)
        lost_since = None
    except Lost as e:
        lost_since = lost_since or time.time()
        if time.time() - lost_since > 600:
            say("lost the home Mac for 10 min (%s). The render may still finish there: %s/%s" % (e, host.inbox, name))
            sys.exit(1)
        time.sleep(a.poll); continue
    line = "%s %s" % (st.get("stage"), st.get("step", ""))
    if line != last:
        say("home Mac:", line.strip()); last = line
    if st.get("stage") in ("done", "failed"):
        break
    if time.time() > deadline:
        say("gave up after %.1f h; the job is still on the home Mac: %s/%s" % (a.timeout_h, host.inbox, name))
        sys.exit(1)
    time.sleep(a.poll)

tmp = tempfile.mkdtemp(prefix="remote-render-")         # the logs come back either way
for f in host.fetch(name, ["render.log", "render-host.log", "VERIFY.md"], tmp):
    shutil.move(os.path.join(tmp, f), os.path.join(W, "render-remote.log" if f == "render.log" else f))
if st["stage"] == "failed":
    say("the render failed on the home Mac: %s" % st.get("error", "?"))
    say("log: %s/render-remote.log. The bundle stays on the home Mac (%s/%s); run yt run %s render again to resend it,"
        % (W, host.inbox, name, name))
    say("or resume there: bash .claude/skills/youtube-edit/scripts/render-mac.sh videos/_render-inbox/%s --from STEP" % name)
    sys.exit(1)


# ---- 3. fetch and deliver -------------------------------------------------------------------------------------------
outs = host.list_out(name)
if not any(f.endswith(".mp4") for f in outs):
    say("the home Mac says done but out/ has no video: %s/%s/out" % (host.inbox, name)); sys.exit(1)
deliver = os.path.expanduser(cfg.get("deliver") or "~/Movies/YouTube Renders/%s" % cfg.get("name", name))
os.makedirs(deliver, exist_ok=True)
t0 = time.time()
got = host.fetch(name, ["out/" + f for f in outs], tmp)
if sorted(got) != outs:
    say("copied back %s of %s; the job stays on the home Mac" % (got, outs)); sys.exit(1)
for f in got:
    shutil.copyfile(os.path.join(tmp, f), os.path.join(W, f))   # the project folder keeps a copy, as a local render would
    shutil.move(os.path.join(tmp, f), os.path.join(deliver, f))
shutil.rmtree(tmp, ignore_errors=True)
say("fetched %s in %d s; delivered to %s" % (", ".join(got), time.time() - t0, deliver))
if not a.keep:
    host.remove(name)
    say("removed the bundle from the home Mac")
print("DELIVERED\t%s" % deliver)
