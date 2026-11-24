#!/usr/bin/env python3
"""server.py: the studio, a page on http://127.0.0.1:4040 where Dennis follows every video from idea to results.

  python3 server.py [--port 4040]        (yt app starts it; launchd keeps it running after install.sh)

Reads and writes videos/<name>/ through core.py; starts `yt` commands and Claude runs as background jobs. Binds to
127.0.0.1 only. Every POST and PUT needs the header X-Studio: 1. Paths stay inside the video's folder.
"""
import base64, json, mimetypes, os, re, shlex, sys, uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, parse_qs, unquote

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import core

WEB = os.path.join(HERE, "web")
PIPE = os.path.dirname(HERE)
EDITABLE_EXTRA = ("notes.txt", "PAPER-CUT.md", "CHECKPOINT-B.md")
READ_ONLY = ("youtube/YOUTUBE.md",)


def config():
    """pipeline/config.sh as a dict (KEY="value" lines), for CLAUDE_BIN, BUDGET_USD and MODEL."""
    out = {}
    try:
        for line in open(os.path.join(PIPE, "config.sh")):
            m = re.match(r'^([A-Z_]+)="([^"]*)"', line.strip())
            if m:
                out[m.group(1)] = m.group(2)
    except OSError:
        pass
    return out


def yt_argv(*args):
    yt = os.environ.get("STUDIO_YT")
    return ([yt] if yt else ["bash", os.path.join(PIPE, "yt")]) + list(args)


def claude_argv(prompt, extra=()):
    cfg = config()
    bin_ = os.environ.get("STUDIO_CLAUDE") or cfg.get("CLAUDE_BIN") or "claude"
    model = os.environ.get("STUDIO_MODEL", "sonnet")
    return [bin_, "-p", prompt, "--permission-mode", "auto", "--permission-prompts", "none", "--output-format", "json",
            "--max-budget-usd", cfg.get("BUDGET_USD", "20"), "--model", model] + list(extra)


def claude_result(log):
    """The reply and cost from a claude -p --output-format json log (the last JSON object in it)."""
    for chunk in reversed([c for c in re.split(r"\n(?=\{)", log.strip()) if c.strip().startswith("{")]):
        try:
            j = json.loads(chunk)
            return j.get("result") or "", j.get("total_cost_usd")
        except ValueError:
            continue
    return log.strip()[-4000:], None


def all_docs():
    seen = []
    for p in core.PHASES:
        for d in p.get("docs", []):
            if d not in seen:
                seen.append(d)
    return seen + [d for d in EDITABLE_EXTRA if d not in seen]


def reviews(name):
    w = core.video_dir(name)
    rel = lambda p: p if os.path.exists(os.path.join(w, p)) else None
    snaps = sorted(f for f in os.listdir(os.path.join(w, "snaps"))) if os.path.isdir(os.path.join(w, "snaps")) else []
    meta = core._read(os.path.join(w, "youtube", "metadata.json"), {}) or {}
    thumbs = sorted(f for f in os.listdir(os.path.join(w, "youtube"))
                    if re.match(r"^thumbnail-\d+\.jpg$", f)) if os.path.isdir(os.path.join(w, "youtube")) else []
    variants = sorted(os.listdir(os.path.join(w, "review", "variants"))) if os.path.isdir(os.path.join(w, "review", "variants")) else []
    return {
        "A": {"video": rel("review/cut-review.mp4"), "stills": ["snaps/" + s for s in snaps if s.startswith(("grade", "screen"))],
              "doc": "PAPER-CUT.md"},
        "B": {"video": rel("review/preview.mp4"), "stills": (["snaps/sheet.png"] if "sheet.png" in snaps else []),
              "variants": ["review/variants/" + v for v in variants], "doc": "CHECKPOINT-B.md"},
        "package": {"thumbs": ["youtube/" + t for t in thumbs],
                    "titles": [(t["title"] if isinstance(t, dict) else t) for t in meta.get("titles", [])],
                    "video": next((f for f in sorted(os.listdir(w)) if f.endswith((".mp4", ".mov"))), None),
                    "doc": "youtube/YOUTUBE.md"},
    }


