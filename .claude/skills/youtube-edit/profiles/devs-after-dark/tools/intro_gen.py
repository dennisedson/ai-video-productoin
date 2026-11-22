import re, sys
s = open("DevsAfterDark-colon-white.svg").read()
paths = re.findall(r'<path[^>]*/?>(?:</path>)?', s)
assert len(paths) == 14, len(paths)
names = ["D1", "e1", "v", "s", "colon", "A", "f", "t", "e2", "r1", "D2", "a", "r2", "k"]
tag = lambda i: re.sub(r'<path', '<path id="g-%s"' % names[i], paths[i], count=1)
VB = 'viewBox="-24 -180.6 1383.62 242.2"'
layerA = "".join(tag(i) for i in range(0, 5))
layerB = "".join(tag(i) for i in range(5, 10))
layerC = "".join(tag(i) for i in range(10, 14))
COLD_DEFAULT = '<div id="cold" data-hold><div class="lbl"><b>&#9679;</b> COLD OPEN &middot; PAST-EPISODE CLIPS &middot; 0&ndash;9 S</div></div>'
cold = sys.argv[1] if len(sys.argv) > 1 else COLD_DEFAULT

page = '''<!doctype html>
<!-- Devs:After Dark intro (15.4 s): cold open (0-9.15 s, past-episode clips) then the wordmark builds on the theme's hits
     ("Decisive Hit": drums 9.15, hits 9.65 / 10.15, the decisive hit 12.22, near silence after). Logo: the official SVG,
     one path per letter, split into three layers (Devs: / After / Dark) with the same viewBox so they overlay exactly. -->
<html lang="en"><head><meta charset="utf-8" />
<style>
  @font-face { font-family: "JetBrains Mono"; src: url("fonts/jetbrains-mono-latin-500-normal.woff2") format("woff2"); font-weight: 500; font-display: block; }
  * { box-sizing: border-box; }
  html, body { margin:0; width:100%; height:100%; overflow:hidden; background:#0F1116; }
  #stage { position:relative; width:1920px; height:1080px; overflow:hidden; background:#0F1116; }
  #vig { position:absolute; inset:0; background: radial-gradient(1500px 1000px at 50% 50%, transparent 50%, rgba(0,0,0,.45) 100%); }
  #glow { position:absolute; left:360px; top:140px; width:1200px; height:800px; border-radius:50%;
          background: radial-gradient(closest-side, rgba(251,191,36,.30), rgba(251,191,36,.08) 55%, transparent 100%); opacity:0; }
  #lamp { position:absolute; inset:0; background: radial-gradient(1000px 700px at 50% 42%, rgba(251,191,36,.07), transparent 70%); opacity:0; }
  #logo { position:absolute; left:210px; top:360px; width:1500px; height:262.6px; transform-origin:50% 55%; }
  #logo .ly { position:absolute; inset:0; }
  #logo svg { position:absolute; inset:0; width:100%; height:100%; overflow:visible; }
  #ly-a { clip-path: inset(0% 0% 23.5% 0%); }
  #g-colon { opacity: 0; }
  #ly-c { clip-path: inset(8% 0% 23.5% 0%); }
  #ly-b { clip-path: polygon(0% 0%, 0% 0%, -12% 100%, -12% 100%); }
  #tag { position:absolute; left:0; width:1920px; top:680px; text-align:center; font-family:"JetBrains Mono", monospace; font-weight:500;
         font-size:30px; letter-spacing:.42em; color:#8A8D99; text-transform:uppercase; opacity:0; }
  #tag em { font-style:normal; color:#FBBF24; }
  #cold { position:absolute; inset:0; background:#0B0D11; }
  #cold .lbl { position:absolute; left:0; width:1920px; top:500px; text-align:center; font-family:"JetBrains Mono", monospace; font-size:28px;
               letter-spacing:.3em; color:#8A8D99; }
  #cold .lbl b { color:#FBBF24; font-weight:500; }
</style></head>
<body>
<div id="stage" data-composition-id="dad-intro" data-start="0" data-duration="15.4" data-fps="30" data-width="1920" data-height="1080">
  <div id="lamp"></div>
  <div id="glow"></div>
  <div id="logo">
    <div class="ly" id="ly-a"><svg xmlns="http://www.w3.org/2000/svg" VB>LA</svg></div>
    <div class="ly" id="ly-b"><svg xmlns="http://www.w3.org/2000/svg" VB>LB</svg></div>
    <div class="ly" id="ly-c"><svg xmlns="http://www.w3.org/2000/svg" VB>LC</svg></div>
  </div>
  <div id="tag">The internet, <em>after</em> bedtime.</div>
  <div id="vig"></div>
  COLD
  <audio id="theme" src="sfx/theme-intro.m4a" data-start="0" data-duration="15.4" data-track-index="20" data-volume="0.9"></audio>
</div>
<script src="vendor/gsap.min.js"></script>
<script>
  const tl = gsap.timeline({ paused: true });
  const DEVS = ['#g-D1','#g-e1','#g-v','#g-s'], DARK = ['#g-D2','#g-a','#g-r2','#g-k'];
  tl.set(DEVS, { y: 175 }, 0);
  tl.set(DARK, { y: -175 }, 0);
    // the cold open hands over on the drums
  tl.to('#cold', { opacity: 0, duration: 0.12, ease: 'none' }, 9.08);
  tl.to('#lamp', { opacity: 1, duration: 1.2, ease: 'power2.out' }, 9.15);
  // 9.15 drums: Devs rises
  tl.to(DEVS, { y: 0, duration: 0.55, ease: 'power4.out', stagger: 0.07 }, 9.12);
  // 9.65 / 9.9 / 10.15: the colon blinks on like a cursor
  tl.set('#g-colon', { opacity: 1 }, 9.65); tl.set('#g-colon', { opacity: 0 }, 9.90); tl.set('#g-colon', { opacity: 1 }, 10.15);
  // 10.15 hit: Dark drops in
  tl.to(DARK, { y: 0, duration: 0.55, ease: 'power4.out', stagger: 0.07 }, 10.12);
  // 10.75-11.9: After slashes in along its italic slant
  tl.to('#ly-b', { clipPath: 'polygon(0% 0%, 112% 0%, 100% 100%, -12% 100%)', duration: 1.15, ease: 'power2.inOut' }, 10.75);
  // 12.22 the decisive hit: the wordmark punches, the amber glow flares and settles
  tl.fromTo('#logo', { scale: 1.0 }, { scale: 1.07, duration: 0.05, ease: 'none', immediateRender: false }, 12.18);
  tl.to('#logo', { scale: 1.0, duration: 0.9, ease: 'elastic.out(1, 0.45)' }, 12.23);
  tl.fromTo('#glow', { opacity: 0 }, { opacity: 1, duration: 0.06, ease: 'none', immediateRender: false }, 12.18);
  tl.to('#glow', { opacity: 0.35, duration: 1.4, ease: 'power2.out' }, 12.26);
  // the quiet after: the tagline
  tl.fromTo('#tag', { opacity: 0, y: 18 }, { opacity: 1, y: 0, duration: 0.9, ease: 'power2.out', immediateRender: false }, 12.7);
  // out to the episode
  tl.to('#stage', { opacity: 0, duration: 0.5, ease: 'power1.in' }, 14.9);
  window.__timelines = window.__timelines || {};
  window.__timelines["dad-intro"] = tl;
</script>
</body></html>
'''
page = page.replace("VB", VB, 3).replace("LA", layerA, 1).replace("LB", layerB, 1).replace("LC", layerC, 1).replace("  COLD\n", "  " + cold + "\n", 1)
open("comp/index.html", "w").write(page)
print("ok", len(page))
