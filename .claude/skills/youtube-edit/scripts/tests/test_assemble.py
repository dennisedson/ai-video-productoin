"""assemble.py: a one-segment manifest at the master spec (render-mac.sh's loudness pass) keeps the video stream
bit for bit and redoes only the audio; a trimmed segment or several segments are still conformed (re-encoded)."""
import os, subprocess, unittest
from .helpers import ffmpeg, needs_ffmpeg, probe, run, scratch, write


def video_hash(path):   # the decoded pictures: the BT.709 remux rewrites the stream headers, never a picture,
    return subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-map", "0:v:0", "-f", "hash", "-hash", "md5", "-"],   # and no re-encode matches bit for bit
                          capture_output=True, text=True, check=True).stdout.strip()


@needs_ffmpeg
class Assemble(unittest.TestCase):
    def clip(self, d, name, size="320x180", rate=30, dur=4):
        p = os.path.join(d, name)
        ffmpeg("-f", "lavfi", "-i", "testsrc2=size=%s:rate=%s:duration=%s" % (size, rate, dur),
               "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=%s" % dur, "-af", "volume=-20dB",
               "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", p)
        return p

    def assemble(self, d, segments):
        man = write(os.path.join(d, "assembly.json"), {"project": "t", "width": 320, "height": 180, "fps": 30, "loudness": -14,
                                                       "segments": segments})
        out = os.path.join(d, "out", "t-4k.mp4")
        r = run("assemble.py", "--manifest", man, "--out", out)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return out, r.stdout

    def test_one_segment_at_spec_copies_the_video(self):
        d = scratch(self)
        src = self.clip(d, "render.mp4")
        out, log = self.assemble(d, [{"name": "t", "file": "render.mp4"}])
        self.assertIn("video copied", log)
        self.assertEqual(video_hash(out), video_hash(src))
        streams, _ = probe(out)
        self.assertLessEqual(abs(streams["video"] - 4.0), 1 / 30 + 1e-6)
        self.assertLessEqual(abs(streams["video"] - streams["audio"]), 0.12)

    def test_trim_size_or_several_segments_are_conformed(self):
        d = scratch(self)
        src = self.clip(d, "render.mp4")
        self.clip(d, "small.mp4", size="160x90")
        for segs in ([{"name": "t", "file": "render.mp4", "trim": [1.0, 3.0]}],
                     [{"name": "t", "file": "small.mp4"}],
                     [{"name": "a", "file": "render.mp4"}, {"name": "b", "file": "render.mp4"}]):
            out, log = self.assemble(d, segs)
            self.assertNotIn("video copied", log, segs)
            self.assertNotEqual(video_hash(out), video_hash(src), segs)


if __name__ == "__main__":
    unittest.main()