def detail(name):
    v = core.load_video(name); st = core.state(name)
    w = core.video_dir(name)
    ph = core.current_phase(name, v, st)
    return {"video": v, "phase": ph, "stage": (st or {}).get("stage", ""),
            "history": (st or {}).get("history", [])[-8:],
            "phases": core.PHASES, "progress": v.get("phases", {}),
            "docs": {d: os.path.exists(os.path.join(w, d)) for d in all_docs()},
            "questions": core.questions(name), "jobs": core.jobs(name, 12), "reviews": reviews(name),
            "raw": sorted(os.listdir(os.path.join(w, "raw"))) if os.path.isdir(os.path.join(w, "raw")) else [],
            "split": core.split_proposal(name), "all_series": [x["title"] for x in core.all_series()],
            "length": dict(zip(("target", "max"), core.profile_length(v.get("profile"))), minutes=core.estimate_minutes(name))}


def fill(template, values):
    return re.sub(r"\{(\w+)\}", lambda m: str(values.get(m.group(1), m.group(0))), template)


# ---- actions: the only commands the page can start ------------------------------------------------------------------
def append_approval(name, which, words):
    d = os.path.join(core.video_dir(name), "approvals"); os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "%s.md" % which), "a") as f:
        f.write("\n## %s (studio)\n\n%s\n" % (core.now(), words))


def pick(name, what, index):
    p = os.path.join(core.video_dir(name), "youtube", "metadata.json")
    m = core._read(p, None)
    if m is None:
        raise ValueError("no youtube/metadata.json yet")
    if what == "title":
        t = m.get("titles", [])
        m["titles"] = [t[index]] + [x for i, x in enumerate(t) if i != index]
    else:
        o = m.get("thumbnail", {}).get("options", [])
        chosen = dict(o[index]); chosen["why"] = "Dennis's pick"
        m["thumbnail"]["options"] = [chosen]
        yd = os.path.dirname(p)
        keep = "thumbnail-%d" % (index + 1)
        for f in os.listdir(yd):                           # the chosen files become thumbnail-1, the rest go
            mm = re.match(r"^(thumbnail-\d+)(-mobile)?\.jpg$", f)
            if mm and mm.group(1) != keep:
                os.remove(os.path.join(yd, f))
        for suf in ("", "-mobile"):
            src = os.path.join(yd, keep + suf + ".jpg")
            if os.path.exists(src) and keep != "thumbnail-1":
                os.replace(src, os.path.join(yd, "thumbnail-1" + suf + ".jpg"))
        tj = core._read(os.path.join(yd, "thumbnails.json"), {}) or {}
        if str(index + 1) in tj:
            e = tj[str(index + 1)]; e["file"], e["mobile"] = "thumbnail-1.jpg", "thumbnail-1-mobile.jpg"
            core._write(os.path.join(yd, "thumbnails.json"), {"1": e})
    core._write(p, m)


