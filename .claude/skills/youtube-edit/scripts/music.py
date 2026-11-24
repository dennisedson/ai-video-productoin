#!/usr/bin/env python3
"""music.py: the background music pass, timed to the video. Picked while the 4K render runs, mixed in at its end.

  python3 music.py plan    --project DIR              the published timeline (sting, its hit, end card), the 30 s
                                                       sample window, how many Epidemic edits the length needs
                                                       -> music/plan.json
  python3 music.py analyze --project DIR --track F [--drop T] [--edit A|B]
                                                       a track's tempo, beats and its drops (bar-aligned rises in
                                                       energy); prints the EditRecording input that puts the drop on
                                                       the sting's hit (edit A) or fills the rest (edit B)
  python3 music.py check   --project DIR --file F      where the beats of a finished edit land against the hit
  python3 music.py samples --project DIR              music/cand-N.wav (edit A of each candidate) under the same
                                                       30 s of the video -> music/samples/N.mp4 + MUSIC-REVIEW.html
  python3 music.py mix     --project DIR --pick N     the chosen bed (cand-N.wav, plus cand-N-b.wav when the video
                                                       is longer than one edit) ducked under the voice on the finished
                                                       video -> <video>-music.mp4 next to it (the no-music twin
                                                       stays), MUSIC.md
  python3 music.py none    --project DIR              no music for this video (music/choice.json says so)
  python3 music.py choose  --project DIR --pick N     record the pick; the render's music step mixes it
  python3 music.py status  --project DIR              off | none | chosen N | pending (for the render's music step)

DIR is the video's folder: videos/<name>, or videos/_render-inbox/<name> on the home Mac. All times are on the
published video's clock: the hook, the 3 s sting cut in at bookends.intro.at, the rest from `resume`, the end card.
The profile's music.json sets whether the pass runs, the levels and the brief for picking; music/levels.json in the
video's folder overrides the levels for that video. Each track is first brought to the same loudness (ref_lufs), so
the levels mean the same for every track and the samples compare fairly.
"""
import argparse, glob, html, json, os, re, shutil, subprocess, sys

SK = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
ap = argparse.ArgumentParser()
ap.add_argument("cmd", choices=["plan", "analyze", "check", "samples", "mix", "none", "choose", "status"])
ap.add_argument("--project", required=True)
ap.add_argument("--track")
ap.add_argument("--file")
ap.add_argument("--drop", type=float, help="analyze: use this drop (seconds into the track) instead of the best one")
ap.add_argument("--edit", default="A", choices=["A", "B"])
ap.add_argument("--pick", type=int)
a = ap.parse_args()
W = os.path.abspath(a.project.rstrip("/"))
M = os.path.join(W, "music")
os.makedirs(M, exist_ok=True)
EDIT_MAX = 295.0          # Epidemic edits stop at 300 s; keep a margin


def load(p, d=None):
    try:
        return json.load(open(p))
    except (OSError, ValueError):
        return d


def run(cmd, quiet=True):
    return subprocess.run([str(c) for c in cmd], capture_output=quiet, text=True)


def dur(p):
    r = run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p])
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


R = load(os.path.join(W, "render.json"), {}) or {}
S = load(os.path.join(W, "storyboard.json"), {}) or {}
PROFILE = S.get("profile") or "hubspot"
PD = os.path.join(SK, "profiles", PROFILE)
CFG = {"pass": True, "ref_lufs": -10, "hook_db": -16, "body_db": -19, "card_db": -14, "hit_offset": None,
       "brief": "instrumental, no vocals, confident and modern, steady under talk"}
CFG.update(load(os.path.join(PD, "music.json"), {}) or {})
CFG.update(load(os.path.join(W, "music", "levels.json"), {}) or {})     # this video only: {"hook_db": -14, ...}
NAME = R.get("name", os.path.basename(W))


def template_len(kind, default):
    try:
        m = re.search(r'data-composition-id="[^"]+"[^>]*data-duration="([0-9.]+)"', open(os.path.join(PD, kind, "index.html")).read())
        return float(m.group(1)) if m else default
    except OSError:
        return default


