"""compose.py, the tutorial layout (format 23): face card left or right, the screen plate, full-frame stretches, zooms."""
import os, unittest
from .helpers import run, scratch, write, read


def board(face="right", **extra):
    lay = {"type": "tutorial", "face": face, "screen": "screen.mp4", "plate_in": 2.0,
           "full": [[5.0, 8.0], [10.0, None]], "zooms": [{"at": 11.0, "rect": [480, 270, 1440, 810], "dur": 0.6}]}
    lay.update(extra)
    return {"id": "t", "duration": 14.0, "layout": lay,
            "beats": [{"type": "line", "id": "l1", "text": "On the screen side", "in": 1.0, "out": 4.0, "anchor": "-"},
                      {"type": "line", "id": "l2", "text": "Full frame line", "in": 6.0, "out": 7.5, "anchor": "-"}]}


class TutorialLayout(unittest.TestCase):
    def build(self, spec):
        d = scratch(self)
        sp = write(os.path.join(d, "storyboard.json"), spec)
        r = run("compose.py", "--spec", sp, "--out", os.path.join(d, "public"))
        return r, (read(os.path.join(d, "public", "index.html")) if r.returncode == 0 else "")

    def test_face_right_and_left(self):
        for face, card_x, side_x, plate_x in (("right", 1304, 0, 48), ("left", 24, 640, 688)):
            r, page = self.build(board(face))
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("#video-wrap { left:%dpx; top:24px;" % card_x, page)
            self.assertIn("#host-l1 { left:%dpx !important; width:1280px !important; }" % side_x, page)   # split-time copy sits on the screen side
            self.assertNotIn("#host-l2", page.split("tutorial layout")[1].split("</style>")[0])           # a line inside a full stretch stays full width
            self.assertIn("tl.set('#tut-screen', { x: %d, y: 207, scale: 0.6167" % plate_x, page)
            self.assertIn('id="tut-screen" class="clip" src="screen.mp4" muted', page)
            self.assertIn("scale: 2.0000", page)                                                         # the zoom fills the frame with its rect

    def test_face_full_intro(self):
        spec = board("left", face_crop={"x": 1505, "y": 0, "w": 1110, "h": 1936, "src": [3840, 2160]}, face_full=[[0, 4.4]])
        spec["beats"][0]["in"] = 0.5                                      # a line in the intro stays full width
        r, page = self.build(spec)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("tl.set('#bg-video', { x: 0, y: 0, scale: 1 }", page)                    # the intro starts full frame
        self.assertIn("tl.to('#video-wrap', { clipPath: 'inset(24px 1304px 24px 24px round 28px)', duration: 0.6", page)
        self.assertIn("tl.to('#bg-video', { x: -778.7, y: 24.0, scale: 1.0667, duration: 0.6", page)   # the crop lands in the card
        self.assertNotRegex(page, r"tl\.(to|set)\('#(video-wrap|bg-video)', \{ (left|top|width|height):")   # transforms only
        self.assertNotIn("#host-l1 {", page)
        r, _ = self.build(board("left", face_full=[[0, 4.4]]))                  # face_full needs face_crop
        self.assertNotEqual(r.returncode, 0)

    def test_full_frame_intro_by_default(self):
        crop = {"x": 1505, "y": 0, "w": 1110, "h": 1936, "src": [3840, 2160]}
        r, page = self.build(board("left", face_crop=crop, plate_in=4.7))        # no face_full: the intro is full frame
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("full-frame intro by default, 0-4.40", r.stdout)
        self.assertIn("tl.set('#bg-video', { x: 0, y: 0, scale: 1 }", page)
        self.assertNotIn("#host-l1 {", page)                                   # the intro line keeps the full width
        r, page = self.build(board("left", face_crop=crop, plate_in=4.7, face_full=[]))   # opted out: card from frame one
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("full-frame intro", r.stdout)
        self.assertIn("#host-l1 {", page)
        r, _ = self.build(board("left", face_crop=crop))                         # plate at 2.0 s: too soon for an intro
        self.assertNotIn("full-frame intro", r.stdout)

    def test_guards(self):
        r, _ = self.build(board("middle"))
        self.assertNotEqual(r.returncode, 0)
        r, _ = self.build(board(zooms=[{"at": 9.0, "rect": [0, 0, 960, 540]}]))       # 9.0 is in the split between stretches
        self.assertNotEqual(r.returncode, 0)
        r, _ = self.build(board(full=[[5.0, 8.0], [8.2, None]]))                          # stretches too close to animate
        self.assertNotEqual(r.returncode, 0)
