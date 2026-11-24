#!/usr/bin/env python3
"""core.py: the video project model the studio and `yt new` share.

A video is a folder videos/<name>/ with video.json (its phase and facts), the planning documents (BRIEF.md,
research.md, references.md, SCRIPT.md, results.md), questions.json, review comments, studio jobs, and everything
the pipeline writes (state.json, the cut, the storyboard, youtube/). A video made before the studio has no
video.json; it is read from state.json alone.

  python3 core.py new NAME --origin colleague|problem|feature|finished [--title T] [--series S] [--presenter P]
  python3 core.py ask NAME "question" [--options "a|b"]
  python3 core.py propose-split NAME --series "Title" --part "name::title::promise::minutes" ... [--why W]
"""
import datetime as dt, json, os, re, shutil, subprocess, sys, threading, time, uuid

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
    sr = v.get("series") or []
    v["series"] = [sr] if isinstance(sr, str) else list(sr)
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
                     "series": v.get("series", []), "minutes": estimate_minutes(n), "stage": (st or {}).get("stage", ""), "open_questions": oq,
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
    series = [series] if isinstance(series, str) and series else list(series or [])
    notes = ["Profile: %s" % profile] + (["Series: %s" % ", ".join(series)] if series else []) + (["Presenter: %s" % presenter] if presenter else [])
    open(os.path.join(w, "notes.txt"), "w").write("\n".join(notes) + "\n")
    save_video(name, {"name": name, "title": title, "origin": origin, "series": series, "profile": profile,
                      "presenter": presenter, "phase": "packaging" if origin == "finished" else "ideation",
                      "phases": {}, "created": now()})
    return w


# ---- length ---------------------------------------------------------------------------------------------------------
WPM = 150                                                  # Dennis's pace, from his transcripts (agentcli 1316 words in 6:26)
DEMO_S = 45


def profile_length(profile):
    y = _read(os.path.join(SK, "profiles", profile or "hubspot", "youtube.json"), {}) or {}
    L = y.get("length") or {}
    return float(L.get("target_minutes", 6)), float(L.get("max_minutes", 10))


def estimate_seconds(script):
    """Spoken length of SCRIPT.md: read-aloud words at WPM, each demo beat DEMO_S or its own '(~30s)' / '(~2m)'."""
    words, secs = 0, 0.0
    for line in script.splitlines():
        t = line.strip()
        if t.startswith(">"):
            words += len(t[1:].split())
        m = re.match(r"^(?:→|->)\s*demo:(.*)$", t, re.I)
        if m:
            d = re.search(r"\(~\s*(\d+(?:\.\d+)?)\s*(s|sec|m|min)\w*\)", m.group(1))
            secs += (float(d.group(1)) * (60 if d.group(2).startswith("m") else 1)) if d else DEMO_S
    return round(words / WPM * 60 + secs)


def estimate_minutes(name):
    """The best length we know: the cut (flat-cut duration) once there is one, else the script's estimate; None if neither."""
    w = video_dir(name)
    cm = _read(os.path.join(w, "cut-map.json"), None)
    if cm and cm.get("flat_duration"):
        return round(float(cm["flat_duration"]) / 60, 1)
    p = os.path.join(w, "SCRIPT.md")
    if os.path.isfile(p):
        text = open(p).read()
        reads = sum(len(l.strip()[1:].split()) for l in text.splitlines() if l.strip().startswith(">"))
        if reads < 20:                                     # still the template: no estimate yet
            return None
        return round(estimate_seconds(text) / 60, 1)
    return None


# ---- series ---------------------------------------------------------------------------------------------------------
def series_dir():
    return os.path.join(ROOT, "catalog", "series")


def all_series():
    d = series_dir(); out = []
    if os.path.isdir(d):
        for f in sorted(os.listdir(d)):
            if f.endswith(".json"):
                s = _read(os.path.join(d, f), None)
                if s:
                    out.append(s)
    known = {s["title"] for s in out}
    for n in (os.listdir(videos_dir()) if os.path.isdir(videos_dir()) else []):   # series named on a video but without a page yet
        if n.startswith((".", "_")) or not _NAME.match(n) or not os.path.isdir(os.path.join(videos_dir(), n)):
            continue
        for t in load_video(n).get("series", []):
            if t and t not in known:
                known.add(t); out.append({"slug": slug(t), "title": t, "parts": [], "page": False})
    return out


def get_series(sslug):
    s = _read(os.path.join(series_dir(), slug(sslug) + ".json"), None)
    if s is None:
        s = next((x for x in all_series() if x["slug"] == slug(sslug)), None)
        if s is None:
            raise KeyError(sslug)
    members = [n for n in (os.listdir(videos_dir()) if os.path.isdir(videos_dir()) else [])
               if not n.startswith((".", "_")) and _NAME.match(n) and os.path.isdir(os.path.join(videos_dir(), n))
               and s["title"] in load_video(n).get("series", [])]
    order = [p for p in s.get("parts", []) if p in members] + sorted(m for m in members if m not in s.get("parts", []))
    s["parts"] = order
    return s