def hit_offset():
    if CFG.get("hit_offset") is not None:
        return float(CFG["hit_offset"])
    try:                                                     # the sting's impact sound
        m = re.search(r'id="sfx-hit"[^>]*data-start="([0-9.]+)"', open(os.path.join(PD, "intro", "index.html")).read())
        return float(m.group(1)) if m else 0.3
    except OSError:
        return 0.3


def flat_duration():
    cm = load(os.path.join(W, "cut-map.json"), {}) or {}
    if cm.get("flat_duration"):
        return float(cm["flat_duration"])
    for f in ("public/input-video.mp4", "%s-4k.mp4" % NAME):
        if os.path.isfile(os.path.join(W, f)):
            return dur(os.path.join(W, f))
    words = load(os.path.join(W, "transcript.json"), []) or []
    return words[-1]["end"] if words else 0.0


def timeline():
    B = R.get("bookends") or {}
    flat = flat_duration()
    t = {"flat": round(flat, 3)}
    if "intro" in B:
        at = float(B["intro"]["at"]); resume = float(B["intro"].get("resume", at))
        il = template_len("intro", 3.0)
        t.update(sting_in=at, sting_out=round(at + il, 3), hit=round(at + hit_offset(), 3), resume=resume, intro_len=il)
    after = (B.get("outro") or {}).get("after")
    end_flat = float(after) if after is not None else flat
    body = (t["sting_in"] + t["intro_len"] + end_flat - t["resume"]) if "sting_in" in t else end_flat
    ol = template_len("outro", 15.0) if "outro" in B else 0.0
    t.update(card_start=round(body, 3), card_len=ol, total=round(body + ol, 3))
    return t


def to_published(x, t):
    """A time on the flat cut's clock -> the published clock."""
    if "sting_in" not in t:
        return x
    return x if x < t["sting_in"] else (None if x < t["resume"] else x - t["resume"] + t["sting_out"])


def split_point(t):
    """Where edit A ends when the video is longer than one edit: the longest pause between 200 s and 295 s."""
    words = load(os.path.join(W, "transcript.json"), []) or []
    best, gap = None, 0.0
    for w0, w1 in zip(words, words[1:]):
        g0, g1 = to_published(w0["end"], t), to_published(w1["start"], t)
        if g0 is None or g1 is None or not 200 <= g0 <= EDIT_MAX - 2:
            continue
        if g1 - g0 > gap:
            best, gap = (g0 + g1) / 2, g1 - g0
    return round(best if best else min(EDIT_MAX - 5, t["total"] / 2), 2)


def plan():
    t = timeline()
    hit = t.get("hit", 0.0)
    ws = max(0.0, hit - 20.0)
    we = min(t["total"], ws + 30.0)
    edits = [{"edit": "A", "start": 0.0, "end": t["total"]}]
    if t["total"] > EDIT_MAX:
        sp = split_point(t)
        edits = [{"edit": "A", "start": 0.0, "end": sp, "overlap": 4.0}, {"edit": "B", "start": sp, "end": t["total"]}]
    p = {"name": NAME, "profile": PROFILE, "timeline": t, "window": [round(ws, 2), round(we, 2)], "edits": edits,
         "levels": {k: CFG[k] for k in ("hook_db", "body_db", "card_db")}, "brief": CFG.get("brief"), "pass": CFG.get("pass", True)}
    json.dump(p, open(os.path.join(M, "plan.json"), "w"), indent=1)
    return p


# ---- analysis ---------------------------------------------------------------------------------------------------
def beats_of(f):
    r = run(["npx", "--yes", "hyperframes", "beats", f, "--json"])
    try:
        d = json.loads(r.stdout[r.stdout.index("{"):])
        return float(d.get("bpm") or 0), [float(x) for x in d.get("beatTimes", [])]
    except (ValueError, KeyError):
        return 0.0, []


