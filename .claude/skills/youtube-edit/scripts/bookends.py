#!/usr/bin/env python3
"""bookends.py: a profile's intro sting and end card, filled in, rendered and joined onto a finished video.

  python3 bookends.py --project videos/<project> [--preview] [--gpu] [--shared shared]

Reads videos/<project>/render.json:
  "bookends": {"intro": {"at": 7.5, "resume": 7.6, "eyebrow": "HubSpot is going headless", "title": "Agents"},
               "outro": {"next": "The agent CLI", "subscribe": "Subscribe for the series", "after": null}}
(outro "next" is optional: without it the card is generic, "Thanks for watching" / "Keep building", or set
"eyebrow" and "title"; in YouTube Studio set the box's video element to "Best for viewer".)
and the storyboard's "profile" (its templates: profiles/<profile>/intro/index.html, outro/index.html).

- intro: the sting cuts in at `at` (a frame in a pause, after the first sentence that names the topic: never before the
  hook) and the video resumes at `resume` (`at` when absent; a little later trims the pause).
- outro: the end card follows the video (or `after`, seconds into it, to drop a tail).
Either key can be left out.

Steps: fill the templates into <project>/bookends/<kind>/ (fonts, GSAP and sfx staged next to them), render each
(4K, or 1080p draft with --preview), then assemble.py joins main + sting + main + end card into <project>/<name>-full-4k.mp4
with levels left alone (the main video is already at -14 LUFS; the sounds keep their mix). Checks the joined duration.
--preview renders the two clips only (bookends/<kind>-preview.mp4), for Checkpoint B.
"""
import argparse, html, json, os, re, shutil, subprocess, sys

SK = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
ap = argparse.ArgumentParser()
ap.add_argument("--project", required=True)
ap.add_argument("--shared", default=None, help="the shared folder with sfx/ (default: render.json 'shared', else 'shared')")
ap.add_argument("--preview", action="store_true", help="1080p draft renders of the clips only")
ap.add_argument("--gpu", action="store_true")
ap.add_argument("--workers", default="1")
args = ap.parse_args()

W = args.project.rstrip("/")
R = json.load(open(os.path.join(W, "render.json")))
S = json.load(open(os.path.join(W, "storyboard.json")))
B = R.get("bookends") or sys.exit("render.json has no 'bookends'")
prof = S.get("profile") or sys.exit("the storyboard names no profile (bookends live in a profile)")
PD = os.path.join(SK, "profiles", prof)
shared = args.shared or R.get("shared", "shared")
name = R.get("name", os.path.basename(W))
out_dir = os.path.join(W, "bookends")

def run(cmd, **kw):
    print("   $ " + " ".join(cmd[:6]) + (" ..." if len(cmd) > 6 else ""), flush=True)
    subprocess.run(cmd, check=True, **kw)

def dur(path):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                                capture_output=True, text=True, check=True).stdout.strip())

def stream_durs(path):
    j = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,duration", "-of", "json", path],
                                  capture_output=True, text=True, check=True).stdout)
    return {s["codec_type"]: float(s.get("duration") or 0) for s in j["streams"]}

def spans(text, per):
    e = html.escape
    if per == "letter":
        return "".join("<span>%s</span>" % ("&nbsp;" if c == " " else e(c)) for c in text)
    return " ".join("<span>%s</span>" % e(w) for w in text.split())

def build(kind, fields):
    tpl = os.path.join(PD, kind, "index.html")
    if not os.path.exists(tpl): sys.exit("profile %s has no %s template (%s)" % (prof, kind, tpl))
    d = os.path.join(out_dir, kind)
    page = open(tpl).read()
    for k, v in fields.items(): page = page.replace("{{%s}}" % k, v)
    old = os.path.join(d, "index.html")
    reuse[kind] = os.path.exists(old) and open(old).read() == page
    left = re.findall(r"\{\{[A-Z_]+\}\}", page)
    if left: sys.exit("%s template: unfilled %s" % (kind, ", ".join(sorted(set(left)))))
    shutil.rmtree(d, ignore_errors=True); os.makedirs(os.path.join(d, "fonts")); os.makedirs(os.path.join(d, "vendor"))
    open(os.path.join(d, "index.html"), "w").write(page)
    for f in os.listdir(os.path.join(PD, "fonts")):
        shutil.copy(os.path.join(PD, "fonts", f), os.path.join(d, "fonts", f))
    shutil.copy(os.path.join(SK, "assets", "vendor", "gsap.min.js"), os.path.join(d, "vendor", "gsap.min.js"))
    for sfx in sorted(set(re.findall(r'src="sfx/([^"]+)"', page))):
        src = os.path.join(shared, "sfx", sfx)
        if not os.path.exists(src): sys.exit("missing sound %s (the %s template uses it)" % (src, kind))
        os.makedirs(os.path.join(d, "sfx"), exist_ok=True); shutil.copy(src, os.path.join(d, "sfx", sfx))
    if os.path.isdir(os.path.join(PD, "assets")):   # profile artwork the templates use (the HubSpot sprocket)
        shutil.copytree(os.path.join(PD, "assets"), os.path.join(d, "assets"))
    hj = os.path.join(W, "public", "hyperframes.json")
    if os.path.exists(hj): shutil.copy(hj, os.path.join(d, "hyperframes.json"))
    return d