def save_series(data):
    data = dict(data); data["slug"] = slug(data.get("slug") or data["title"]); data.pop("page", None)
    data.setdefault("parts", []); data.setdefault("playlist", ""); data.setdefault("description", ""); data.setdefault("cover", "")
    _write(os.path.join(series_dir(), data["slug"] + ".json"), data)
    md = os.path.join(series_dir(), data["slug"] + ".md")
    if not os.path.exists(md):
        open(md, "w").write("# %s\n\nWhat the series is for, who it's for, and the order to watch it in.\n" % data["title"])
    return data


def set_series(name, titles):
    v = load_video(name); v["series"] = [t for t in dict.fromkeys(t.strip() for t in titles) if t]
    save_video(name, v)
    for t in v["series"]:                                   # every series it joins gets a page, the video added to its order
        try:
            s = _read(os.path.join(series_dir(), slug(t) + ".json"), None) or {"title": t, "parts": []}
        except ValueError:
            continue
        if name not in s.get("parts", []):
            s.setdefault("parts", []).append(name)
        save_series(s)
    return v


def delete_series(sslug):
    """Remove a series page and take the series off its videos; the videos stay."""
    sr = get_series(sslug)
    for n in sr["parts"]:
        v = load_video(n); v["series"] = [t for t in v.get("series", []) if t != sr["title"]]; save_video(n, v)
    for ext in (".json", ".md"):
        p = os.path.join(series_dir(), sr["slug"] + ext)
        if os.path.exists(p):
            os.remove(p)
    return sr["slug"]


# ---- delete a video: to the Trash, never removed outright --------------------------------------------------------------
BUSY = ("queued", "cutting", "storyboarding", "rendering", "transcribing", "drafting")


def trash_dir():
    return os.environ.get("STUDIO_TRASH") or os.path.expanduser("~/.Trash")


def delete_video(name):
    """Move videos/<name>/ to the Trash (recoverable there) and take it out of its series. Refuses while a stage runs."""
    w = video_dir(name)
    if not os.path.isdir(w):
        raise KeyError(name)
    stage = (state(name) or {}).get("stage", "")
    if stage in BUSY:
        raise ValueError("%s is %s right now; wait for the stage to finish, then delete it" % (name, stage))
    for sr in all_series():
        if name in sr.get("parts", []) and os.path.exists(os.path.join(series_dir(), sr["slug"] + ".json")):
            s = _read(os.path.join(series_dir(), sr["slug"] + ".json"), {})
            s["parts"] = [x for x in s.get("parts", []) if x != name]
            save_series(s)
    for other in os.listdir(videos_dir()):                 # links from its sibling parts
        if other != name and _NAME.match(other) and os.path.isfile(os.path.join(videos_dir(), other, "video.json")):
            v = load_video(other)
            if name in v.get("related", []):
                v["related"] = [x for x in v["related"] if x != name]; save_video(other, v)
    os.makedirs(trash_dir(), exist_ok=True)
    dest = os.path.join(trash_dir(), "%s %s" % (name, dt.datetime.now().strftime("%Y-%m-%d %H.%M.%S")))
    os.rename(w, dest) if os.stat(w).st_dev == os.stat(trash_dir()).st_dev else __import__("shutil").move(w, dest)
    return dest


# ---- split: one idea into a series of videos ------------------------------------------------------------------------
def _split_path(name):
    return os.path.join(video_dir(name), "studio", "split.json")


def propose_split(name, series_title, parts, why=""):
    """parts: [{"name", "title", "promise", "minutes"}]; the first is this video. Writes the proposal and asks Dennis."""
    if not parts or parts[0].get("name") != name:
        parts = [{"name": name, "title": load_video(name).get("title") or name, "promise": "", "minutes": ""}] + [p for p in parts if p.get("name") != name]
    for p in parts:
        p["name"] = slug(p["name"])
        video_dir(p["name"])
    prop = {"series": series_title, "parts": parts, "why": why, "status": "proposed", "proposed": now()}
    q = ask(name, "Make this a series? %s: %s" % (series_title, "; ".join("%d. %s" % (i + 1, p.get("title") or p["name"]) for i, p in enumerate(parts))),
            ["Make it a series", "Keep one video"], frm="claude")
    q["action"] = "split"
    with _lock:
        qs = questions(name)
        for x in qs:
            if x["id"] == q["id"]:
                x["action"] = "split"
        _write(_qpath(name), qs)
    prop["question"] = q["id"]
    _write(_split_path(name), prop)
    return prop


