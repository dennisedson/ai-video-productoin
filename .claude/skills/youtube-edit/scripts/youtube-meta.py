#!/usr/bin/env python3
"""youtube-meta.py: the exact half of a video's YouTube metadata (no AI). The writing half is metadata.json, which the
pipeline's youtube stage (pipeline/prompts/youtube.md) writes; this script times it, links it, checks it and lays it
out for YouTube Studio.

  python3 youtube-meta.py prep  --project videos/NAME      final timeline + captions.srt, before metadata.json exists
  python3 youtube-meta.py build --project videos/NAME      metadata.json + links.tsv -> YOUTUBE.md, captions, catalog
  python3 youtube-meta.py check --project videos/NAME --video FILE.mp4   the times against the rendered video

Everything lands in videos/NAME/youtube/:
  timeline.json   how a time on the flat cut (the transcript's clock) maps onto the published video: the intro sting is
                  cut in at bookends.intro.at and the video resumes at .resume, the end card follows the video
  captions.srt    the transcript as captions on the published video's clock, with metadata.json's caption_fixes applied
  links.tsv       every tracked link: the full UTM URL to shorten and a Bitly column you fill in; a filled Bitly link
                  replaces the long one in YOUTUBE.md on the next build (`yt youtube NAME`)
  YOUTUBE.md      title options, description, chapters, cards, end screen, tags, pinned comment, checks, in Studio order
The build also writes this video's entry in catalog/VIDEOS.md (between its own markers; the rest is left alone).

YouTube's rules checked here: title <= 100 characters (about 70 show in search); description <= 5,000 characters, the
first ~157 shown above the fold; chapters start at 00:00, at least three, ascending, each >= 10 s; at most 5 cards, none
in the end screen; end screen 5-20 s at the end of a video >= 25 s long, at most 4 elements, one a video or playlist;
tags <= 500 characters; 3 hashtags (the first three in the description show above the title).
"""
import argparse, csv, datetime as dt, json, os, re, subprocess, sys
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

SK = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
ROOT = os.path.abspath(os.path.join(SK, "..", "..", ".."))
ap = argparse.ArgumentParser()
ap.add_argument("cmd", choices=["prep", "build", "check", "published"])
ap.add_argument("--url", help="published: the video's YouTube link")
ap.add_argument("--project", required=True)
ap.add_argument("--video", help="check: the rendered video")
a = ap.parse_args()
W = os.path.abspath(a.project.rstrip("/"))
NAME = os.path.basename(W)
Y = os.path.join(W, "youtube")
os.makedirs(Y, exist_ok=True)


def load(path, default=None):
    try:
        return json.load(open(path))
    except (OSError, ValueError):
        return default


def ffdur(path):
    try:
        return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                                    capture_output=True, text=True).stdout.strip())
    except (OSError, ValueError):
        return None


# ---- the published video's clock ---------------------------------------------------------------------------------
def template_duration(profile, kind):
    p = os.path.join(SK, "profiles", profile, kind, "index.html")
    try:
        m = re.search(r'data-duration="([0-9.]+)"', open(p).read())
        return float(m.group(1)) if m else None
    except OSError:
        return None


