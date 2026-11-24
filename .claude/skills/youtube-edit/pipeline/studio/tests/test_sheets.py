import os, unittest
from helpers import temp_root, cleanup

SCRIPT = """# Script: Agents 3

Intro text that isn't read.

## Hook
> Stop paying an agent to do the same job twice. Today we turn one run into a script you keep.
→ demo: log in with the CLI

```copy: Log in
hubspot auth login
```

## Sign-off
> Got questions? Put them down below. Until next time.

```copy: The exercise
https://github.com/hubspotdev/builder-exercises
```
See also https://developers.hubspot.com/docs/guide for more.
"""


class SheetsTest(unittest.TestCase):
    def setUp(self):
        self.root, self.core = temp_root()
        import importlib, script_sheets
        importlib.reload(script_sheets)
        self.ss = script_sheets

    def tearDown(self):
        cleanup(self.root)

    def test_teleprompter_has_only_reads_and_markers(self):
        tp, sheet, links = self.ss.build(SCRIPT)
        self.assertNotIn("Intro text", tp)
        self.assertIn("HOOK", tp)
        self.assertIn("→ DEMO: log in with the CLI", tp)
        self.assertNotIn("hubspot auth login", tp)
        for line in tp.splitlines():
            if not line.startswith(("→", "—")) and line.strip():
                self.assertLessEqual(len(line), 32, line)
        self.assertIn("Stop paying", tp)

    def test_sheet_numbers_copy_blocks_in_order(self):
        tp, sheet, links = self.ss.build(SCRIPT)
        self.assertLess(sheet.index("1. Log in"), sheet.index("2. The exercise"))
        self.assertIn("hubspot auth login", sheet)
        self.assertIn("log in with the CLI", sheet)

    def test_links_found(self):
        _, _, links = self.ss.build(SCRIPT)
        urls = [u for _, u in links]
        self.assertIn("https://github.com/hubspotdev/builder-exercises", urls)
        self.assertIn("https://developers.hubspot.com/docs/guide", urls)

    def test_run_writes_files_and_merges_references(self):
        w = self.core.scaffold("s", "problem")
        open(os.path.join(w, "SCRIPT.md"), "w").write(SCRIPT)
        with open(os.path.join(w, "references.md"), "a") as f:
            f.write("| Guide | https://developers.hubspot.com/docs/guide | desc | live | 2026-11-24 |\n")
        self.ss.run("s")
        self.ss.run("s")
        refs = open(os.path.join(w, "references.md")).read()
        self.assertEqual(refs.count("https://developers.hubspot.com/docs/guide"), 1)
        self.assertEqual(refs.count("https://github.com/hubspotdev/builder-exercises"), 1)
        self.assertTrue(os.path.isfile(os.path.join(w, "teleprompter.txt")))
        self.assertTrue(os.path.isfile(os.path.join(w, "recording-sheet.md")))


if __name__ == "__main__":
    unittest.main()
