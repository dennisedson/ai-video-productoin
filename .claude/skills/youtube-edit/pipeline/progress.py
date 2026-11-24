#!/usr/bin/env python3
"""progress.py: the table `yt status` prints, with a progress column. No AI, read-only.

  python3 progress.py ROOT

Per video (videos/*/state.json):
  rendering     a real percentage: render-mac.sh's steps from render.log, weighted by how long each step took in this
                Mac's earlier renders, and HyperFrames' own percentage (frames) inside the render step; minutes left.
  cutting,      an estimate, marked "~": the Claude run reports no progress, so elapsed time against the median of this
  storyboarding Mac's earlier runs of the same stage, plus the step it is on. No earlier runs: the step and minutes so far.
  waiting ones  what it is waiting for.
On the home Mac, hand-off and remote jobs in videos/_render-inbox/ are listed under the videos, with their render's
progress, and a zip still arriving shows its size so far.
"""
import datetime as dt, glob, json, os, re, statistics, sys, time

ROOT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
NOW = dt.datetime.strptime(os.environ["PROGRESS_NOW"], "%Y-%m-%d %H:%M:%S") if os.environ.get("PROGRESS_NOW") else dt.datetime.now()   # tests set it
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
STEPS = ["flatcut", "facecrop", "compose", "check", "render", "tags", "loudness", "verify", "card", "bookends", "deliver"]
DEFAULT_S = {"flatcut": 510, "facecrop": 60, "compose": 5, "check": 15, "render": 930, "tags": 2, "loudness": 150,
             "verify": 25, "card": 20, "bookends": 200, "deliver": 15}   # the home Mac's agents-2 render, 2026-11-22
STEP_WORDS = {"flatcut": "4K flat cut", "facecrop": "face crop", "compose": "compose", "check": "checks",
              "render": "4K render", "tags": "colour tags", "loudness": "loudness", "verify": "verify",
              "card": "face-card check", "bookends": "intro and end card", "deliver": "delivering"}
HF = re.compile(r"(\d{1,3})%\s+(Extracting video frames|Streaming frame (\d+)/(\d+)|Encoding frame (\d+)/(\d+)|"
                r"Assembling final video|Render complete)")


def mins(s):
    s = max(0, int(s))
    return "%d min" % round(s / 60) if s >= 90 else "%d s" % s


def parse_runs(path):
    """render.log -> [ {start: datetime, steps: [(name, datetime, [lines])]} ] for each '---- date ----' run."""
    runs, cur, step = [], None, None
    try:
        lines = open(path, errors="replace").read().splitlines()
    except OSError:
        return runs
    for ln in lines:
        m = re.match(r"^---- \w{3} (\w{3}) +(\d+) (\d\d):(\d\d):(\d\d) \S+ (\d{4}) ----$", ln)
        if m:
            mon, day, H, M, S, Y = m.groups()
            try:
                cur = {"start": dt.datetime(int(Y), MONTHS.index(mon) + 1, int(day), int(H), int(M), int(S)), "steps": []}
            except ValueError:
                cur = None
            if cur:
                runs.append(cur)
            step = None; continue
        m = re.match(r"^== ([a-z]+) (\d\d):(\d\d):(\d\d)$", ln)
        if m and cur is not None and m.group(1) in STEPS:
            t = cur["start"].replace(hour=int(m.group(2)), minute=int(m.group(3)), second=int(m.group(4)))
            last = cur["steps"][-1][1] if cur["steps"] else cur["start"]
            while t < last - dt.timedelta(minutes=1):          # past midnight
                t += dt.timedelta(days=1)
            step = (m.group(1), t, []); cur["steps"].append(step); continue
        if step is not None and "%" in ln:
            step[2].append(ln)
    return runs


def learned_step_seconds():
    """Median seconds per render step from every render.log on this Mac (a step retried right after is left out)."""
    seen = {}
    for p in glob.glob(os.path.join(ROOT, "videos", "*", "render.log")) + \
             glob.glob(os.path.join(ROOT, "videos", "_render-inbox", "*", "render.log")):
        for run in parse_runs(p):
            st = run["steps"]
            for (a, ta, _), (b, tb, _) in zip(st, st[1:]):
                d = (tb - ta).total_seconds()
                if a != b and 0 <= d < 4 * 3600:
                    seen.setdefault(a, []).append(d)
    return {k: statistics.median(v) for k, v in seen.items() if v}