def timeline():
    render = load(os.path.join(W, "render.json"), {}) or {}
    story = load(os.path.join(W, "storyboard.json"), {}) or {}
    source = load(os.path.join(Y, "source.json"), {}) or {}          # a metadata-only video: the finished file
    profile = story.get("profile") or source.get("profile") or "hubspot"
    words = load(os.path.join(W, "transcript.json"), []) or []
    main = None
    for f in ([source["video"]] if source.get("video") else []) + ["public/input-video.mp4", "%s-4k.mp4" % render.get("name", NAME), "output-4k.mp4"]:
        if os.path.isfile(os.path.join(W, f)):
            main = ffdur(os.path.join(W, f)); break
    if not main:
        cl = load(os.path.join(W, "cut-list.json"), {}) or {}
        main = cl.get("kept_seconds") or (words[-1]["end"] if words else None)
    if not main:
        sys.exit("can't tell the flat cut's length (no input-video, cut-list.json or transcript.json)")
    B = render.get("bookends") or {}
    t = {"main": round(main, 3), "intro": None, "outro": None, "profile": profile}
    if B.get("intro"):
        at = float(B["intro"]["at"]); resume = float(B["intro"].get("resume", at))
        t["intro"] = {"at": at, "resume": resume, "dur": template_duration(profile, "intro") or 3.0}
    body_end = map_t(t, main)
    if B.get("outro"):
        t["outro"] = {"start": round(body_end, 3), "dur": template_duration(profile, "outro") or 15.0}
    t["total"] = round(body_end + (t["outro"]["dur"] if t["outro"] else 0), 3)
    return t


def map_t(t, x):
    """A time on the flat cut -> the published video. Times inside the trimmed pause land at the sting's end."""
    i = t.get("intro")
    if not i or x <= i["at"]:
        return x
    return i["at"] + i["dur"] + max(0.0, x - i["resume"])


def stamp(s, total):
    s = int(round(s))
    return "%d:%02d:%02d" % (s // 3600, s % 3600 // 60, s % 60) if total >= 3600 else "%02d:%02d" % (s // 60, s % 60)


# ---- captions -----------------------------------------------------------------------------------------------------
def fix_text(text, fixes):
    for wrong, right in fixes:
        text = re.sub(r"(?<![\w'])%s(?![\w'])" % re.escape(wrong), right, text)
    return text


def captions(t, fixes):
    words = load(os.path.join(W, "transcript.json"), []) or []
    cues, cur = [], []
    for w in words:
        if cur and (w["start"] - cur[-1]["end"] > 0.6 or w["end"] - cur[0]["start"] > 6.0
                    or len(" ".join(x["text"] for x in cur + [w])) > 84
                    or (t["intro"] and cur[0]["start"] < t["intro"]["at"] - 0.05 and w["start"] >= t["intro"]["at"] - 0.05)):
            cues.append(cur); cur = []
        cur.append(w)
        if w["text"].endswith((".", "?", "!")) and len(" ".join(x["text"] for x in cur)) > 30:
            cues.append(cur); cur = []
    if cur:
        cues.append(cur)

    def ts(x):
        ms = int(round(x * 1000))
        return "%02d:%02d:%02d,%03d" % (ms // 3600000, ms % 3600000 // 60000, ms % 60000 // 1000, ms % 1000)

    def two_lines(text):
        if len(text) <= 42:
            return text
        mid, best = len(text) // 2, None
        for m in re.finditer(" ", text):
            if best is None or abs(m.start() - mid) < abs(best - mid):
                best = m.start()
        return text[:best] + "\n" + text[best + 1:]

    out = []
    for n, c in enumerate(cues, 1):
        a0, a1 = map_t(t, c[0]["start"]), map_t(t, c[-1]["end"])
        if t["intro"] and c[0]["start"] < t["intro"]["at"]:      # a cue before the sting ends where the sting starts
            a1 = min(a1, t["intro"]["at"])
        text = fix_text(" ".join(x["text"] for x in c), fixes)
        out.append("%d\n%s --> %s\n%s\n" % (n, ts(a0), ts(max(a1, a0 + 0.5)), two_lines(text)))
    open(os.path.join(Y, "captions.srt"), "w").write("\n".join(out))
    return len(out)


# ---- links ---------------------------------------------------------------------------------------------------------
def youtube_url(u):
    return urlsplit(u).netloc.lower().endswith(("youtube.com", "youtu.be"))


def utm(url, campaign, content, cfg):
    parts = urlsplit(url)
    q = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if not k.startswith("utm_")]
    q += [("utm_source", cfg.get("source", "youtube")), ("utm_medium", cfg.get("medium", "video")),
          ("utm_campaign", campaign), ("utm_content", content)]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(q), parts.fragment))