def energy(f, beats):
    """RMS between consecutive beats (mono, 11 kHz)."""
    import numpy as np
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", f, "-ac", "1", "-ar", "11025", "-f", "f32le", "-"], capture_output=True).stdout
    x = np.frombuffer(raw, dtype=np.float32)
    sr = 11025.0
    e = []
    for b0, b1 in zip(beats, beats[1:]):              # 30 ms early: a beat is marked just after its attack
        seg = x[max(0, int((b0 - 0.03) * sr)):max(0, int((b1 - 0.03) * sr))]
        e.append(float(np.sqrt(np.mean(seg ** 2))) if len(seg) else 0.0)
    return e


def drops(f):
    bpm, beats = beats_of(f)
    if len(beats) < 24:
        return bpm, beats, []
    e = energy(f, beats)
    rise = [max(0.0, e[i] - e[i - 1]) for i in range(1, len(e))]
    phase = max(range(4), key=lambda p: sum(rise[i - 1] for i in range(1, len(e)) if i % 4 == p))   # bar starts
    peak = max(e) or 1.0
    cands = []
    for i in range(8, len(e) - 4):
        if i % 4 != phase:
            continue
        after, before = sum(e[i:i + 4]) / 4, sum(e[i - 8:i]) / 8
        score = (after / (before + 1e-6)) * (after / peak)                  # a jump, into something loud
        cands.append((score, beats[i], after / peak))
    cands.sort(reverse=True)
    out = []
    for sc, tm, lvl in cands:
        if all(abs(tm - o["t"]) > 8 * 60.0 / max(bpm, 1) for o in out):
            out.append({"t": round(tm, 3), "score": round(sc, 2), "level": round(lvl, 2)})
        if len(out) == 3:
            break
    return bpm, beats, out


def nearest(beats, t):
    return min(beats, key=lambda b: abs(b - t)) if beats else None


# ---- the mix ------------------------------------------------------------------------------------------------------
def norm_db(f, ref=-10.0):
    """Static gain that brings a track to the reference loudness, so the levels mean the same for every track."""
    r = run(["ffmpeg", "-nostats", "-i", f, "-af", "ebur128", "-f", "null", "-"]).stderr
    I = re.findall(r"I:\s+(-?[0-9.]+) LUFS", r)
    return round(ref - float(I[-1]), 2) if I and float(I[-1]) > -70 else 0.0


def gain_expr(t, t0=0.0, g=0.0):
    """Piecewise-linear music level in dB on the published clock (shifted by t0 for a window), as a volume expression."""
    pts = [(0.0, CFG["hook_db"])]
    if "sting_out" in t:
        pts += [(t["sting_out"], CFG["hook_db"]), (t["sting_out"] + 2.0, CFG["body_db"])]
    pts += [(max(t["card_start"] - 1.0, pts[-1][0]), CFG["body_db"] if "sting_out" in t else CFG["hook_db"]),
            (t["card_start"], CFG["card_db"]), (t["total"] + 60, CFG["card_db"])]
    T = "(t+%.3f)" % t0
    expr = "%.2f" % pts[-1][1]
    for (x0, y0), (x1, y1) in reversed(list(zip(pts, pts[1:]))):
        seg = "%.2f" % y0 if x1 - x0 < 1e-3 else "(%.2f+(%.2f)*(%s-%.3f)/%.3f)" % (y0, y1 - y0, T, x0, x1 - x0)
        expr = "if(lt(%s,%.3f),%s,%s)" % (T, x1, seg, expr)
    return "pow(10,(%s%+.2f)/20)" % (expr, g)