LEARNED = learned_step_seconds()


def weight(step):
    return max(LEARNED.get(step, DEFAULT_S[step]), 1.0)


def render_progress(W):
    """(pct, detail) for a render running in project folder W, from its render.log; None when there is no run."""
    runs = parse_runs(os.path.join(W, "render.log"))
    if not runs or not runs[-1]["steps"]:
        return None
    try:
        cfg = json.load(open(os.path.join(W, "render.json")))
    except (OSError, ValueError):
        cfg = {}
    plan = [s for s in STEPS
            if not (s == "flatcut" and not cfg.get("face_raw")) and not (s == "facecrop" and not cfg.get("face_crop"))
            and not (s == "card" and not (cfg.get("card") and cfg.get("face_windows")))
            and not (s == "bookends" and not cfg.get("bookends"))]
    run = runs[-1]
    name, started, lines = run["steps"][-1]
    if name not in plan:
        plan.append(name)
    done_steps = {s for s, _, _ in run["steps"][:-1]}
    if run["steps"][0][0] != plan[0]:                          # a --from resume: what came before it is done
        done_steps |= set(plan[:plan.index(run["steps"][0][0])])
    total = sum(weight(s) for s in plan)
    done = sum(weight(s) for s in plan if s in done_steps and s != name)
    elapsed = (NOW - started).total_seconds()
    frac, detail = None, STEP_WORDS.get(name, name)
    for ln in reversed(lines):                               # HyperFrames' own percentage (render, bookends)
        m = HF.search(ln)
        if m:
            frac = int(m.group(1)) / 100.0
            if m.group(3):
                detail += ", frame %s/%s" % (m.group(3), m.group(4))
            elif m.group(5):
                detail += ", encoding %s/%s" % (m.group(5), m.group(6))
            elif "Extracting" in m.group(2):
                detail += ", extracting frames"
            break
    if frac is None:
        frac = min(elapsed / weight(name), 0.95)
    left = (1 - frac) * weight(name) + sum(weight(s) for s in plan[plan.index(name) + 1:])
    pct = 100.0 * (done + frac * weight(name)) / total
    return pct, "%s · ~%s left" % (detail, mins(left))


def history_medians():
    """Median seconds of each Claude stage on this Mac: cutting -> awaiting-A, storyboarding -> awaiting-B."""
    seen = {"cutting": [], "storyboarding": [], "drafting": []}
    for p in glob.glob(os.path.join(ROOT, "videos", "*", "state.json")):
        try:
            h = json.load(open(p))["history"]
        except (OSError, ValueError, KeyError):
            continue
        for a, b in zip(h, h[1:]):
            if (a["stage"], b["stage"]) in (("cutting", "awaiting-A"), ("storyboarding", "awaiting-B"), ("drafting", "youtube-ready")):
                try:
                    d = (dt.datetime.strptime(b["at"], "%Y-%m-%d %H:%M:%S") - dt.datetime.strptime(a["at"], "%Y-%m-%d %H:%M:%S")).total_seconds()
                except ValueError:
                    continue
                if 0 < d < 12 * 3600:
                    seen[a["stage"]].append(d)
    return {k: statistics.median(v) for k, v in seen.items() if v}


MEDIANS = history_medians()
CUT_STEPS = [("screenshare-vfr", "screen to 30 fps"), ("audio-raw.wav", "audio"), ("transcribe", "transcribing"),
             ("auto-editor", "speech map"), ("paper-cut", "paper cut"), ("camera-check", "camera check"),
             ("screen-activity", "screen activity"), ("screen-windows", "screen windows"),
             ("checkpoint-a", "Claude: the cut"), ("checkpoint-b", "Claude: the storyboard"),
             ("youtube-meta.py prep", "timing"), ("youtube.md", "Claude: the YouTube metadata")]


def claude_stage_progress(W, stage, since):
    """(pct or None, detail) for cutting / storyboarding."""
    step = None
    try:
        for ln in open(os.path.join(W, "pipeline", "stage.log"), errors="replace").read().splitlines()[-400:]:
            if ln.startswith("==== ") and ln.endswith(" " + {"cutting": "cut", "storyboarding": "storyboard", "drafting": "youtube-only"}[stage]):
                step = None                                      # this run's start (stage.sh marks it)
            elif re.match(r"^== \d\d:\d\d:\d\d ", ln):
                for key, words in CUT_STEPS:
                    if key in ln:
                        step = words
    except OSError:
        pass
    elapsed = (NOW - since).total_seconds()
    step = step or "starting"
    med = MEDIANS.get(stage)
    if med:
        return min(100.0 * elapsed / med, 95.0), "%s · %s of ~%s" % (step, mins(elapsed), mins(med))
    return None, "%s · %s so far" % (step, mins(elapsed))