def link_rows(meta, ycfg):
    """[{id, label, placement, url, long, bitly, back_half}] for each external link and placement; Bitly kept from links.tsv."""
    old = {}
    p = os.path.join(Y, "links.tsv")
    if os.path.isfile(p):
        for r in csv.DictReader(open(p), delimiter="\t"):
            if (r.get("bitly") or "").strip():
                old[r["key"]] = r["bitly"].strip()
    campaign = meta.get("campaign") or ycfg.get("campaign") or NAME
    rows = []
    for L in meta.get("links", []):
        for pl in L.get("placements", ["desc"]):
            key = "%s:%s" % (L["id"], pl)
            if youtube_url(L["url"]):
                rows.append({"key": key, "id": L["id"], "placement": pl, "label": L.get("label", ""), "url": L["url"],
                             "long": L["url"], "bitly": "", "back_half": ""}); continue
            content = "%s_%s_%s" % (NAME, pl, L["id"])
            rows.append({"key": key, "id": L["id"], "placement": pl, "label": L.get("label", ""), "url": L["url"],
                         "long": utm(L["url"], campaign, content, ycfg.get("utm", {})), "bitly": old.get(key, ""),
                         "back_half": ("%s-%s%s" % (NAME, L["id"], "" if pl == "desc" else "-" + pl))[:50]})
    with open(p, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["key", "label", "back_half", "bitly", "long"], delimiter="\t", extrasaction="ignore")
        w.writeheader()
        for r in rows:
            if not youtube_url(r["url"]):
                w.writerow(r)
    return rows


def link_for(rows, lid, placement):
    for r in rows:
        if r["id"] == lid and r["placement"] == placement:
            return r["bitly"] or r["long"]
    for r in rows:                                          # the link exists but not for this placement: its desc one
        if r["id"] == lid:
            return r["bitly"] or r["long"]
    return None


def fill(text, rows, placement, problems):
    def sub(m):
        u = link_for(rows, m.group(1), placement)
        if not u:
            problems.append("{link:%s} has no link with that id" % m.group(1)); return m.group(0)
        return u
    return re.sub(r"\{link:([\w-]+)\}", sub, text)


# ---- catalog -------------------------------------------------------------------------------------------------------
def catalog_entry(meta, t, rows):
    c = meta.get("catalog", {})
    old = open(CAT).read() if os.path.isfile(CAT) else ""
    m = re.search(r"<!-- video:%s -->(.*?)<!-- /video:%s -->" % (re.escape(NAME), re.escape(NAME)), old, re.S)
    keep = {}
    if m:                                                   # what `yt published` set survives a rebuild
        for k in ("YouTube", "Published", "Status"):
            mm = re.search(r"^- \*\*%s:\*\* (.*)$" % k, m.group(1), re.M)
            if mm:
                keep[k] = mm.group(1)
    title = (meta.get("chosen_title") or (meta.get("titles") or [{}])[0].get("title") or NAME)
    lines = ["<!-- video:%s -->" % NAME, "### %s" % title, "",
             "- **Slug:** `%s` · **Channel:** %s · **Series:** %s" % (NAME, c.get("channel", "HubSpot Developers"), c.get("series", "-")),
             "- **Status:** %s" % keep.get("Status", "drafted, not published"),
             "- **YouTube:** %s" % keep.get("YouTube", "(not published yet)"),
             "- **Published:** %s" % keep.get("Published", "-"),
             "- **Length:** %s" % stamp(t["total"], t["total"]),
             "- **Summary:** %s" % c.get("summary", meta.get("description", {}).get("opening", "")),
             "- **Audience:** %s" % meta.get("audience", "-"),
             "- **Topics:** %s" % ", ".join(c.get("topics", [])),
             "- **Questions it answers:** %s" % " · ".join(meta.get("description", {}).get("learn", [])),
             "- **Chapters:** %s" % " · ".join("%s %s" % (stamp(map_t(t, float(ch["t"])), t["total"]), ch["title"]) for ch in meta.get("chapters", [])),
             "- **Links used:** %s" % ", ".join(sorted({"[%s](%s)" % (r["label"] or r["id"], r["url"]) for r in rows})),
             "- **Related:** %s" % (", ".join(c.get("related", [])) or "-"),
             "<!-- /video:%s -->" % NAME]
    block = "\n".join(lines)
    if m:
        new = old[:m.start()] + block + old[m.end():]
    else:
        head = old if old.strip() else "# Video catalog\n\nOne entry per video: what it covers, where it lives, what it links to. Written by `yt youtube`\n(youtube-meta.py build) between each video's markers; `yt published NAME URL` fills in the link and date.\n"
        new = head.rstrip() + "\n\n" + block + "\n"
    open(CAT, "w").write(new)