def mix_filter(t, t0=0.0, length=None, g=0.0):
    """[0:a] the video's audio (voice, sting and card sounds), [1:a] the music. The key that ducks the music is the
    voice only: the sting and the end card are muted in it, so the music's hit lands with the sting's."""
    quiet = []
    if "sting_in" in t:
        quiet.append("between(t+%.3f,%.3f,%.3f)" % (t0, t["sting_in"], t["sting_out"]))
    quiet.append("gte(t+%.3f,%.3f)" % (t0, t["card_start"]))
    fade = ",afade=t=out:st=%.3f:d=1.5" % (length - 1.5) if length else ""
    return ("[0:a]asplit=2[v][k0];[k0]volume=0:enable='%s'[key];"
            "[1:a]aresample=48000,volume='%s':eval=frame,afade=t=in:d=0.4%s[m];"
            "[m][key]sidechaincompress=threshold=0.02:ratio=10:attack=15:release=350[duck];"
            "[v][duck]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.84:level=false[a]"
            % ("+".join(quiet), gain_expr(t, t0, g), fade))


def bed(n, p):
    """cand-N.wav, joined to cand-N-b.wav on a beat when the video needs two edits -> music/bed-N.wav."""
    A = os.path.join(M, "cand-%d.wav" % n)
    if not os.path.isfile(A):
        sys.exit("no music/cand-%d.wav" % n)
    out = os.path.join(M, "bed-%d.wav" % n)
    if len(p["edits"]) == 1:
        shutil.copy(A, out); return out
    Bf = os.path.join(M, "cand-%d-b.wav" % n)
    if not os.path.isfile(Bf):
        sys.exit("the video is %.0f s, longer than one edit: make edit B for candidate %d (music/cand-%d-b.wav) first"
                 % (p["timeline"]["total"], n, n))
    sp, ov = p["edits"][0]["end"], p["edits"][0].get("overlap", 4.0)
    _, ba = beats_of(A); _, bb = beats_of(Bf)
    join = nearest([b for b in ba if b <= sp + ov / 2], sp) or sp               # a beat of A near the split
    first_b = bb[0] if bb else 0.0                                              # B's first beat lands on it
    b_start = max(0.0, first_b)
    xf = 2 * 60.0 / max(beats_of(A)[0] or 120, 1)                               # two beats
    run(["ffmpeg", "-y", "-v", "error", "-i", A, "-ss", "%.3f" % b_start, "-i", Bf, "-filter_complex",
         "[0:a]atrim=0:%.3f,asetpts=N/SR/TB[a];[1:a]asetpts=N/SR/TB[b];[a][b]acrossfade=d=%.3f:c1=tri:c2=tri[o]" % (join + xf / 2, xf),
         "-map", "[o]", out])
    return out


def final_video():
    for f in ("%s-full-4k.mp4" % NAME, "%s-4k.mp4" % NAME):
        if os.path.isfile(os.path.join(W, f)):
            return os.path.join(W, f)
    return None