WAITING = {"awaiting-A": "ready to review (REVIEW-A)", "awaiting-B": "ready to review (REVIEW-B)",
           "awaiting-import": "zip on the Desktop; waiting for the video back (yt import)",
           "awaiting-host": "waiting for the home Mac (yt host)", "queued": "queued",
           "youtube-ready": "metadata ready: youtube/YOUTUBE.md (yt published NAME URL once it's live)"}


def youtube_note(W):
    try:
        st = open(os.path.join(W, "youtube", "status")).read().split()
    except OSError:
        return ""
    word = {"drafting": "drafting", "ready": "ready", "failed": "failed"}.get(st[0].rstrip(","), st[0])
    return " · YouTube: %s%s" % (word, " (problems)" if "problems" in st else "")


SUFFIX = ""      # set per video: its YouTube metadata note


def row(name, stage, pct, detail, est=False):
    p = "" if pct is None else ("~%d%%" if est else "%d%%") % round(pct)
    print("%-24s %-15s %5s  %s%s" % (name[:24], stage, p, detail, SUFFIX))


print("%-24s %-15s %5s  %s" % ("VIDEO", "STAGE", "", "PROGRESS / LAST CHANGE"))
for p in sorted(glob.glob(os.path.join(ROOT, "videos", "*", "state.json"))):
    W = os.path.dirname(p); name = os.path.basename(W)
    try:
        s = json.load(open(p)); h = s["history"][-1]; stage = s["stage"]
        since = dt.datetime.strptime(h["at"], "%Y-%m-%d %H:%M:%S")
    except (OSError, ValueError, KeyError):
        continue
    note = h.get("note", "")
    SUFFIX = youtube_note(W)
    if stage == "rendering" and "home Mac" not in note:
        r = render_progress(W)
        row(name, stage, r[0] if r else None, r[1] if r else "starting · %s" % mins((NOW - since).total_seconds()))
    elif stage == "rendering":
        row(name, stage, None, "on the home Mac · %s so far" % mins((NOW - since).total_seconds()))
    elif stage == "transcribing":
        row(name, stage, None, "transcribing · %s so far" % mins((NOW - since).total_seconds()))
    elif stage in ("cutting", "storyboarding", "drafting"):
        pct, detail = claude_stage_progress(W, stage, since)
        row(name, stage, pct, detail, est=True)
    elif stage in WAITING:
        row(name, stage, None, "%s · since %s" % (WAITING[stage], h["at"][5:16]))
    elif stage == "done":
        row(name, stage, 100.0, "finished %s%s" % (h["at"][5:16], " · " + note if note else ""))
    else:
        row(name, stage, None, "%s · %s" % (h["at"][5:16], note or stage))

SUFFIX = ""
# the home Mac: renders other Macs handed over (videos/_render-inbox)
HIN = os.path.join(ROOT, "videos", "_render-inbox")
jobs = sorted(glob.glob(os.path.join(HIN, "*-render.zip"))) + sorted(d for d in glob.glob(os.path.join(HIN, "*")) if os.path.isdir(d))
if jobs:
    print("render inbox (on this Mac):")
for j in jobs:
    base = os.path.basename(j)
    if j.endswith(".zip"):
        row("  " + base[:-len("-render.zip")], "arriving", None, "%.2f GB so far" % (os.path.getsize(j) / 1e9)); continue
    if base.startswith((".", "_")) or base.endswith(".partial") or not os.path.isfile(os.path.join(j, "job.json")):
        continue
    try:
        st = json.load(open(os.path.join(j, "status.json")))
    except (OSError, ValueError):
        st = {"stage": "queued"}
    if st.get("stage") == "rendering":
        r = render_progress(j)
        row("  " + base, "rendering", r[0] if r else None, r[1] if r else st.get("step", ""))
    elif st.get("stage") == "done":
        row("  " + base, "done", 100.0, "video in out/; drag it back, then yt clean-renders")
    elif st.get("stage") == "failed":
        row("  " + base, "failed", None, st.get("error", ""))
    else:
        row("  " + base, "queued", None, "waiting for the render agent")