def action(name, act, args):
    """(argv, label) for an action, after any file changes it makes; ValueError for anything not on the list."""
    w = core.video_dir(name)
    a = args or {}
    simple = {"youtube": ("youtube",), "thumb": ("thumb",), "drive": ("drive",), "rerun-cut": ("run", None, "cut"),
              "rerun-storyboard": ("run", None, "storyboard")}
    if act in simple:
        parts = [name if x is None else x for x in simple[act]]
        if act in ("youtube", "thumb", "drive"):
            parts = [parts[0], name] + parts[1:]
        if act == "drive" and a.get("no_video"):
            parts.append("--no-video")
        return yt_argv(*parts), act
    if act == "shorten":
        return yt_argv("shorten", name, *(["--hubspot"] if a.get("hubspot") or core.load_video(name).get("profile") == "hubspot" and not core.load_video(name).get("legacy") else [])), "shorten"
    if act == "sheets":
        return [sys.executable, os.path.join(HERE, "script_sheets.py"), name], "teleprompter and recording sheet"
    if act == "finder-raw":
        os.makedirs(os.path.join(w, "raw"), exist_ok=True)
        return ["open", os.path.join(w, "raw")], "open raw/ in Finder"
    if act in ("start-cut", "start-cut-fast"):
        return yt_argv("start", name, *(["--fast"] if act.endswith("fast") else [])), "start the cut"
    if act == "approve-a":
        grade = re.sub(r"[^a-z]", "", (a.get("grade") or "blacks").lower()) or "blacks"
        append_approval(name, "A", "approve %s (grade: %s)%s" % (name, grade, (". " + a["note"]) if a.get("note") else ""))
        return yt_argv("run", name, "storyboard"), "approve A: storyboard"
    if act == "approve-b":
        append_approval(name, "B", "approve %s%s" % (name, (". " + a["note"]) if a.get("note") else ""))
        cmd = shlex.join(yt_argv("run", name, "render")) + " && " + shlex.join(yt_argv("run", name, "youtube"))
        return ["/bin/sh", "-c", cmd], "approve B: render and YouTube"
    if act == "import":
        path = os.path.expanduser(a.get("path", ""))
        if not os.path.isfile(path):
            raise ValueError("no such file: %s" % path)
        return yt_argv("import", name, path), "import the render"
    if act == "published":
        url = a.get("url", "").strip()
        if not re.match(r"^https://(youtu\.be/|(www\.)?youtube\.com/)", url):
            raise ValueError("a YouTube link, please")
        sched = a.get("scheduled", "").strip()
        if sched and not re.match(r"^\d{4}-\d{2}-\d{2}$", sched):
            raise ValueError("the date as YYYY-MM-DD")
        return yt_argv("published", name, url, *(["--scheduled", sched] if sched else [])), "record the upload"
    if act in ("pick-title", "pick-thumb"):
        pick(name, "title" if act == "pick-title" else "thumb", int(a.get("index", 0)))
        return yt_argv("youtube", name), "pick and rebuild"
    raise ValueError("not an action: %r" % act)


# ---- chat -----------------------------------------------------------------------------------------------------------
def chat_path(name):
    return os.path.join(core.video_dir(name), "studio", "chat.json")


def chat_messages(name):
    msgs = core._read(chat_path(name), []) or []
    changed = False
    for m in msgs:
        if m["role"] == "claude" and not m.get("text") and m.get("job"):
            try:
                j = core.job(name, m["job"])
            except KeyError:
                continue
            if not j["running"]:
                m["text"], m["cost"] = claude_result(j["log"]); changed = True
    if changed:
        core._write(chat_path(name), msgs)
    return msgs


