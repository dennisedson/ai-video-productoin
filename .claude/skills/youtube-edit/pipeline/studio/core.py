#!/usr/bin/env python3
"""core.py: the video project model the studio and `yt new` share.

A video is a folder videos/<name>/ with video.json (its phase and facts), the planning documents (BRIEF.md,
research.md, references.md, SCRIPT.md, results.md), questions.json, review comments, studio jobs, and everything
the pipeline writes (state.json, the cut, the storyboard, youtube/). A video made before the studio has no
video.json; it is read from state.json alone.

  python3 core.py new NAME --origin colleague|problem|feature|finished [--title T] [--series S] [--presenter P]
  python3 core.py ask NAME "question" [--options "a|b"]
"""
import datetime as dt, json, os, re, subprocess, sys, threading, time, uuid

HERE = os.path.dirname(os.path.abspath(__file__))
SK = os.path.normpath(os.path.join(HERE, "..", ".."))
ROOT = os.environ.get("STUDIO_ROOT") or os.path.normpath(os.path.join(SK, "..", "..", ".."))
PHASES = json.load(open(os.path.join(HERE, "phases.json")))["phases"]
PHASE_IDS = [p["id"] for p in PHASES]
ORIGINS = ("colleague", "problem", "feature", "finished")
REVIEWS = ("A", "B", "package")
_NAME = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
_lock = threading.Lock()


def now():
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M")


def slug(text):
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return re.sub(r"-{2,}", "-", s)


def videos_dir():
    return os.path.join(ROOT, "videos")


def video_dir(name):
    if not name or not _NAME.match(name) or ".." in name:
        raise ValueError("not a video name: %r" % name)
    return os.path.join(videos_dir(), name)


def inside(name, rel):
    """The absolute path of rel inside the video's folder; ValueError if it would leave it."""
    base = os.path.realpath(video_dir(name))
    p = os.path.realpath(os.path.join(base, rel))
    if p != base and not p.startswith(base + os.sep):
        raise ValueError("outside the video folder: %r" % rel)
    return p


def _read(p, default=None):
    try:
        return json.load(open(p))
    except (OSError, ValueError):
        return default


def _write(p, data):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
    os.replace(tmp, p)


def load_video(name):
    w = video_dir(name)
    v = _read(os.path.join(w, "video.json"), None)
    if v is None:                                          # a video from before the studio
        story = _read(os.path.join(w, "storyboard.json"), {}) or {}
        src = _read(os.path.join(w, "youtube", "source.json"), {}) or {}
        v = {"name": name, "title": "", "origin": "finished" if src.get("kind") == "metadata-only" else "",
             "profile": story.get("profile") or src.get("profile") or "", "phase": "", "phases": {}, "legacy": True}
    v.setdefault("name", name); v.setdefault("phases", {})
    meta = _read(os.path.join(w, "youtube", "metadata.json"), {}) or {}
    if not v.get("title") and meta.get("titles"):
        t = meta["titles"][0]
        v["title"] = t["title"] if isinstance(t, dict) else t
    return v


def save_video(name, data):
    data = {k: v for k, v in data.items() if k != "legacy"}
    _write(os.path.join(video_dir(name), "video.json"), data)


def state(name):
    return _read(os.path.join(video_dir(name), "state.json"), None)


_STAGE_PHASE = {"queued": "cut", "cutting": "cut", "awaiting-A": "cut", "storyboarding": "storyboard",
                "awaiting-B": "storyboard", "rendering": "render", "awaiting-import": "render", "awaiting-host": "render",
                "done": "packaging", "youtube-ready": "packaging", "youtube": "packaging"}


def derive_phase(video, st):
    """The phase to show: the pipeline's stage for the cut-to-render phases, video.json for the rest, whichever is later."""
    mine = video.get("phase") or ("packaging" if video.get("origin") == "finished" else "")
    stage = (st or {}).get("stage", "")
    if stage == "failed":                                  # a failed stage stays in the phase that failed
        hist = [h.get("stage") for h in (st or {}).get("history", []) if h.get("stage") != "failed"]
        stage = hist[-1] if hist else ""
    piped = _STAGE_PHASE.get(stage, "")
    cands = [p for p in (mine, piped) if p in PHASE_IDS]
    if not cands:
        return "ideation"
    return max(cands, key=PHASE_IDS.index)