CAT = os.path.join(ROOT, "catalog", "VIDEOS.md")


# ---- published: the link and date into the catalog -----------------------------------------------------------------
if a.cmd == "published":
    old = open(CAT).read() if os.path.isfile(CAT) else ""
    m = re.search(r"<!-- video:%s -->(.*?)<!-- /video:%s -->" % (re.escape(NAME), re.escape(NAME)), old, re.S)
    if not m:
        sys.exit("no catalog entry for %s yet (yt youtube %s writes it)" % (NAME, NAME))
    body = m.group(1)
    for k, v in (("Status", "published"), ("YouTube", a.url), ("Published", dt.date.today().isoformat())):
        body = re.sub(r"^- \*\*%s:\*\* .*$" % k, "- **%s:** %s" % (k, v), body, flags=re.M)
    open(CAT, "w").write(old[:m.start(1)] + body + old[m.end(1):])
    print("catalog: %s published at %s" % (NAME, a.url))
    sys.exit(0)

# ---- prep ----------------------------------------------------------------------------------------------------------
t = timeline()
meta = load(os.path.join(Y, "metadata.json"))
if a.cmd == "prep":
    json.dump(t, open(os.path.join(Y, "timeline.json"), "w"), indent=1)
    n = captions(t, [])
    print("timeline: flat cut %.1f s -> published %.1f s (%s)" % (t["main"], t["total"],
          "sting at %.1f s, +%.1f s after it" % (t["intro"]["at"], t["intro"]["dur"] - (t["intro"]["resume"] - t["intro"]["at"])) if t["intro"] else "no sting"))
    print("captions.srt: %d cues (before caption fixes)" % n)
    sys.exit(0)

if a.cmd == "check":
    d = ffdur(a.video) if a.video else None
    if d is None:
        sys.exit("can't read %s" % a.video)
    off = d - t["total"]
    print("rendered %.2f s vs expected %.2f s (%+.2f s)" % (d, t["total"], off))
    sys.exit(0 if abs(off) <= 0.5 else 1)

# ---- build ---------------------------------------------------------------------------------------------------------
if not meta:
    sys.exit("no youtube/metadata.json yet (the youtube stage writes it: yt run %s youtube)" % NAME)
json.dump(t, open(os.path.join(Y, "timeline.json"), "w"), indent=1)
ycfg = load(os.path.join(SK, "profiles", t["profile"], "youtube.json"), {}) or {}
problems, notes = [], []
rows = link_rows(meta, ycfg)
ncues = captions(t, meta.get("caption_fixes", []))
total = t["total"]

# chapters
chap = sorted(({"at": map_t(t, float(c["t"])), "title": c["title"].strip()} for c in meta.get("chapters", [])), key=lambda c: c["at"])
if chap:
    chap[0]["at"] = 0.0 if chap[0]["at"] < 1.0 else chap[0]["at"]
    if chap[0]["at"] != 0.0:
        problems.append("the first chapter must start at 00:00")
    if len(chap) < 3:
        problems.append("YouTube needs at least three chapters (has %d)" % len(chap))
    for c, n in zip(chap, chap[1:] + [{"at": total}]):
        if n["at"] - c["at"] < 10:
            problems.append("chapter \"%s\" is %.1f s; each must be at least 10 s" % (c["title"], n["at"] - c["at"]))
