import json, os, stat, tempfile, threading, unittest, urllib.request, urllib.error
from helpers import temp_root, cleanup


def stand_in(path, name):
    """A stand-in for claude or yt: prints its arguments as JSON (claude-style result) and exits 0."""
    p = os.path.join(path, name)
    open(p, "w").write('#!/bin/sh\nprintf \'{"result": "stand-in ran: %s", "total_cost_usd": 0.01}\\n\' "$*"\n')
    os.chmod(p, os.stat(p).st_mode | stat.S_IEXEC)
    return p


class ServerTest(unittest.TestCase):
    def setUp(self):
        self.root, self.core = temp_root()
        self.bin = tempfile.mkdtemp()
        os.environ["STUDIO_CLAUDE"] = stand_in(self.bin, "claude")
        os.environ["STUDIO_YT"] = stand_in(self.bin, "yt")
        import importlib, server
        importlib.reload(server)
        self.server = server.make_server(0)
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.core.scaffold("v1", "problem", title="Video one")

    def tearDown(self):
        self.server.shutdown(); self.server.server_close()
        cleanup(self.root)
        for k in ("STUDIO_CLAUDE", "STUDIO_YT"):
            os.environ.pop(k, None)

    def call(self, method, path, body=None, header=True, headers=None):
        data = json.dumps(body).encode() if body is not None else None
        h = {"Content-Type": "application/json"}
        if header:
            h["X-Studio"] = "1"
        h.update(headers or {})
        req = urllib.request.Request("http://127.0.0.1:%d%s" % (self.port, path), data=data, method=method, headers=h)
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                raw = r.read()
                return r.status, (json.loads(raw) if r.headers.get("Content-Type", "").startswith("application/json") else raw)
        except urllib.error.HTTPError as e:
            raw = e.read()
            try:
                return e.code, json.loads(raw)
            except ValueError:
                return e.code, raw

    def test_board(self):
        st, body = self.call("GET", "/api/videos")
        self.assertEqual(st, 200)
        self.assertEqual([v["name"] for v in body["videos"]], ["v1"])
        self.assertEqual(body["phases"][0]["id"], "ideation")

    def test_index_served(self):
        st, body = self.call("GET", "/")
        self.assertEqual(st, 200)
        self.assertIn(b"<html", body)

    def test_new_video(self):
        st, body = self.call("POST", "/api/videos", {"title": "Agents 3: CLI", "origin": "feature"})
        self.assertEqual(st, 200)
        self.assertEqual(body["name"], "agents-3-cli")
        st, body = self.call("POST", "/api/videos", {"name": "v1", "origin": "feature"})
        self.assertEqual(st, 409)

    def test_post_needs_header(self):
        st, _ = self.call("POST", "/api/videos", {"title": "x", "origin": "feature"}, header=False)
        self.assertEqual(st, 403)

    def test_video_detail(self):
        st, v = self.call("GET", "/api/videos/v1")
        self.assertEqual(st, 200)
        self.assertEqual(v["phase"], "ideation")
        self.assertIn("BRIEF.md", v["docs"])

    def test_doc_round_trip_and_escape(self):
        st, _ = self.call("PUT", "/api/videos/v1/doc?path=BRIEF.md", {"text": "# New brief\n"})
        self.assertEqual(st, 200)
        st, d = self.call("GET", "/api/videos/v1/doc?path=BRIEF.md")
        self.assertEqual(d["text"], "# New brief\n")
        st, _ = self.call("PUT", "/api/videos/v1/doc?path=../../etc.md", {"text": "x"})
        self.assertEqual(st, 400)
        st, _ = self.call("PUT", "/api/videos/v1/doc?path=state.json", {"text": "x"})
        self.assertEqual(st, 400)

    def test_media_range(self):
        p = os.path.join(self.root, "videos", "v1", "review", "clip.mp4")
        open(p, "wb").write(bytes(range(256)) * 4)
        st, body = self.call("GET", "/media/v1/review/clip.mp4", headers={"Range": "bytes=10-19"})
        self.assertEqual(st, 206)
        self.assertEqual(body, bytes(range(10, 20)))
        st, _ = self.call("GET", "/media/v1/../../x")
        self.assertIn(st, (400, 404))

    def test_questions_and_comments(self):
        q = self.core.ask("v1", "Which face?", ["Dennis", "guest"])
        st, body = self.call("POST", "/api/videos/v1/questions", {"id": q["id"], "answer": "guest"})
        self.assertEqual(st, 200)
        self.assertEqual(self.core.questions("v1")[0]["answer"], "guest")
        items = [{"id": "c1", "t": 3.2, "text": "off centre"}]
        st, _ = self.call("POST", "/api/videos/v1/comments/B", {"items": items})
        self.assertEqual(st, 200)
        st, body = self.call("GET", "/api/videos/v1/comments/B")
        self.assertEqual(body["items"], items)

    def test_action_whitelist_and_job(self):
        st, _ = self.call("POST", "/api/videos/v1/action", {"action": "rm-rf"})
        self.assertEqual(st, 400)
        st, body = self.call("POST", "/api/videos/v1/action", {"action": "youtube"})
        self.assertEqual(st, 200)
        j = self.core.wait_job("v1", body["job"], 10)
        self.assertEqual(j["exit"], 0)
        self.assertIn("youtube v1", j["log"])

    def test_request_runs_claude(self):
        st, body = self.call("POST", "/api/videos/v1/request", {"phase": "ideation", "form": "freeform", "fields": {"text": "hello there"}})
        self.assertEqual(st, 200)
        j = self.core.wait_job("v1", body["job"], 10)
        self.assertIn("hello there", j["log"])
        self.assertIn("--max-budget-usd", j["log"])

    def test_chat_keeps_one_session(self):
        st, b1 = self.call("POST", "/api/videos/v1/chat", {"text": "first"})
        self.core.wait_job("v1", b1["job"], 10)
        sid = self.core.load_video("v1")["chat_session"]
        self.assertIn("--session-id %s" % sid, self.core.job("v1", b1["job"])["log"])
        st, b2 = self.call("POST", "/api/videos/v1/chat", {"text": "second"})
        self.core.wait_job("v1", b2["job"], 10)
        self.assertIn("--resume %s" % sid, self.core.job("v1", b2["job"])["log"])
        st, chat = self.call("GET", "/api/videos/v1/chat")
        self.assertEqual([m["role"] for m in chat["messages"]], ["dennis", "claude", "dennis", "claude"])
        self.assertIn("stand-in ran", chat["messages"][1]["text"])

    def test_series_api_and_split_by_answer(self):
        st, _ = self.call("POST", "/api/videos/v1/series", {"titles": ["Headless", "Auth"]})
        self.assertEqual(st, 200)
        st, body = self.call("GET", "/api/series")
        self.assertEqual(sorted(s["title"] for s in body["series"]), ["Auth", "Headless"])
        st, s = self.call("GET", "/api/series/auth")
        self.assertEqual(s["parts"], ["v1"])
        st, _ = self.call("PUT", "/api/series/auth", {"playlist": "https://www.youtube.com/playlist?list=X", "parts": ["v1"]})
        self.assertEqual(self.core.get_series("auth")["playlist"], "https://www.youtube.com/playlist?list=X")
        self.core.propose_split("v1", "Auth", [{"name": "v1"}, {"name": "v2", "title": "Second"}])
        q = self.core.questions("v1")[-1]
        st, _ = self.call("POST", "/api/videos/v1/questions", {"id": q["id"], "answer": "Make it a series"})
        self.assertEqual(st, 200)
        self.assertTrue(os.path.isdir(os.path.join(self.root, "videos", "v2")))

    def test_delete_needs_the_name(self):
        os.environ["STUDIO_TRASH"] = os.path.join(self.root, "Trash")
        try:
            st, _ = self.call("POST", "/api/videos/v1/delete", {"confirm": "nope"})
            self.assertEqual(st, 400)
            st, body = self.call("POST", "/api/videos/v1/delete", {"confirm": "v1"})
            self.assertEqual(st, 200)
            self.assertFalse(os.path.exists(os.path.join(self.root, "videos", "v1")))
        finally:
            os.environ.pop("STUDIO_TRASH", None)

    def test_step_done_and_approve(self):
        st, _ = self.call("POST", "/api/videos/v1/phase", {"phase": "ideation", "step": "brief", "done": True})
        self.assertEqual(st, 200)
        self.assertEqual(self.core.load_video("v1")["phases"]["ideation"]["done"], ["brief"])
        st, v = self.call("POST", "/api/videos/v1/phase", {"phase": "ideation", "approve": True})
        self.assertEqual(self.core.load_video("v1")["phase"], "script")


if __name__ == "__main__":
    unittest.main()