def catalog_status(name):
    """'published' or 'scheduled' from catalog/VIDEOS.md (yt published writes it), else ''."""
    try:
        cat = open(os.path.join(ROOT, "catalog", "VIDEOS.md")).read()
    except OSError:
        return ""
    m = re.search(r"<!-- video:%s -->(.*?)<!-- /video:%s -->" % (re.escape(name), re.escape(name)), cat, re.S)
    st = re.search(r"^- \*\*Status:\*\* (\w+)", m.group(1), re.M) if m else None
    return st.group(1) if st and st.group(1) in ("published", "scheduled") else ""


def current_phase(name, v=None, st=None):
    v = v if v is not None else load_video(name)
    ph = derive_phase(v, st if st is not None else state(name))
    cs = catalog_status(name)
    want = "results" if cs == "published" else "publish" if cs == "scheduled" else ""
    if want and PHASE_IDS.index(want) > PHASE_IDS.index(ph):
        ph = want
    return ph


def phase(pid):
    for p in PHASES:
        if p["id"] == pid:
            return p
    raise KeyError(pid)


def waiting_on(video, st, open_q):
    stage = (st or {}).get("stage", "")
    if open_q:
        return "you: %d question%s" % (open_q, "" if open_q == 1 else "s")
    if video.get("name") and catalog_status(video["name"]) == "scheduled":
        return "its go-live date"
    return {"queued": "the cut stage", "cutting": "the cut stage", "storyboarding": "the storyboard stage",
            "rendering": "the render", "awaiting-import": "the home Mac", "awaiting-host": "the home Mac",
            "failed": "a fix (the stage failed)", "awaiting-A": "you: Checkpoint A", "awaiting-B": "you: Checkpoint B"}.get(stage, "you")


def list_videos():
    rows = []
    if not os.path.isdir(videos_dir()):
        return rows
    for n in sorted(os.listdir(videos_dir())):
        if n.startswith((".", "_")) or not _NAME.match(n) or not os.path.isdir(os.path.join(videos_dir(), n)):
            continue
        v, st = load_video(n), state(n)
        oq = sum(1 for q in questions(n) if not q.get("answer"))
        ph = current_phase(n, v, st)
        rows.append({"name": n, "title": v.get("title") or n, "phase": ph, "origin": v.get("origin", ""),
                     "series": v.get("series", ""), "stage": (st or {}).get("stage", ""), "open_questions": oq,
                     "waiting_on": waiting_on(v, st, oq), "legacy": bool(v.get("legacy")),
                     "updated": max((os.path.getmtime(os.path.join(videos_dir(), n, f)) for f in ("video.json", "state.json")
                                     if os.path.exists(os.path.join(videos_dir(), n, f))), default=0)})
    return rows


def scaffold(name, origin, title="", series="", profile="hubspot", presenter=""):
    if origin not in ORIGINS:
        raise ValueError("origin must be one of %s" % ", ".join(ORIGINS))
    w = video_dir(name)
    if os.path.exists(w):
        raise FileExistsError("videos/%s already exists" % name)
    os.makedirs(os.path.join(w, "raw"))
    for d in ("work", "snaps", "public", "review", "pipeline"):
        os.makedirs(os.path.join(w, d))
    tpl = os.path.join(HERE, "templates")
    fill = lambda s: s.replace("{{TITLE}}", title or name).replace("{{PRESENTER}}", presenter or "the colleague")
    brief = "BRIEF-%s.md" % (origin if origin in ("colleague", "problem", "feature") else "feature")
    files = {"BRIEF.md": brief, "research.md": "research.md", "references.md": "references.md", "SCRIPT.md": "SCRIPT.md",
             "results.md": "results.md"}
    for out, src in files.items():
        open(os.path.join(w, out), "w").write(fill(open(os.path.join(tpl, src)).read()))
    notes = ["Profile: %s" % profile] + (["Series: %s" % series] if series else []) + (["Presenter: %s" % presenter] if presenter else [])
    open(os.path.join(w, "notes.txt"), "w").write("\n".join(notes) + "\n")
    save_video(name, {"name": name, "title": title, "origin": origin, "series": series, "profile": profile,
                      "presenter": presenter, "phase": "packaging" if origin == "finished" else "ideation",
                      "phases": {}, "created": now()})
    return w


# ---- questions -----------------------------------------------------------------------------------------------------
def _qpath(name):
    return os.path.join(video_dir(name), "questions.json")