def split_proposal(name):
    return _read(_split_path(name), None)


def _clean_parts(name, parts):
    out, seen = [], set()
    for p in parts:
        n = slug(p.get("name") or p.get("title") or "")
        if not n:
            continue
        if n in seen:
            raise ValueError("two parts share the folder %s" % n)
        seen.add(n); out.append(dict(p, name=n))
    if not out or out[0]["name"] != name:
        raise ValueError("part 1 must be this video (%s)" % name)
    if len(out) < 2:
        raise ValueError("a series needs at least two parts")
    return out


def apply_split(name, parts=None, series_title=None):
    """Make the video part 1 of a series and create the other parts as studio projects (origin and profile copied)."""
    prop = split_proposal(name) or {}
    parts = parts or prop.get("parts") or []
    title = series_title or prop.get("series")
    if not title or not parts:
        raise ValueError("no split proposal")
    parts = _clean_parts(name, parts)
    v = load_video(name)
    brief = open(os.path.join(video_dir(name), "BRIEF.md")).read() if os.path.isfile(os.path.join(video_dir(name), "BRIEF.md")) else ""
    made = []
    for i, p in enumerate(parts):
        n = slug(p["name"])
        if n != name and not os.path.exists(video_dir(n)):
            scaffold(n, v.get("origin") or "problem", p.get("title", ""), v.get("series", []), v.get("profile") or "hubspot", v.get("presenter", ""))
            w = video_dir(n)
            for f in ("research.md", "references.md"):          # the research and links are shared; each part gets a copy
                src = os.path.join(video_dir(name), f)
                if os.path.isfile(src):
                    open(os.path.join(w, f), "w").write(open(src).read())
            if os.path.isdir(_mat_dir(name)) and not os.path.exists(os.path.join(w, "materials")):
                shutil.copytree(_mat_dir(name), os.path.join(w, "materials"))
            open(os.path.join(w, "BRIEF.md"), "a").write(
                "\n\n## Part %d of %s\n%s\n\nTarget length: %s min. From the original brief (videos/%s/BRIEF.md):\n\n%s\n"
                % (i + 1, title, p.get("promise", ""), p.get("minutes") or "under 6", name, "\n".join("> " + l for l in brief.splitlines())))
            made.append(n)
        nv = load_video(n); nv["part"] = i + 1; nv["related"] = [slug(x["name"]) for x in parts if slug(x["name"]) != n]
        if title not in nv.get("series", []):
            nv["series"] = nv.get("series", []) + [title]
        save_video(n, nv)
    s = _read(os.path.join(series_dir(), slug(title) + ".json"), None) or {"title": title, "parts": []}
    order = [slug(p["name"]) for p in parts]
    s["parts"] = order + [x for x in s.get("parts", []) if x not in order]
    save_series(s)
    if prop:
        prop["status"] = "accepted"; prop["accepted"] = now(); prop["parts"] = parts; prop["series"] = title; _write(_split_path(name), prop)
    return {"series": slug(title), "made": made, "parts": order}


# ---- materials: what a colleague (or anyone) already made --------------------------------------------------------
MAX_UPLOAD = 2 << 30


def _mat_dir(name):
    return os.path.join(video_dir(name), "materials")


def _mat_index(name):
    return _read(os.path.join(_mat_dir(name), "materials.json"), None) or {"files": {}, "links": []}


def _safe_filename(fn):
    fn = os.path.basename(fn.replace("\\", "/")).strip()
    fn = re.sub(r"[^\w .()+,'-]", "_", fn).lstrip(".")
    if not fn or fn in ("materials.json", "README.md"):
        raise ValueError("not a usable file name")
    return fn[:150]


def materials(name):
    idx = _mat_index(name); d = _mat_dir(name); files = []
    if os.path.isdir(d):
        for fn in sorted(os.listdir(d)):
            p = os.path.join(d, fn)
            if fn in ("materials.json", "README.md") or fn.startswith(".") or not os.path.isfile(p):
                continue
            meta = idx["files"].get(fn, {})
            files.append({"file": fn, "path": "materials/" + fn, "size": os.path.getsize(p), "note": meta.get("note", ""), "added": meta.get("added", "")})
    return {"files": files, "links": idx["links"]}


