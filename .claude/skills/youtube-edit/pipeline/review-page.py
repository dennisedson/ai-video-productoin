#!/usr/bin/env python3
"""review-page.py W A|B: a local review page for a checkpoint (REVIEW-A.html / REVIEW-B.html in the video folder), opened
by the notification. Plays the review video (A) or the preview render (B), shows the stills and the write-up, and ends
with how to approve. Static HTML, relative paths, nothing leaves the Mac."""
import html, os, sys
W, which = sys.argv[1], sys.argv[2].upper()
name = os.path.basename(os.path.normpath(W))
rel = lambda p: "%s?v=%d" % (p, os.path.getmtime(os.path.join(W, p))) if os.path.exists(os.path.join(W, p)) else None
if which == "A":
    title, video, doc = "Checkpoint A: the cut", rel("review/cut-review.mp4"), "PAPER-CUT.md"
    images = [("Camera grade options", rel("snaps/grade-options.png")), ("Screen windows", rel("snaps/screen-windows.png"))]
    approve = "approve %s (grade: blacks)" % name
else:
    title, video, doc = "Checkpoint B: storyboard and preview", rel("review/preview.mp4"), "CHECKPOINT-B.md"
    images = [("Every overlay and layout change", rel("snaps/sheet.png"))]
    approve = "approve %s" % name
variants = sorted(f for f in os.listdir(os.path.join(W, "review", "variants"))) if os.path.isdir(os.path.join(W, "review", "variants")) else []
text = open(os.path.join(W, doc)).read() if os.path.exists(os.path.join(W, doc)) else "(%s is missing)" % doc
parts = ['<!doctype html><meta charset="utf-8"><title>%s · %s</title>' % (html.escape(name), title),
         '<style>body{font:16px/1.5 -apple-system,system-ui,sans-serif;max-width:1180px;margin:32px auto;padding:0 24px;color:#110C0A;background:#F5F0EE}'
         'h1{font-size:28px;margin:0 0 4px}h2{font-size:19px;margin:32px 0 8px}video,img{width:100%;border-radius:14px;background:#042729}'
         'pre{white-space:pre-wrap;background:#fff;padding:18px;border-radius:14px;font:14px/1.5 ui-monospace,Menlo,monospace}'
         '.ok{background:#042729;color:#fff;padding:18px 22px;border-radius:14px}code{background:#FF4800;color:#fff;padding:2px 8px;border-radius:6px}</style>',
         "<h1>%s</h1><div>%s</div>" % (html.escape(name), title)]
if video:
    parts.append('<h2>Watch</h2><video src="%s" controls preload="metadata"></video>' % video)
for v in variants:
    parts.append('<h2>Variant: %s</h2><video src="review/variants/%s?v=%d" controls preload="metadata"></video>' % (html.escape(v), v, os.path.getmtime(os.path.join(W, "review", "variants", v))))
for cap, img in images:
    if img:
        parts.append('<h2>%s</h2><img src="%s">' % (cap, img))
parts.append("<h2>%s</h2><pre>%s</pre>" % (doc, html.escape(text)))
parts.append('<div class="ok">Approve or send notes in a Claude Code thread on the Video folder, for example <code>%s</code>, '
             'or <code>%s: notes ...</code>. Status of every edit: <code>yt status</code>.</div>' % (html.escape(approve), html.escape(name)))
out = os.path.join(W, "REVIEW-%s.html" % which)
open(out, "w").write("\n".join(parts))
print(out)
