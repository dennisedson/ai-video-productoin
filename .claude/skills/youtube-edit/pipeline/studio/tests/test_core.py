import json, os, unittest
from helpers import temp_root, cleanup


class CoreTest(unittest.TestCase):
    def setUp(self):
        self.root, self.core = temp_root()

    def tearDown(self):
        cleanup(self.root)

    def test_scaffold_writes_every_file(self):
        w = self.core.scaffold("agents-3", "problem", title="Stale deals")
        for f in ("video.json", "BRIEF.md", "research.md", "references.md", "SCRIPT.md", "results.md"):
            self.assertTrue(os.path.isfile(os.path.join(w, f)), f)
        self.assertTrue(os.path.isdir(os.path.join(w, "raw")))
        v = json.load(open(os.path.join(w, "video.json")))
        self.assertEqual((v["name"], v["origin"], v["phase"], v["title"]), ("agents-3", "problem", "ideation", "Stale deals"))
        self.assertIn("The problem", open(os.path.join(w, "BRIEF.md")).read())
        self.assertIn("Stale deals", open(os.path.join(w, "BRIEF.md")).read())

    def test_scaffold_refuses_existing(self):
        self.core.scaffold("x", "feature")
        with self.assertRaises(FileExistsError):
            self.core.scaffold("x", "feature")

    def test_finished_origin_starts_at_packaging(self):
        self.core.scaffold("done-video", "finished")
        self.assertEqual(self.core.load_video("done-video")["phase"], "packaging")

    def test_slug(self):
        self.assertEqual(self.core.slug("Agents 3: The CLI!"), "agents-3-the-cli")

    def test_video_dir_refuses_escape(self):
        for bad in ("../x", "a/b", "", ".hidden", "_inbox"):
            with self.assertRaises(ValueError):
                self.core.video_dir(bad)

    def test_derive_phase_from_state(self):
        v = {"phase": "recording", "origin": "problem"}
        d = self.core.derive_phase
        self.assertEqual(d(v, {"stage": "cutting"}), "cut")
        self.assertEqual(d(v, {"stage": "awaiting-A"}), "cut")
        self.assertEqual(d(v, {"stage": "storyboarding"}), "storyboard")
        self.assertEqual(d(v, {"stage": "awaiting-B"}), "storyboard")
        self.assertEqual(d(v, {"stage": "awaiting-import"}), "render")
        self.assertEqual(d(v, {"stage": "done"}), "packaging")
        self.assertEqual(d({"phase": "publish"}, {"stage": "done"}), "publish")
        self.assertEqual(d({"phase": "script"}, None), "script")
        self.assertEqual(d({}, {"stage": "youtube-ready"}), "packaging")

    def test_existing_pipeline_video_without_video_json(self):
        w = os.path.join(self.root, "videos", "old")
        os.makedirs(w)
        json.dump({"stage": "awaiting-B"}, open(os.path.join(w, "state.json"), "w"))
        v = self.core.load_video("old")
        self.assertEqual(v["name"], "old")
        rows = self.core.list_videos()
        self.assertEqual([(r["name"], r["phase"]) for r in rows], [("old", "storyboard")])

    def test_questions_round_trip(self):
        self.core.scaffold("q", "feature")
        q = self.core.ask("q", "Which face?", options=["Dennis", "guest"])
        self.assertEqual(len(self.core.questions("q")), 1)
        self.assertEqual(self.core.list_videos()[0]["open_questions"], 1)
        self.core.answer("q", q["id"], "guest")
        self.assertEqual(self.core.questions("q")[0]["answer"], "guest")
        self.assertEqual(self.core.list_videos()[0]["open_questions"], 0)

    def test_comments_round_trip(self):
        self.core.scaffold("c", "feature")
        items = [{"id": "1", "t": 12.5, "text": "off centre", "box": [10, 20, 30, 40]}]
        self.core.save_comments("c", "B", items)
        self.assertEqual(self.core.comments("c", "B"), items)
        with self.assertRaises(ValueError):
            self.core.comments("c", "../x")

    def test_list_skips_underscore_folders(self):
        os.makedirs(os.path.join(self.root, "videos", "_inbox"))
        self.core.scaffold("v", "problem")
        self.assertEqual([r["name"] for r in self.core.list_videos()], ["v"])

    def test_phases_content(self):
        ids = [p["id"] for p in self.core.PHASES]
        self.assertEqual(ids, ["ideation", "script", "recording", "cut", "storyboard", "render", "packaging", "publish", "results"])
        for p in self.core.PHASES:
            self.assertEqual(p["forms"][-1]["id"], "freeform", p["id"])

    def test_catalog_status_moves_the_phase(self):
        self.core.scaffold("pub", "problem")
        os.makedirs(os.path.join(self.root, "catalog"))
        open(os.path.join(self.root, "catalog", "VIDEOS.md"), "w").write(
            "<!-- video:pub -->\n### T\n\n- **Status:** scheduled (private until 2026-12-01)\n<!-- /video:pub -->\n")
        self.assertEqual(self.core.current_phase("pub"), "publish")
        self.assertEqual(self.core.list_videos()[0]["waiting_on"], "its go-live date")

    def test_job_runs_and_records(self):
        self.core.scaffold("j", "problem")
        jid = self.core.start_job("j", "test", ["/bin/echo", "hello"])
        self.core.wait_job("j", jid, 10)
        j = self.core.job("j", jid)
        self.assertEqual(j["exit"], 0)
        self.assertIn("hello", j["log"])


if __name__ == "__main__":
    unittest.main()