def _save_mat_index(name, idx):
    os.makedirs(_mat_dir(name), exist_ok=True)
    _write(os.path.join(_mat_dir(name), "materials.json"), idx)
    m = materials(name)
    out = ["# Materials for %s" % name, "",
           "What others already made for this video. Read the files and open the links before writing anything that",
           "draws on them; credit the colleague as BRIEF.md says.", ""]
    if m["files"]:
        out += ["## Files", ""] + ["- %s%s" % (f["file"], (": " + f["note"]) if f["note"] else "") for f in m["files"]] + [""]
    if m["links"]:
        out += ["## Links", ""] + ["- [%s](%s)%s" % (l.get("label") or l["url"], l["url"], (": " + l["note"]) if l.get("note") else "") for l in m["links"]] + [""]
    open(os.path.join(_mat_dir(name), "README.md"), "w").write("\n".join(out))


def save_material(name, filename, stream, length, note=""):
    if length > MAX_UPLOAD:
        raise ValueError("files over 2 GB go in the folder by hand (Finder)")
    fn = _safe_filename(filename); d = _mat_dir(name); os.makedirs(d, exist_ok=True)
    base, ext = os.path.splitext(fn); k = 2
    while os.path.exists(os.path.join(d, fn)):
        fn = "%s (%d)%s" % (base, k, ext); k += 1
    tmp = os.path.join(d, ".upload-" + uuid.uuid4().hex)
    try:
        with open(tmp, "wb") as f:
            left = length
            while left > 0:
                chunk = stream.read(min(1 << 20, left))
                if not chunk:
                    raise ValueError("the upload stopped part way")
                f.write(chunk); left -= len(chunk)
        os.replace(tmp, os.path.join(d, fn))
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    with _lock:
        idx = _mat_index(name); idx["files"][fn] = {"note": note, "added": now()}; _save_mat_index(name, idx)
    return fn


def add_material_link(name, url, label="", note=""):
    url = url.strip()
    if not re.match(r"^https?://\S+$", url):
        raise ValueError("a link starts with http:// or https://")
    with _lock:
        idx = _mat_index(name)
        if not any(l["url"] == url for l in idx["links"]):
            idx["links"].append({"url": url, "label": label.strip(), "note": note.strip(), "added": now()})
        _save_mat_index(name, idx)
        ref = os.path.join(video_dir(name), "references.md")
        text = open(ref).read() if os.path.isfile(ref) else "| Label | URL | Used for | Status | Checked |\n| --- | --- | --- | --- | --- |\n"
        if url not in text:
            cell = lambda x: x.replace("|", "/").replace("\n", " ")
            row = "| %s | %s | %s | unchecked | |\n" % (cell(label or url), url, cell("material: " + note if note else "material"))
            open(ref, "w").write(text if text.endswith("\n") else text + "\n")
            open(ref, "a").write(row)
    return materials(name)


def set_material_note(name, note, file=None, url=None):
    with _lock:
        idx = _mat_index(name)
        if file:
            fn = _safe_filename(file)
            if not os.path.isfile(os.path.join(_mat_dir(name), fn)):
                raise KeyError(fn)
            idx["files"].setdefault(fn, {"added": now()})["note"] = note
        else:
            hit = [l for l in idx["links"] if l["url"] == url]
            if not hit:
                raise KeyError(url)
            hit[0]["note"] = note
        _save_mat_index(name, idx)
    return materials(name)


def remove_material(name, file=None, url=None):
    with _lock:
        idx = _mat_index(name)
        if file:
            fn = _safe_filename(file); p = os.path.join(_mat_dir(name), fn)
            if os.path.isfile(p):
                os.remove(p)
            idx["files"].pop(fn, None)
        else:
            idx["links"] = [l for l in idx["links"] if l["url"] != url]
        _save_mat_index(name, idx)
    return materials(name)


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
    sp = sub.add_parser("propose-split"); sp.add_argument("name"); sp.add_argument("--series", required=True)
    sp.add_argument("--part", action="append", default=[], help="name::title::promise::minutes (this video first)")
    sp.add_argument("--why", default="")
    a = ap.parse_args(argv)
    if a.cmd == "new":
        name = slug(a.name)
        try:
            w = scaffold(name, a.origin, a.title, a.series, a.profile, a.presenter)
        except (FileExistsError, ValueError) as e:
            sys.exit(str(e))
        print("made %s (%s, phase %s)" % (os.path.relpath(w, ROOT), a.origin, load_video(name)["phase"]))
    elif a.cmd == "propose-split":
        parts = []
        for x in a.part:
            bits = (x.split("::") + ["", "", "", ""])[:4]
            parts.append({"name": bits[0], "title": bits[1], "promise": bits[2], "minutes": bits[3]})
        p = propose_split(a.name, a.series, parts, a.why)
        print("proposed %d videos in %s; Dennis answers in the studio" % (len(p["parts"]), a.series))
    elif a.cmd == "ask":
        q = ask(a.name, a.text, [o for o in a.options.split("|") if o] if a.options else None)
        print("asked %s: %s" % (q["id"], q["text"]))


if __name__ == "__main__":
    main(sys.argv[1:])