def window_video(p):
    """The sample window on the published clock at 1080p, with the voice: cut from the finished video when it exists,
    else built from the composition (rendered in a copy, so the 4K render beside it isn't disturbed) and the sting."""
    out = os.path.join(M, "window.mp4")
    if os.path.isfile(out):
        return out
    ws, we = p["window"]; t = p["timeline"]
    fv = final_video()
    if fv:
        run(["ffmpeg", "-y", "-v", "error", "-ss", "%.3f" % ws, "-i", fv, "-t", "%.3f" % (we - ws), "-vf", "scale=-2:1080",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-c:a", "aac", "-b:a", "192k", out])
        return out
    src = os.path.join(M, "window-src"); shutil.rmtree(src, ignore_errors=True); os.makedirs(src)
    for f in os.listdir(os.path.join(W, "public")):
        if f != ".hyperframes":
            os.symlink(os.path.join(W, "public", f), os.path.join(src, f))
    parts, k = [], 0

    def comp(s, e):
        nonlocal k
        if e - s < 0.05:
            return
        o = os.path.join(M, "w%d.mp4" % k); k += 1
        r = run(["npx", "--yes", "hyperframes", "render", src, "--start", "%.3f" % s, "--end", "%.3f" % e, "--quality", "draft",
                 "--workers", "1", "-o", o], quiet=False)
        if r.returncode != 0 or not os.path.isfile(o):
            sys.exit("the sample window's render failed (%.1f-%.1f s)" % (s, e))
        parts.append(o)
    if "sting_in" in t and ws < t["sting_out"] and we > t["sting_in"]:
        comp(ws, min(we, t["sting_in"]))
        intro = os.path.join(W, "bookends", "intro-preview.mp4")
        if not os.path.isfile(intro):
            run(["python3", os.path.join(SK, "scripts", "bookends.py"), "--project", W, "--preview"], quiet=False)
        if not os.path.isfile(intro):
            sys.exit("no sting preview (bookends.py --preview)")
        parts.append(intro)
        comp(t["resume"], t["resume"] + (we - t["sting_out"]))
    else:
        base = t.get("resume", 0) - t.get("sting_out", 0) if ws >= t.get("sting_out", 1e9) else 0.0
        comp(ws + base, we + base)
    lst = os.path.join(M, "window.txt")
    open(lst, "w").write("".join("file '%s'\n" % x for x in parts))
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst, "-vf", "scale=1920:1080,fps=30",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", out])
    if not os.path.isfile(out):
        sys.exit("the sample window couldn't be joined")
    return out


# ---- commands -----------------------------------------------------------------------------------------------------
if a.cmd == "plan":
    p = plan(); t = p["timeline"]
    print("music plan for %s (%s): %.1f s published%s; end card from %.1f s" % (NAME, PROFILE, t["total"],
          ", the sting %.2f-%.2f s with its hit at %.2f s" % (t["sting_in"], t["sting_out"], t["hit"]) if "hit" in t else "", t["card_start"]))
    print("sample window: %.1f-%.1f s; Epidemic edits: %s" % (p["window"][0], p["window"][1],
          ", ".join("%s %.1f-%.1f s" % (e["edit"], e["start"], e["end"]) for e in p["edits"])))
    if not p["pass"]:
        print("the %s profile has the music pass off (music.json)" % PROFILE)
    sys.exit(0)

p = load(os.path.join(M, "plan.json")) or plan()
t = p["timeline"]

if a.cmd == "analyze":
    if not a.track or not os.path.isfile(a.track):
        sys.exit("--track FILE (the track's preview or full download)")
    bpm, beats, ds = drops(a.track)
    if not beats:
        sys.exit("no beats found in %s" % a.track)
    out = {"bpm": bpm, "beats": len(beats), "length": round(dur(a.track), 2), "drops": ds}
    e = next(x for x in p["edits"] if x["edit"] == a.edit)
    length = e["end"] - e["start"] + e.get("overlap", 0.0)
    inp = {"targetDurationMs": int(round(length * 1000)), "downloadAudioFormat": "WAV", "forceDuration": True,
           "skipStems": True, "maxResults": 1}
    if a.edit == "A" and "hit" in t:
        d = a.drop if a.drop is not None else (ds[0]["t"] if ds else None)
        if d is not None:
            bar = 4 * 60.0 / max(bpm, 1)
            pre = min(2 * bar, t["hit"], d)                    # two bars of build-up before the drop
            inp["requiredRegionsAtOffsets"] = [{"startMs": int(round((d - pre) * 1000)), "endMs": int(round((d + 2 * bar) * 1000)),
                                                "offsetMsInEdit": int(round((t["hit"] - pre) * 1000))}]
            out["drop_used"] = d
    out["edit_input"] = inp
    print(json.dumps(out, indent=1))
    sys.exit(0)

if a.cmd == "check":
    f = a.file or sys.exit("--file FILE")
    bpm, beats = beats_of(f)
    L = dur(f)
    res = {"file": os.path.basename(f), "bpm": bpm, "length": round(L, 2), "want": round(t["total"] if "-b" not in f else 0, 2)}
    if "hit" in t and "-b" not in f:
        nb = nearest(beats, t["hit"])
        res["beat_at_hit_ms"] = None if nb is None else int(round((nb - t["hit"]) * 1000))
    print(json.dumps(res))
    sys.exit(0)

if a.cmd == "status":
    ch = load(os.path.join(M, "choice.json"))
    if R.get("music") == "none" or not CFG.get("pass", True):
        print("off")
    elif ch is not None:
        print("none" if not ch.get("pick") else "chosen %d" % ch["pick"])
    else:
        print("pending")
    sys.exit(0)

if a.cmd == "choose":
    if not a.pick or not os.path.isfile(os.path.join(M, "cand-%d.wav" % a.pick)):
        sys.exit("no music/cand-%s.wav" % a.pick)
    if len(p["edits"]) > 1 and not os.path.isfile(os.path.join(M, "cand-%d-b.wav" % a.pick)):
        sys.exit("the video needs two edits: make edit B of candidate %d (music/cand-%d-b.wav) first" % (a.pick, a.pick))
    info = (load(os.path.join(M, "candidates.json"), {}) or {}).get(str(a.pick), {})
    json.dump({"pick": a.pick, "track": info}, open(os.path.join(M, "choice.json"), "w"), indent=1)
    print("music for %s: candidate %d (%s)" % (NAME, a.pick, info.get("title", "?"))); sys.exit(0)

if a.cmd == "none":
    json.dump({"pick": None, "note": "no music"}, open(os.path.join(M, "choice.json"), "w"))
    print("no music for %s" % NAME); sys.exit(0)

if a.cmd == "samples":
    cands = sorted(glob.glob(os.path.join(M, "cand-[0-9].wav")) + glob.glob(os.path.join(M, "cand-[0-9][0-9].wav")))
    if not cands:
        sys.exit("no music/cand-N.wav yet")
    info = load(os.path.join(M, "candidates.json"), {}) or {}
    wv = window_video(p)
    ws, we = p["window"]
    sd = os.path.join(M, "samples"); os.makedirs(sd, exist_ok=True)
    rows = []
    for c in cands:
        n = int(re.search(r"cand-(\d+)\.wav$", c).group(1))
        o = os.path.join(sd, "%d.mp4" % n)
        r = run(["ffmpeg", "-y", "-v", "error", "-i", wv, "-ss", "%.3f" % ws, "-t", "%.3f" % (we - ws), "-i", c,
                 "-filter_complex", mix_filter(t, ws, g=norm_db(c)), "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                 "-movflags", "+faststart", o])
        if r.returncode != 0:
            print("sample %d failed: %s" % (n, r.stderr.strip()[-300:])); continue
        bpm, beats = beats_of(c)
        nb = nearest(beats, t["hit"]) if "hit" in t else None
        meta = info.get(str(n), {})
        rows.append({"n": n, "file": "samples/%d.mp4" % n, "title": meta.get("title", "Candidate %d" % n),
                     "artist": meta.get("artist", ""), "bpm": meta.get("bpm") or bpm, "why": meta.get("why", ""),
                     "hit_ms": None if nb is None else int(round((nb - t["hit"]) * 1000))})
        print("sample %d: %s (%s), beat at the hit %s ms" % (n, rows[-1]["title"], rows[-1]["bpm"], rows[-1]["hit_ms"]))
    hit_in = t["hit"] - ws if "hit" in t else None
    cards = "".join(
        '<figure><video controls preload="metadata" src="music/%s"></video><figcaption><b>%d. %s</b>%s<br>%s BPM%s<br><i>%s</i>'
        '</figcaption></figure>' % (r["file"], r["n"], html.escape(r["title"]), (" · " + html.escape(r["artist"])) if r["artist"] else "",
                                    r["bpm"], (" · the beat lands %+d ms from the sting's hit" % r["hit_ms"]) if r["hit_ms"] is not None else "",
                                    html.escape(r["why"])) for r in rows)
    page = """<!doctype html><meta charset="utf-8"><title>Music for %s</title>
<style>body{font:15px -apple-system,system-ui,sans-serif;background:#111;color:#eee;margin:32px}
main{display:grid;grid-template-columns:repeat(auto-fill,minmax(440px,1fr));gap:24px}figure{margin:0}
video{width:100%%;border-radius:8px;background:#000}figcaption{margin-top:8px;line-height:1.5}i{color:#aaa}
code{background:#222;padding:2px 6px;border-radius:4px}</style>
<h1>Music for %s</h1><p>The same 30 s (%.1f-%.1f s of the published video)%s under each track. Pick one in a Claude
thread on this Mac: <code>music 3 for %s</code>, or <code>no music for %s</code>.</p><main>%s</main>""" % (
        html.escape(NAME), html.escape(NAME), ws, we,
        ", the sting's hit at %.1f s into each clip" % hit_in if hit_in is not None else "", NAME, NAME, cards)
    open(os.path.join(W, "MUSIC-REVIEW.html"), "w").write(page)
    json.dump(rows, open(os.path.join(M, "samples.json"), "w"), indent=1)
    print("MUSIC-REVIEW.html: %d samples" % len(rows))
    sys.exit(0 if rows else 1)

if a.cmd == "mix":
    if not a.pick:
        sys.exit("--pick N")
    fv = final_video() or sys.exit("no finished video yet (%s-full-4k.mp4 / %s-4k.mp4); the render's music step mixes it" % (NAME, NAME))
    b = bed(a.pick, p)
    L = dur(fv)
    if abs(dur(b) - L) > 1.0:
        print("note: the bed is %.1f s, the video %.1f s; it is cut or ends early" % (dur(b), L))
    out = fv[:-4] + "-music.mp4"
    r = run(["ffmpeg", "-y", "-v", "error", "-i", fv, "-i", b, "-filter_complex", mix_filter(t, 0.0, min(L, dur(b)), g=norm_db(b)),
             "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", out])
    if r.returncode != 0 or not os.path.isfile(out):
        sys.exit("the mix failed: " + r.stderr.strip()[-400:])
    lufs = run(["ffmpeg", "-nostats", "-i", out, "-map", "0:a", "-af", "ebur128=peak=true", "-f", "null", "-"]).stderr
    I = re.findall(r"I:\s+(-?[0-9.]+) LUFS", lufs); P = re.findall(r"Peak:\s+(-?[0-9.]+) dBFS", lufs)
    ok_len = abs(dur(out) - L) < 0.1
    info = (load(os.path.join(M, "candidates.json"), {}) or {}).get(str(a.pick), {})
    json.dump({"pick": a.pick, "track": info, "file": os.path.basename(out)}, open(os.path.join(M, "choice.json"), "w"), indent=1)
    open(os.path.join(W, "MUSIC.md"), "w").write(
        "# Music: %s\n\n- Track: %s%s (Epidemic Sound%s)\n- Timing: edit A puts the track's drop on the sting's hit at %s;"
        " %s\n- Levels: %s dB under the hook, %s dB under the body, %s dB on the end card, ducked under the voice"
        " (the sting and end card don't duck it), -1 dB limiter\n- Files: `%s` (with music), `%s` (no music)\n"
        "- Loudness: %s LUFS integrated, true peak %s dBFS\n" % (
            NAME, info.get("title", "candidate %d" % a.pick), (" · " + info["artist"]) if info.get("artist") else "",
            (", id " + info["id"]) if info.get("id") else "", "%.2f s" % t["hit"] if "hit" in t else "-",
            "edit B continues it from %.1f s, joined on a beat" % p["edits"][1]["start"] if len(p["edits"]) > 1 else "one edit to the end",
            CFG["hook_db"], CFG["body_db"], CFG["card_db"], os.path.basename(out), os.path.basename(fv),
            I[-1] if I else "?", P[-1] if P else "?"))
    print("music: %s (%.1f s%s), %s LUFS, peak %s dBFS" % (out, dur(out), "" if ok_len else ", LENGTH DIFFERS", I[-1] if I else "?", P[-1] if P else "?"))
    sys.exit(0 if ok_len else 1)