class Handler(BaseHTTPRequestHandler):
    server_version = "studio"

    def log_message(self, fmt, *args):
        pass

    def send(self, code, body, ctype="application/json"):
        data = json.dumps(body).encode() if ctype == "application/json" else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}") if n else {}

    def route(self, method):
        u = urlsplit(self.path); path = unquote(u.path); qs = parse_qs(u.query)
        if method in ("POST", "PUT") and self.headers.get("X-Studio") != "1":
            return self.send(403, {"error": "missing X-Studio header"})
        try:
            if method == "GET" and (path == "/" or path.startswith("/static/")):
                return self.static("index.html" if path == "/" else path[len("/static/"):])
            if method == "GET" and path.startswith("/media/"):
                return self.media(path[len("/media/"):])
            if path == "/api/videos":
                if method == "GET":
                    return self.send(200, {"videos": core.list_videos(), "phases": [{"id": p["id"], "title": p["title"], "where": p.get("where")} for p in core.PHASES]})
                b = self.body()
                name = core.slug(b.get("name") or b.get("title") or "")
                if not name:
                    return self.send(400, {"error": "a name or title, please"})
                try:
                    core.scaffold(name, b.get("origin", "problem"), b.get("title", ""), b.get("series", ""), b.get("profile", "hubspot"), b.get("presenter", ""))
                except FileExistsError as e:
                    return self.send(409, {"error": str(e)})
                return self.send(200, {"name": name})
            if path == "/api/series" and method == "GET":
                return self.send(200, {"series": core.all_series()})
            ms = re.match(r"^/api/series/([a-z0-9-]+)$", path)
            if ms:
                sr = core.get_series(ms.group(1))
                if method == "PUT":
                    b = self.body()
                    for k in ("playlist", "description", "cover", "parts"):
                        if k in b:
                            sr[k] = b[k]
                    if "md" in b:
                        open(os.path.join(core.series_dir(), sr["slug"] + ".md"), "w").write(b["md"])
                    sr = core.save_series(sr)
                    return self.send(200, core.get_series(sr["slug"]))
                mdp = os.path.join(core.series_dir(), sr["slug"] + ".md")
                vids = []
                for n in sr["parts"]:
                    vv = core.load_video(n)
                    vids.append({"name": n, "title": vv.get("title") or n, "phase": core.current_phase(n, vv), "minutes": core.estimate_minutes(n),
                                 "part": vv.get("part")})
                sr["videos"] = vids; sr["md"] = open(mdp).read() if os.path.isfile(mdp) else ""
                return self.send(200, sr)
            m = re.match(r"^/api/videos/([^/]+)(?:/(.*))?$", path)
            if not m:
                return self.send(404, {"error": "not found"})
            name, rest = m.group(1), m.group(2) or ""
            core.video_dir(name)
            if not os.path.isdir(core.video_dir(name)):
                return self.send(404, {"error": "no video %s" % name})
            return self.video_route(method, name, rest, qs)
        except ValueError as e:
            return self.send(400, {"error": str(e)})
        except KeyError as e:
            return self.send(404, {"error": "not found: %s" % e})

    def video_route(self, method, name, rest, qs):
        if rest == "" and method == "GET":
            return self.send(200, detail(name))
        if rest == "doc":
            rel = (qs.get("path") or [""])[0]
            if rel not in all_docs():
                raise ValueError("not a document the studio edits: %s" % rel)
            p = core.inside(name, rel)
            if method == "GET":
                return self.send(200, {"path": rel, "text": open(p).read() if os.path.isfile(p) else "", "exists": os.path.isfile(p),
                                       "read_only": rel in READ_ONLY})
            if rel in READ_ONLY:
                raise ValueError("%s is generated; change it with a request" % rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, "w").write(self.body().get("text", ""))
            return self.send(200, {"saved": rel})
        if rest == "phase" and method == "POST":
            b = self.body(); v = core.load_video(name); pid = b.get("phase")
            core.phase(pid)
            pr = v.setdefault("phases", {}).setdefault(pid, {"done": []})
            if "step" in b:
                done = set(pr.get("done", []))
                (done.add if b.get("done") else done.discard)(b["step"])
                pr["done"] = sorted(done)
            if b.get("approve"):
                pr["approved"] = core.now()
                i = core.PHASE_IDS.index(pid)
                if i + 1 < len(core.PHASE_IDS):
                    v["phase"] = core.PHASE_IDS[i + 1]
            if "set" in b:
                core.phase(b["set"]); v["phase"] = b["set"]
            core.save_video(name, v)
            return self.send(200, detail(name))
        if rest == "questions":
            if method == "GET":
                return self.send(200, {"questions": core.questions(name)})
            b = self.body()
            if b.get("ask"):
                return self.send(200, core.ask(name, b["ask"], b.get("options"), frm="dennis"))
            q = core.answer(name, b["id"], b.get("answer", ""))
            if q.get("action") == "split":
                prop = core.split_proposal(name)
                if prop and prop.get("status") == "proposed":
                    if b.get("answer") == "Make it a series":
                        q["result"] = core.apply_split(name)
                    elif b.get("answer") == "Keep one video":
                        prop["status"] = "declined"; core._write(core._split_path(name), prop)
            return self.send(200, q)
        m = re.match(r"^comments/(\w+)$", rest)
        if m:
            if method == "GET":
                return self.send(200, {"items": core.comments(name, m.group(1))})
            core.save_comments(name, m.group(1), self.body().get("items", []))
            return self.send(200, {"saved": len(core.comments(name, m.group(1)))})
        if rest == "series" and method == "POST":
            return self.send(200, core.set_series(name, self.body().get("titles", [])))
        if rest == "split" and method == "POST":
            b = self.body(); prop = core.split_proposal(name)
            if not prop:
                raise ValueError("no split proposal")
            if b.get("accept"):
                r = core.apply_split(name, b.get("parts"), b.get("series"))
                if prop.get("question"):
                    try:
                        core.answer(name, prop["question"], "Make it a series")
                    except KeyError:
                        pass
                return self.send(200, r)
            prop["status"] = "declined"; core._write(core._split_path(name), prop)
            if prop.get("question"):
                try:
                    core.answer(name, prop["question"], "Keep one video")
                except KeyError:
                    pass
            return self.send(200, prop)
        if rest == "frame" and method == "POST":
            b = self.body(); cid = re.sub(r"[^a-zA-Z0-9_-]", "", b.get("id", ""))
            if not cid:
                raise ValueError("a comment id")
            data = base64.b64decode(b.get("png", "").split(",")[-1])
            d = core.inside(name, "review/comments"); os.makedirs(d, exist_ok=True)
            open(os.path.join(d, cid + ".png"), "wb").write(data)
            return self.send(200, {"frame": "review/comments/%s.png" % cid})
        if rest == "action" and method == "POST":
            b = self.body()
            argv, label = action(name, b.get("action", ""), b.get("args"))
            return self.send(200, {"job": core.start_job(name, "action", argv, label=label)})
        if rest == "request" and method == "POST":
            b = self.body(); ph = core.phase(b.get("phase", ""))
            form = next((f for f in ph.get("forms", []) if f["id"] == b.get("form")), None)
            if not form:
                raise ValueError("no such form")
            fields = {k: str(v) for k, v in (b.get("fields") or {}).items()}
            if form.get("action"):
                argv, label = action(name, form["action"], fields)
                return self.send(200, {"job": core.start_job(name, "action", argv, label=label)})
            v = core.load_video(name)
            req = fill(form["prompt"], fields).replace("<name>", name).replace("<profile>", v.get("profile") or "hubspot")
            prompt = fill(open(os.path.join(HERE, "prompts", "form.md")).read(),
                          {"name": name, "phase_title": ph["title"], "profile": v.get("profile") or "hubspot", "request": req,
                           "target": "%g" % core.profile_length(v.get("profile"))[0], "max": "%g" % core.profile_length(v.get("profile"))[1]})
            return self.send(200, {"job": core.start_job(name, "request", claude_argv(prompt), label=form["label"])})
        if rest == "notes" and method == "POST":
            b = self.body(); review = b.get("review", "B")
            items = core.comments(name, review)
            if not items:
                raise ValueError("no comments to send")
            lines = []
            for i, c in enumerate(items, 1):
                bits = ["%d. at %.2f s" % (i, float(c.get("t", 0)))]
                if c.get("box"):
                    bits.append("box %s" % ",".join(str(int(x)) for x in c["box"]))
                if c.get("still"):
                    bits.append("still %s" % c["still"])
                if c.get("frame"):
                    bits.append("frame %s" % c["frame"])
                lines.append("%s: %s" % ("; ".join(bits), c.get("text", "")))
            rv = reviews(name).get(review, {})
            prompt = fill(open(os.path.join(HERE, "prompts", "notes.md")).read(),
                          {"name": name, "review": review, "review_title": {"A": "Checkpoint A (the cut)", "B": "Checkpoint B (the storyboard)", "package": "the YouTube package"}[review],
                           "notes": "\n".join(lines), "doc": rv.get("doc", "")})
            for c in items:
                c["sent"] = core.now()
            core.save_comments(name, review, items)
            return self.send(200, {"job": core.start_job(name, "notes", claude_argv(prompt), label="notes for %s" % review)})
        if rest == "chat":
            if method == "GET":
                return self.send(200, {"messages": chat_messages(name)})
            text = self.body().get("text", "").strip()
            if not text:
                raise ValueError("an empty message")
            v = core.load_video(name)
            first = not v.get("chat_session")
            if first:
                v["chat_session"] = str(uuid.uuid4()); core.save_video(name, v)
            sid = v["chat_session"]
            ph = core.phase(core.current_phase(name, v))
            system = fill(open(os.path.join(HERE, "prompts", "chat.md")).read(), {"name": name, "phase_title": ph["title"],
                          "target": "%g" % core.profile_length(v.get("profile"))[0], "max": "%g" % core.profile_length(v.get("profile"))[1]})
            argv = claude_argv(text, (["--session-id", sid] if first else ["--resume", sid]) + ["--append-system-prompt", system])
            jid = core.start_job(name, "chat", argv, label="chat")
            msgs = core._read(chat_path(name), []) or []
            msgs += [{"role": "dennis", "text": text, "at": core.now()}, {"role": "claude", "text": "", "job": jid, "at": core.now()}]
            core._write(chat_path(name), msgs)
            return self.send(200, {"job": jid})
        m = re.match(r"^jobs/([0-9a-f-]+)$", rest)
        if m and method == "GET":
            j = core.job(name, m.group(1))
            if j.get("kind") in ("request", "notes", "chat") and not j["running"]:
                j["reply"], j["cost"] = claude_result(j["log"])
            return self.send(200, j)
        return self.send(404, {"error": "not found"})

    def static(self, rel):
        p = os.path.realpath(os.path.join(WEB, rel))
        if not p.startswith(os.path.realpath(WEB) + os.sep) or not os.path.isfile(p):
            return self.send(404, {"error": "not found"})
        return self.send(200, open(p, "rb").read(), mimetypes.guess_type(p)[0] or "application/octet-stream")

    def media(self, rest):
        name, _, rel = rest.partition("/")
        p = core.inside(name, rel)
        if not os.path.isfile(p):
            return self.send(404, {"error": "not found"})
        size = os.path.getsize(p); ctype = mimetypes.guess_type(p)[0] or "application/octet-stream"
        rng = re.match(r"bytes=(\d*)-(\d*)", self.headers.get("Range", ""))
        start, end = 0, size - 1
        if rng and (rng.group(1) or rng.group(2)):
            if rng.group(1):
                start = int(rng.group(1)); end = int(rng.group(2)) if rng.group(2) else size - 1
            else:
                start = max(0, size - int(rng.group(2)))
            end = min(end, size - 1)
            self.send_response(206); self.send_header("Content-Range", "bytes %d-%d/%d" % (start, end, size))
        else:
            self.send_response(200)
        self.send_header("Content-Type", ctype); self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(end - start + 1)); self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        with open(p, "rb") as f:
            f.seek(start); left = end - start + 1
            while left > 0:
                chunk = f.read(min(1 << 20, left))
                if not chunk:
                    break
                try:
                    self.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    return
                left -= len(chunk)

    def do_GET(self):
        self.route("GET")

    def do_POST(self):
        self.route("POST")

    def do_PUT(self):
        self.route("PUT")


def make_server(port):
    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("--port", type=int, default=int(os.environ.get("STUDIO_PORT", "4040")))
    a = ap.parse_args()
    s = make_server(a.port)
    print("studio on http://127.0.0.1:%d (videos: %s)" % (a.port, core.videos_dir()), flush=True)
    s.serve_forever()