chapters_txt = "\n".join("%s %s" % (stamp(c["at"], total), c["title"]) for c in chap)

# titles
titles = meta.get("titles", [])
for tt in titles:
    if len(tt["title"]) > 100:
        problems.append("title over 100 characters: %s" % tt["title"])

# description
D = meta.get("description", {})
parts = [D.get("opening", "").strip()]
cta = [r for r in rows if r["placement"] == "desc"]
if cta:
    parts.append("\n".join("▶ %s: %s" % (r["label"], r["bitly"] or r["long"]) for r in cta))
if D.get("learn"):
    parts.append("In this video:\n" + "\n".join("• %s" % q for q in D["learn"]))
if chapters_txt:
    parts.append("Chapters:\n" + chapters_txt)
if D.get("terms"):
    parts.append("Key terms:\n" + "\n".join("• %s: %s" % (x["term"], x["definition"]) for x in D["terms"]))
for extra in D.get("extra", []):
    parts.append(extra.strip())
if meta.get("hashtags"):
    parts.append(" ".join(meta["hashtags"][:3]))
desc = fill("\n\n".join(p for p in parts if p), rows, "desc", problems)
desc_short = desc
for r in rows:                                               # the same description once every link is shortened
    if not r["bitly"] and not youtube_url(r["url"]):
        desc_short = desc_short.replace(r["long"], "https://bit.ly/xxxxxxx")
if len(desc) > 5000:
    (problems if len(desc_short) > 5000 else notes).append(
        "description is %d characters with long links (%d once shortened); the limit is 5,000" % (len(desc), len(desc_short)))
kw = (meta.get("primary_keyword") or "").lower()
if kw and kw not in desc[:157].lower():
    notes.append("the primary keyword \"%s\" isn't in the first 157 characters of the description" % meta["primary_keyword"])
if len(meta.get("hashtags", [])) != 3:
    notes.append("use exactly three hashtags (has %d)" % len(meta.get("hashtags", [])))

# tags
tags = meta.get("tags", [])
tags_len = sum(len(x) + (2 if " " in x else 0) for x in tags) + max(len(tags) - 1, 0)
if tags_len > 500:
    problems.append("tags are %d characters; the limit is 500" % tags_len)

# cards
cards = sorted(({"at": map_t(t, float(c["t"])), **c} for c in meta.get("cards", [])), key=lambda c: c["at"])
if len(cards) > 5:
    problems.append("%d cards; YouTube allows 5" % len(cards))
es_start = t["outro"]["start"] if t["outro"] else total - 20
for c in cards:
    if c["at"] >= es_start - 1:
        problems.append("card at %s falls in the end screen, where cards are hidden" % stamp(c["at"], total))

# end screen
es = meta.get("end_screen", [])
if total < 25:
    problems.append("the video is under 25 s: no end screen")
if len(es) > 4:
    problems.append("%d end screen elements; the limit is 4" % len(es))
if es and not any(e.get("type") in ("video", "playlist") for e in es):
    problems.append("the end screen needs a video or playlist element")
es_len = min(20.0, total - es_start)

pinned = fill(meta.get("pinned_comment", ""), rows, "pinned", problems)

# ---- YOUTUBE.md ----
SRCV = (load(os.path.join(Y, "source.json"), {}) or {}).get("video")
L = ["# YouTube: %s" % NAME, "",
     "Published length %s (%s %.1f s%s). Built %s from `youtube/metadata.json`; rebuild with `yt youtube %s` after"
     " filling Bitly links in `youtube/links.tsv`." % (stamp(total, total), "the finished video %s," % SRCV if SRCV else "flat cut", t["main"],
         ", sting at %s" % stamp(t["intro"]["at"], total) if t["intro"] else "", dt.datetime.now().strftime("%Y-%m-%d %H:%M"), NAME), ""]
