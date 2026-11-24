# Video studio: one project per video, followed in a local web app

Date: 2026-11-24. Status: approved by Dennis ("build away").

## Why

The first test (retros/2026-11-agentcli.md) showed that time and money went to four things: inputs that arrived late
(enhanced audio, b-roll, links, whose face), notes rounds run by hand in one long chat thread (two thirds of the work
Mac's AI bill), reviews where screenshots were hard to refer to, and packaging done after the fact. Dennis also wants
the whole life of a video in one place, from the idea to the results, and the web app to be the only window he needs.

## Shape

- **The repo is the overarching project** (CLAUDE.md and the skill hold the shared rules). **Each video is its own
  folder and its own Claude session**: the app's chat panel runs Claude in that video's context only, so no thread
  carries several videos.
- **`yt new [name]`** scaffolds a video. Without a name it asks for one (in a terminal it prompts; in a Claude thread
  Claude asks first). The app has the same as a "New video" form.
- **The studio**: `yt app` serves a page on `http://127.0.0.1:4040` (launchd keeps it running). It reads and writes
  the video folders and starts `yt` commands and Claude runs. Python standard library only, plain HTML/CSS/JS, no
  build step and no npm, so it runs on both Macs after `git pull`.
- The work Mac is where everything happens. The home Mac runs the same app for its two jobs: renders and the music
  pick (Epidemic Sound is only connected there).

## The video project

```
videos/<name>/
  video.json          {"name", "title", "origin": colleague|problem|feature|finished, "series", "profile",
                       "presenter", "phase", "phases": {<id>: {"done": [step ids], "approved": date}},
                       "chat_session", "created", "results": {...}}
  BRIEF.md            viewer, promise, demo, links (the end of ideation)
  research.md         notes and sources
  references.md       every outside link: label, URL, where it's used, status (live / scheduled / 404), checked
  SCRIPT.md           the script Dennis edits (format below)
  teleprompter.txt    generated: only the read-aloud parts, short lines, demo markers
  recording-sheet.md  generated: the outline, then every copy-paste item in order
  questions.json      open questions from Claude runs and Dennis's answers
  review/comments-<A|B|package>.json   review comments (time, frame image, box, text)
  raw/                recordings
  ... everything the pipeline writes today (state.json, cut, storyboard, youtube/)
```

### Phases (pipeline/studio/phases.json)

Each phase has steps (title, instructions, optional template, optional "done when" file check), the documents it
shows, and its request forms. Every phase's forms end with a free-form request.

| # | Phase | Output | Moves on when |
| --- | --- | --- | --- |
| 1 | Ideation | BRIEF.md from the origin's template (colleague: their material and links; problem: research; feature: changelog and docs) | Dennis approves the brief |
| 2 | Script and direction | SCRIPT.md, then teleprompter.txt and recording-sheet.md generated | Dennis approves the script |
| 3 | Recording | the recording checklist; files in raw/ | "Start the cut" (or files dropped through the inbox under the same name) |
| 4 | Cut (Checkpoint A) | as today | approve in the review |
| 5 | Storyboard (Checkpoint B) | as today | approve in the review |
| 6 | Render and music (home Mac) | as today; the work Mac shows the hand-off steps | `yt import` |
| 7 | Packaging | titles, description, thumbnail, links, captions | Dennis picks a title and a thumbnail |
| 8 | Publish | upload checklist, `yt published [--scheduled]`, `yt drive` | published |
| 9 | Results | metrics after two weeks; what to learn for the voice file | Dennis closes it |

The phase is derived: from state.json for phases 4 to 6 (cutting/awaiting-A = 4, storyboarding/awaiting-B = 5,
rendering/awaiting-import = 6, done = 7), from video.json otherwise. A finished video (origin "finished") starts at 7.

### SCRIPT.md format

```
## Hook
> Read-aloud lines go in blockquotes.
→ demo: log in with the CLI
```copy: Log in
hubspot auth login
```
```

`script-sheets.py` turns it into teleprompter.txt (blockquote text wrapped to about 32 characters, `→ DEMO: ...`
markers, section breaks) and recording-sheet.md (section headings with their demo beats, then the copy blocks
numbered in order). The copy blocks' URLs go into references.md.

### Voice

`profiles/<profile>/VOICE.md` holds how Dennis talks (openers, sign-offs, phrases, what he never says, such as claims
that aren't true). The script forms read it. A Results-phase request compares SCRIPT.md with the finished
transcript and proposes VOICE.md changes for Dennis to accept.

## The app

Three views:

1. **Board**: every video as a card in its phase column, with what it waits on (Dennis, a stage, the home Mac) and a
   badge for open questions. A "New video" form.
2. **Video page**: phases down the left; the current phase on the right with its steps (instructions, template,
   done box), its documents (an editor with a live preview, saving to the file), its request forms, the video's open
   questions, and a chat panel at the side. Actions (start a stage, `yt thumb`, `yt drive`, ...) are buttons whose
   log streams into the page.
3. **Review** (Checkpoint A, Checkpoint B, packaging): the video player and stills; press C to comment at the current
   moment (the frame is captured), draw a box on the frame or a still, drag a still into a comment; comments sit on
   the timeline and jump the player when clicked; "Send notes" hands the list to Claude as structured notes. Approve
   and the open questions are on the same page. Packaging review has the title and thumbnail picks as buttons.

### Talking to Claude

- **Forms**: a request is a prompt template (pipeline/studio/prompts/<form>.md) filled with the form's fields and
  run as one `claude -p` in the repo with the video's folder named, on Sonnet by default (`STUDIO_MODEL`), with the
  config's budget cap.
- **Chat**: one session per video. The first message starts `claude -p --session-id <uuid>`, later ones
  `--resume <uuid>`; replies stream to the page. The session id lives in video.json.
- **Questions**: a Claude run that needs Dennis writes to questions.json (`{"id", "from", "text", "options"?,
  "answer"?, "asked", "answered"}`) with `yt ask NAME "question" [--options "a|b"]`; the app shows them and saves
  answers; the next run on that video reads answered questions. The checkpoint prompts are told to ask this way
  instead of only listing open questions in their write-up.
- Every run is a job: `videos/<name>/studio/jobs/<id>.json` (what, started, finished, exit, cost if reported) and
  `<id>.log`; the page polls them.

### Server

- `pipeline/studio/server.py`: `ThreadingHTTPServer` on 127.0.0.1 only (port `STUDIO_PORT`, default 4040).
- API (JSON): `GET /api/videos`, `GET /api/videos/<n>`, `GET|PUT /api/videos/<n>/doc/<file>` (only the documents a
  phase lists), `POST /api/videos` (new), `POST .../action` (a fixed list mapped to `yt` commands), `POST .../request`
  (form), `POST .../chat`, `GET|POST .../questions`, `GET|POST .../comments/<review>`, `POST .../phase` (mark a step,
  approve a phase), `GET /api/jobs/<n>/<id>`.
- `GET /media/<n>/<path>` serves files inside the video folder with HTTP Range (video seeking).
- Safety: binds to 127.0.0.1; every POST and PUT needs the header `X-Studio: 1` (stops other sites posting to it);
  paths are resolved and must stay inside the video folder; commands run as argument lists, never through a shell.
- launchd agent `com.youtube-edit.studio` (install.sh), and `yt app` to start it by hand and open the page.

## Not in this version

- Google Docs: a one-way "share as Google Doc" for comments from others, later.
- Metrics pulled automatically: the Results phase has a "pull metrics" request (Claude with the Supermetrics or a
  YouTube connector, once authorised in claude.ai, if headless runs can use it) and fields to type them in.
- Uploading recordings through the browser: they're too big; the Recording phase shows the raw/ path and a Finder
  button.

## Testing

`pipeline/studio/tests/` (unittest, standard library): the scaffold (`yt new` writes every file, refuses an existing
name, sanitises the name), script-sheets (blockquotes, demo markers, copy blocks, links into references.md), phase
derivation from state.json, the server against a temporary videos folder (board, doc save inside the folder only,
path escapes refused, the header check, Range requests, questions and comments round trips, actions limited to the
list). Claude and `yt` calls are replaced by a stand-in command in tests.