def questions(name):
    return _read(_qpath(name), []) or []


def ask(name, text, options=None, frm="claude"):
    with _lock:
        qs = questions(name)
        q = {"id": uuid.uuid4().hex[:8], "from": frm, "text": text, "options": options or [], "answer": "", "asked": now(), "answered": ""}
        qs.append(q); _write(_qpath(name), qs)
    return q


def answer(name, qid, text):
    with _lock:
        qs = questions(name)
        for q in qs:
            if q["id"] == qid:
                q["answer"], q["answered"] = text, now()
                _write(_qpath(name), qs)
                return q
    raise KeyError(qid)


# ---- review comments -----------------------------------------------------------------------------------------------
def _cpath(name, review):
    if review not in REVIEWS:
        raise ValueError("no such review: %r" % review)
    return os.path.join(video_dir(name), "review", "comments-%s.json" % review)


def comments(name, review):
    return _read(_cpath(name, review), []) or []


def save_comments(name, review, items):
    _write(_cpath(name, review), items)


# ---- jobs: background commands with a log the page can follow --------------------------------------------------------
_procs = {}


def _jdir(name):
    return os.path.join(video_dir(name), "studio", "jobs")


def start_job(name, kind, argv, env=None, cwd=None, label=""):
    jid = dt.datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:4]
    d = _jdir(name); os.makedirs(d, exist_ok=True)
    meta = {"id": jid, "kind": kind, "label": label or kind, "argv": argv, "started": now(), "finished": "", "exit": None}
    _write(os.path.join(d, jid + ".json"), meta)
    log = open(os.path.join(d, jid + ".log"), "w")
    e = dict(os.environ); e.update(env or {})
    p = subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT, cwd=cwd or ROOT, env=e)
    _procs[jid] = p

    def wait():
        rc = p.wait(); log.close()
        m = _read(os.path.join(d, jid + ".json"), meta) or meta
        m["exit"], m["finished"] = rc, now()
        _write(os.path.join(d, jid + ".json"), m)
        _procs.pop(jid, None)
    threading.Thread(target=wait, daemon=True).start()
    return jid


def wait_job(name, jid, timeout):
    end = time.time() + timeout
    while time.time() < end:
        j = job(name, jid)
        if j.get("exit") is not None:
            return j
        time.sleep(0.05)
    return job(name, jid)


def job(name, jid):
    if not re.match(r"^[0-9a-f-]+$", jid):
        raise ValueError(jid)
    d = _jdir(name)
    m = _read(os.path.join(d, jid + ".json"), None)
    if m is None:
        raise KeyError(jid)
    try:
        m["log"] = open(os.path.join(d, jid + ".log"), errors="replace").read()[-60000:]
    except OSError:
        m["log"] = ""
    m["running"] = m.get("exit") is None
    return m


def jobs(name, limit=20):
    d = _jdir(name)
    if not os.path.isdir(d):
        return []
    ids = sorted((f[:-5] for f in os.listdir(d) if f.endswith(".json")), reverse=True)[:limit]
    out = []
    for i in ids:
        m = _read(os.path.join(d, i + ".json"), None)
        if m:
            m["running"] = m.get("exit") is None
            out.append(m)
    return out


def main(argv):
    import argparse
    ap = argparse.ArgumentParser(prog="core.py")
    sub = ap.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("new"); n.add_argument("name"); n.add_argument("--origin", required=True, choices=ORIGINS)
    n.add_argument("--title", default=""); n.add_argument("--series", default=""); n.add_argument("--presenter", default="")
    n.add_argument("--profile", default="hubspot")
    q = sub.add_parser("ask"); q.add_argument("name"); q.add_argument("text"); q.add_argument("--options", default="")
    a = ap.parse_args(argv)
    if a.cmd == "new":
        name = slug(a.name)
        try:
            w = scaffold(name, a.origin, a.title, a.series, a.profile, a.presenter)
        except (FileExistsError, ValueError) as e:
            sys.exit(str(e))
        print("made %s (%s, phase %s)" % (os.path.relpath(w, ROOT), a.origin, load_video(name)["phase"]))
    elif a.cmd == "ask":
        q = ask(a.name, a.text, [o for o in a.options.split("|") if o] if a.options else None)
        print("asked %s: %s" % (q["id"], q["text"]))


if __name__ == "__main__":
    main(sys.argv[1:])