if problems or notes or meta.get("for_dennis"):
    L += ["## Check before publishing", ""]
    L += ["- **Fix:** %s" % p for p in problems] + ["- %s" % n for n in notes] + ["- **For you:** %s" % x for x in meta.get("for_dennis", [])] + [""]
L += ["## Title", "", "Pick one (≤ 100 characters; about 70 show in search):", ""]
for n, tt in enumerate(titles, 1):
    L.append("%d. **%s** (%d)%s" % (n, tt["title"], len(tt["title"]), " · " + tt["why"] if tt.get("why") else ""))
L += ["", "## Description", "", "%d characters with these links (limit 5,000; the first ~157 show above the fold)." % len(desc), "",
      "```", desc, "```", ""]
L += ["## Links to shorten", "",
      "Shorten each long link in Bitly with the suggested back-half, paste the short link into the `bitly` column of"
      " `youtube/links.tsv`, then `yt youtube %s` puts them in the description and the pinned comment." % NAME, "",
      "| Link | Where | Suggested back-half | Bitly | Long link (with UTM) |", "| --- | --- | --- | --- | --- |"]
for r in rows:
    if not youtube_url(r["url"]):
        L.append("| %s | %s | `%s` | %s | `%s` |" % (r["label"], r["placement"], r["back_half"], r["bitly"] or "-", r["long"]))
L += ["", "## Chapters", "", "Already in the description; YouTube builds them from it (first at 00:00, at least three, each ≥ 10 s).", "",
      "```", chapters_txt, "```", ""]
L += ["## Cards (suggested videos at timestamps)", "", "Studio → Editor → Cards. At most 5; hidden while the end screen shows.", ""]
if cards:
    L += ["| At | Card | Teaser | Why here |", "| --- | --- | --- | --- |"]
    for c in cards:
        L.append("| %s | %s | %s | %s |" % (stamp(c["at"], total), c.get("target", ""), c.get("teaser", ""), c.get("why", "")))
else:
    L.append("None suggested.")
L += ["", "## End screen", "",
      "Studio → Editor → End screen, from %s to the end (%.0f s)%s." % (stamp(es_start, total), es_len,
          "; the end card leaves an outlined box for the video element and a circle for subscribe" if t["outro"] else ""), ""]
for e in es:
    L.append("- **%s**%s%s" % (e.get("type", "?").capitalize(), ": " + e["target"] if e.get("target") else "", " · " + e["label"] if e.get("label") else ""))
L += ["", "## Tags", "", "%d characters (limit 500):" % tags_len, "", "```", ", ".join(tags), "```", ""]
L += ["## Pinned comment", "", "```", pinned, "```", ""]
L += ["## Captions", "", "Upload `youtube/captions.srt` (Studio → Subtitles → Add → Upload file → With timing): %d cues on the"
      " published video's clock%s. Your own captions replace YouTube's automatic ones, and AI search reads them." % (
          ncues, ", with %d correction%s" % (len(meta.get("caption_fixes", [])), "" if len(meta.get("caption_fixes", [])) == 1 else "s") if meta.get("caption_fixes") else ""), ""]
open(os.path.join(Y, "YOUTUBE.md"), "w").write("\n".join(L))
os.makedirs(os.path.dirname(CAT), exist_ok=True)
catalog_entry(meta, t, rows)
print("YOUTUBE.md: %d title options, %d chapters, %d cards, %d end screen elements, %d links to shorten; %d problems"
      % (len(titles), len(chap), len(cards), len(es), sum(1 for r in rows if not youtube_url(r["url"])), len(problems)))
for p in problems:
    print("  fix: " + p)
sys.exit(1 if problems else 0)
