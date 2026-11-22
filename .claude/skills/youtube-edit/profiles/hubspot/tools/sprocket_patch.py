#!/usr/bin/env python3
"""Patch the HubSpot intro/outro templates: the official sprocket (assets/hubspot-sprocket.svg) builds itself.
Usage: sprocket_patch.py <profile_dir>
The sprocket is one compound path, so each piece is the same image under its own clip: the ring (a circle), each spoke
(a wedge from the hub, revealed by a growing circle), each end circle (a circle, popped by scale). Measured on the file.
"""
import math, re, sys

PD = sys.argv[1]
HX, HY = 248.6, 208.3                    # hub centre (the hole), viewBox units = px at scale 1
NODES = [  # centre, radius, distance from hub where the end circle starts, angle range of the spoke
    ("t",  248.8, 46.5, 32.5, 129.3, -101.6, -78.3),
    ("bl", 130.8, 323.8, 29.6, 135.4, 125.2, 146.0),
    ("tl", 41.5, 38.5, 36.0, 231.8, -148.4, -130.0),
]
IMG = '<img src="assets/hubspot-sprocket.svg" alt="">'

def css():
    c = ["  /* the HubSpot sprocket (official file), built piece by piece */",
         "  .spr { position:absolute; width:346px; height:356px; transform-origin:0 0; }",
         "  .spr .rot { position:absolute; inset:0; transform-origin:%.1fpx %.1fpx; }" % (HX, HY),
         "  .spr .pc { position:absolute; inset:0; }",
         "  .spr img { position:absolute; left:0; top:0; width:345.8px; height:356px; display:block; }",
         "  .spr .hub { clip-path: circle(92.5px at %.1fpx %.1fpx); transform-origin:%.1fpx %.1fpx; }" % (HX, HY, HX, HY)]
    for k, x, y, r, s, a0, a1 in NODES:
        a0, a1, R = math.radians(a0 - 5), math.radians(a1 + 5), 520
        am = (a0 + a1) / 2
        pts = [(HX, HY)] + [(HX + R * math.cos(a), HY + R * math.sin(a)) for a in (a0, am, a1)]
        c.append("  .spr .w-%s { clip-path: polygon(%s); }" % (k, ", ".join("%.1fpx %.1fpx" % p for p in pts)))
        c.append("  .spr .g-%s { clip-path: circle(92px at %.1fpx %.1fpx); }" % (k, HX, HY))
        c.append("  .spr .n-%s { clip-path: circle(%.1fpx at %.1fpx %.1fpx); transform-origin:%.1fpx %.1fpx; }" % (k, r + 2, x, y, x, y))
    return "\n".join(c) + "\n"

def html(pid, style):
    h = ['    <div class="spr" id="%s" style="%s"><div class="rot">' % (pid, style)]
    for k, *_ in NODES:
        h.append('      <div class="pc w-%s"><div class="pc g-%s">%s</div></div>' % (k, k, IMG))
    for k, *_ in NODES:
        h.append('      <div class="pc n-%s">%s</div>' % (k, IMG))
    h.append('      <div class="pc hub">%s</div>' % IMG)
    h.append('    </div></div>')
    return "\n".join(h) + "\n"

def js(pid, t0, scale, exit_t=None):
    q = lambda sel: "#%s %s" % (pid, sel)
    j = ["  // sprocket: spins in from -120 deg while the ring pops, the spokes grow out, the end circles snap on; ends upright",
         "  tl.set('#%s', { scale: %.4f }, 0);" % (pid, scale),
         "  tl.set('%s', { rotation: -120 }, 0);" % q(".rot"),
         "  tl.set('%s', { scale: 0 }, 0);" % q(".hub")]
    for k, *_ in NODES:
        j.append("  tl.set('%s', { scale: 0 }, 0);" % q(".n-" + k))
        j.append("  tl.set('%s', { clipPath: 'circle(0.0px at %.1fpx %.1fpx)' }, 0);" % (q(".g-" + k), HX, HY))
    j.append("  tl.to('%s', { rotation: 0, duration: 1.1, ease: 'power3.out' }, %.2f);" % (q(".rot"), t0))
    j.append("  tl.to('%s', { scale: 1, duration: 0.45, ease: 'back.out(2.2)' }, %.2f);" % (q(".hub"), t0))
    t = t0 + 0.30
    for k, x, y, r, s, a0, a1 in NODES:
        dur = 0.18 + (s - 92) / 600.0
        j.append("  tl.fromTo('%s', { clipPath: 'circle(90.0px at %.1fpx %.1fpx)' }, { clipPath: 'circle(%.1fpx at %.1fpx %.1fpx)', duration: %.2f, ease: 'power2.out', immediateRender: false }, %.2f);"
                 % (q(".g-" + k), HX, HY, s + 4, HX, HY, dur, t))
        j.append("  tl.to('%s', { scale: 1, duration: 0.34, ease: 'back.out(3)' }, %.2f);" % (q(".n-" + k), t + dur - 0.05))
        t += 0.09
    if exit_t is not None:
        j.append("  tl.to('%s', { rotation: 90, scale: 0, duration: 0.42, ease: 'back.in(1.6)' }, %.2f);" % (q(".rot"), exit_t))
    return "\n".join(j) + "\n"

# ---- intro: the sprocket replaces the node graphic on the right
p = PD + "/intro/index.html"; s = open(p).read()
s = re.sub(r"  #net \{[^\n]*\n  \.ln \{[^\n]*\n  \.nd \{[^\n]*\n  #hub \{[^\n]*\n  \.sat \{[^\n]*\n  \.sat\.pink \{[^\n]*\n", css(), s)
s = re.sub(r'    <div id="net">.*?\n    </div>\n', html("spr", "left:1407px; top:362px;"), s, flags=re.S)
s = "\n".join(l for l in s.split("\n") if not re.search(r"tl\.(set|to)\('(\.ln|\.nd|#hub|\.sat|#net)'", l))
s = s.replace("  // in\n", "  // in\n" + js("spr", 0.26, 1.0, exit_t=2.40), 1)
assert "spr" in s and "#net" not in s and ".sat" not in s, "intro patch failed"
open(p, "w").write(s)

# ---- end card: the sprocket above the text column
p = PD + "/outro/index.html"; s = open(p).read()
s = s.replace("  #fade {", css() + "  #fade {", 1)
s = s.replace('    <div class="mask" id="eyebrow-m">', html("spr", "left:164px; top:120px;") + '    <div class="mask" id="eyebrow-m">', 1)
s = s.replace("  tl.to('#eyebrow', { y: 0,", js("spr", 0.05, 0.47) + "  tl.to('#eyebrow', { y: 0,", 1)
assert s.count('class="spr"') == 1, "outro patch failed"
open(p, "w").write(s)
print("patched intro and outro")
