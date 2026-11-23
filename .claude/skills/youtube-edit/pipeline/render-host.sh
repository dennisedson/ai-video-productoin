#!/bin/bash
# render-host.sh: on the home Mac (the render host). launchd runs it every minute and when videos/_render-inbox changes.
# The work Mac (remote-render.py) copies a render bundle into videos/_render-inbox/<name>/ through the mounted share;
# this starts render-host-job.sh on it, one render at a time. Installed by install.sh --serve-renders.
. "$(cd "$(dirname "$0")" && pwd)/lib.sh"
HIN="$ROOT/videos/_render-inbox"; mkdir -p "$HIN"
touch "$HIN/.host-alive"                                  # the work Mac checks this before sending
L="$HIN/.lock"

# A hand-off: <name>-render.zip dragged in by hand (Screen Sharing). Unpack it once it has stopped growing and opens as
# a whole zip; the folder it makes is then taken like any other bundle below.
for z in "$HIN"/*-render.zip; do
  [ -f "$z" ] || continue
  s1=$(wc -c < "$z"); sleep 10; s2=$(wc -c < "$z")
  [ "$s1" = "$s2" ] || { log "render host: $(basename "$z") still copying"; continue; }
  if python3 - "$z" "$HIN" <<'PY'
import json, os, shutil, sys, zipfile
z, hin = sys.argv[1], sys.argv[2]
try:
    zf = zipfile.ZipFile(z)
except (zipfile.BadZipFile, OSError):
    sys.exit(2)                                            # not whole yet
names = zf.namelist()
top = {n.split("/", 1)[0] for n in names}
if len(top) != 1 or any(n.startswith("/") or ".." in n.split("/") for n in names):
    print("render host: %s is not a render bundle" % os.path.basename(z)); sys.exit(3)
name = top.pop()
if name + "/job.json" not in names:
    print("render host: %s has no job.json" % os.path.basename(z)); sys.exit(3)
tmp = os.path.join(hin, ".unzip-" + name)
shutil.rmtree(tmp, ignore_errors=True)
zf.extractall(tmp)
job = os.path.join(hin, name)
shutil.rmtree(job, ignore_errors=True)                     # a previous job with this name is replaced
os.rename(os.path.join(tmp, name), job)
shutil.rmtree(tmp, ignore_errors=True)
print("render host: unpacked %s" % name)
PY
  then rm -f "$z"; log "render host: unpacked $(basename "$z")"
  else
    rc=$?
    [ "$rc" = 3 ] && { mv "$z" "$z.rejected"; notify "Render host" "$(basename "$z") isn't a render bundle; left as .rejected."; }
  fi
done

if [ -d "$L" ]; then                                      # a render is running, or one died
  pid="$(cat "$L/pid" 2>/dev/null)"
  if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then exit 0; fi
  if [ -z "$pid" ] && [ -n "$(find "$L" -maxdepth 0 -mmin -1 2>/dev/null)" ]; then exit 0; fi   # just being started
  for s in "$HIN"/*/status.json; do                       # the render that held the lock stopped without finishing
    [ -f "$s" ] || continue
    python3 - "$s" <<'PY'
import json, os, sys, time
p = sys.argv[1]; s = json.load(open(p))
if s.get("stage") == "rendering":
    s.update(stage="failed", error="the render stopped (the Mac restarted or the render agent was stopped)",
             at=time.strftime("%Y-%m-%d %H:%M:%S"))
    json.dump(s, open(p + ".tmp", "w"), indent=1); os.replace(p + ".tmp", p)
PY
  done
  rm -rf "$L"; log "render host: cleared a stale lock"
fi

for d in "$HIN"/*/; do
  [ -d "$d" ] || continue
  n="$(basename "$d")"
  case "$n" in .*|_*|*.partial) continue ;; esac
  [ -f "$d/job.json" ] || continue                       # not a whole bundle
  [ -f "$d/status.json" ] && continue                    # already taken
  mkdir "$L" 2>/dev/null || exit 0
  nohup bash "$PIPE/render-host-job.sh" "$n" > "$d/render-host.log" 2>&1 &
  echo $! > "$L/pid"
  log "render host: $n started (pid $!)"
  exit 0
done