def render(kind, d):
    run(["npx", "--yes", "hyperframes", "check", d])
    if args.preview:
        o = os.path.join(out_dir, "%s-preview.mp4" % kind)
        run(["npx", "--yes", "hyperframes", "render", d, "--quality", "draft", "--workers", args.workers, "-o", o])
    else:
        o = os.path.join(out_dir, "%s-4k.mp4" % kind)
        if os.path.exists(o) and reuse.get(kind):
            print("   %s: reusing %s (text unchanged)" % (kind, o)); return o
        cmd = ["npx", "--yes", "hyperframes", "render", d, "--resolution", "4k", "--video-bitrate", R.get("bitrate", "45M"), "--workers", args.workers]
        if args.gpu: cmd.append("--gpu")
        run(cmd + ["-o", o])
    return o

clips, reuse = {}, {}
if "intro" in B:
    i = B["intro"]
    clips["intro"] = render("intro", build("intro", {"EYEBROW": html.escape(i.get("eyebrow", "")), "TITLE": spans(i["title"], "letter")}))
if "outro" in B:
    o = B["outro"]
    if o.get("next"):            # a named next video; otherwise generic (YouTube's "Best for viewer" fills the box)
        eyebrow, title = o.get("eyebrow", "Up next"), o["next"]
    else:
        eyebrow, title = o.get("eyebrow", "Thanks for watching"), o.get("title", "Keep building")
    clips["outro"] = render("outro", build("outro", {"EYEBROW": html.escape(eyebrow), "TITLE": spans(title, "word"),
                                                     "SUBSCRIBE": html.escape(o.get("subscribe", "Subscribe for the series"))}))
if args.preview:
    print("previews: " + ", ".join(clips.values())); sys.exit(0)

main = os.path.join(W, "%s-4k.mp4" % name)
if not os.path.exists(main): sys.exit("no %s (render-mac.sh makes it in its loudness step)" % main)
md = dur(main)
title = B.get("intro", {}).get("title") or name
after = B.get("outro", {}).get("after")
end = float(after) if after is not None else None
segs, expect = [], 0.0
if "intro" in clips:
    at, resume = float(B["intro"]["at"]), float(B["intro"].get("resume", B["intro"]["at"]))
    if not 0 < at <= resume < md: sys.exit("intro at/resume must sit inside the video (0 < at <= resume < %.2f)" % md)
    segs += [{"name": title, "file": os.path.abspath(main), "trim": [0, at]},
             {"name": "Intro sting", "file": os.path.abspath(clips["intro"]), "chapter": False},
             {"name": title + " (cont.)", "file": os.path.abspath(main), "trim": [resume, end], "chapter": False}]
    expect += at + dur(clips["intro"]) + ((end or md) - resume)
else:
    segs.append({"name": title, "file": os.path.abspath(main), "trim": [0, end]}); expect += end or md
if "outro" in clips:
    segs.append({"name": "End card", "file": os.path.abspath(clips["outro"]), "chapter": False}); expect += dur(clips["outro"])

man = os.path.join(W, "assembly-bookends.json")
json.dump({"project": name, "loudness": None, "segments": segs}, open(man, "w"), indent=1)
full = os.path.join(W, "%s-full-4k.mp4" % name)
run(["python3", os.path.join(SK, "scripts", "assemble.py"), "--manifest", man, "--out", full, "--work", os.path.abspath(os.path.join(W, "bookends-work"))] + (["--gpu"] if args.gpu else []))

got, sd = dur(full), stream_durs(full)
ok_len = abs(got - expect) <= 3 / 30.0
ok_av = abs(sd.get("video", 0) - sd.get("audio", 0)) <= 0.12
print("joined: %.3f s (expected %.3f), video %.3f / audio %.3f" % (got, expect, sd.get("video", 0), sd.get("audio", 0)))
if not (ok_len and ok_av):
    sys.exit("FAIL: the joined file's %s is off" % ("length" if not ok_len else "audio/video sync"))
print("bookends OK: %s" % full)
