# Video studio Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `yt new` scaffolds a video project with phases from ideation to results, and `yt app` serves a localhost studio where Dennis follows each video, edits its documents, reviews with pinned comments, answers questions and talks to Claude.

**Architecture:** A pure-Python core module (`pipeline/studio/core.py`) owns the video folder (video.json, phase derivation, scaffold, questions, comments, jobs). `server.py` exposes it over a small JSON API on 127.0.0.1 and serves a plain HTML/JS page from `web/`. Claude runs and `yt` commands are background jobs started as argument lists. `phases.json` and `templates/` hold the content of each phase so it can change without code.

**Tech Stack:** Python 3 standard library (http.server, json, subprocess, unittest), plain HTML/CSS/JavaScript, bash (`yt`, install.sh, inbox.sh), launchd.

## Global Constraints

- Python standard library only; no npm, no build step (the work Mac's company registry blocks npm packages).
- The server binds to 127.0.0.1 only; port `STUDIO_PORT`, default 4040.
- Every POST and PUT needs the header `X-Studio: 1`.
- File access resolves paths and refuses anything outside `videos/<name>/`.
- Commands run as argument lists, never through a shell.
- Form requests default to Sonnet (`STUDIO_MODEL`, default `sonnet`) with the config's `BUDGET_USD` cap.
- Every request form ends with a free-form option.
- Phase ids: ideation, script, recording, cut, storyboard, render, packaging, publish, results.
- Tests: `python3 -m unittest discover .claude/skills/youtube-edit/pipeline/studio/tests`; Claude and `yt` are replaced by a stand-in command (`STUDIO_CLAUDE`, `STUDIO_YT` env vars).

## Files

```
.claude/skills/youtube-edit/pipeline/studio/
  core.py            video folder model: paths, video.json, derive_phase, list_videos, scaffold, questions, comments, jobs
  script_sheets.py   SCRIPT.md -> teleprompter.txt, recording-sheet.md, links into references.md
  server.py          HTTP API + static + media with Range
  phases.json        phases: steps, docs, forms
  templates/         BRIEF-colleague.md BRIEF-problem.md BRIEF-feature.md research.md references.md SCRIPT.md
  prompts/           form.md (the request wrapper), chat.md, notes.md
  web/               index.html app.css app.js
  tests/             test_core.py test_sheets.py test_server.py
.claude/skills/youtube-edit/pipeline/yt               new, app, ask
.claude/skills/youtube-edit/pipeline/install.sh       studio launchd agent
.claude/skills/youtube-edit/pipeline/inbox.sh         claim a drop into a scaffolded video
.claude/skills/youtube-edit/pipeline/prompts/checkpoint-a.md, checkpoint-b.md   ask with `yt ask`
.claude/skills/youtube-edit/profiles/hubspot/VOICE.md  seeded from the three transcripts
CLAUDE.md, README.md                                   how to work from the studio
```

### Task 1: core.py (video model, phases, scaffold)

**Interfaces (produces):**
- `ROOT`, `videos_dir() -> Path`, `video_dir(name) -> Path` (raises ValueError on a bad name or a path escape)
- `slug(text) -> str` (lowercase, a-z0-9 and hyphens)
- `load_video(name) -> dict`, `save_video(name, data)`
- `PHASES: list[dict]` from phases.json; `derive_phase(video: dict, state: dict|None) -> str`
- `list_videos() -> list[dict]` (name, title, phase, waiting_on, open_questions)
- `scaffold(name, origin, title="", series="", profile="hubspot", presenter="") -> Path` (FileExistsError if taken)
- `ask(name, text, options=None, frm="claude") -> dict`, `answer(name, qid, text) -> dict`, `questions(name) -> list`
- `comments(name, review) -> list`, `save_comments(name, review, items)`
- `start_job(name, kind, argv, env=None) -> str`, `job(name, jid) -> dict`
- CLI: `python3 core.py new NAME --origin O [--title T]`, `python3 core.py ask NAME TEXT [--options a|b]`

- [ ] Write tests: scaffold writes video.json, BRIEF.md from the origin's template, research.md, references.md, SCRIPT.md, raw/; refuses an existing folder; slug sanitises; derive_phase maps state.json stages (cutting/awaiting-A -> cut, storyboarding/awaiting-B -> storyboard, rendering/awaiting-import/awaiting-host -> render, done -> packaging unless video.json phase is later; origin finished -> packaging); video_dir refuses `../x`; ask/answer round trip; list_videos counts open questions.
- [ ] Run, see them fail; implement; run, pass; commit.

### Task 2: script_sheets.py

**Interfaces:** `build(script_text) -> (teleprompter: str, sheet: str, links: list[tuple[label, url]])`; `run(name)` writes both files and merges links into references.md (no duplicates by URL).

- [ ] Tests: blockquote lines become wrapped teleprompter lines (<= 32 chars), `→ demo:` lines become `→ DEMO: ...`, `## ` headings become section breaks; copy fences (```copy: Label) are numbered in the sheet in order; URLs in copy blocks and in text come back as links; references merge keeps existing rows.
- [ ] Implement, pass, commit.

### Task 3: server.py (API, static, media)

**Interfaces:** `make_server(port, root=None) -> ThreadingHTTPServer`; routes per the spec.

- [ ] Tests (server on an ephemeral port, ROOT pointed at a temp folder, STUDIO_CLAUDE/STUDIO_YT = a stand-in script): GET /api/videos; POST /api/videos creates; POST without X-Studio -> 403; GET/PUT doc inside the phase docs, PUT of `../../x` -> 400; media Range returns 206 with the right bytes; questions and comments round trip; action outside the list -> 400; action in the list starts a job whose argv is the stand-in plus the yt args; request and chat start jobs (chat stores chat_session and uses --resume the second time).
- [ ] Implement, pass, commit.

### Task 4: phases.json, templates, prompts, VOICE.md

- [ ] phases.json: the nine phases, each with steps (id, title, instructions, template?, done_file?), docs, forms (id, label, fields, prompt) and a free-form form; the review phases name their review (A, B, package).
- [ ] templates per origin; prompts/form.md (the wrapper: video folder, phase, the brief, references, VOICE.md, answered questions, "ask with yt ask", the form's text), chat.md, notes.md (structured comments to notes for the stage).
- [ ] VOICE.md seeded from the three transcripts' openers, sign-offs and habits.
- [ ] Test: phases.json loads, ids match the constraint list, every phase's forms end with freeform, every template it names exists. Commit.

### Task 5: the web app

- [ ] index.html/app.css/app.js: board (phase columns, cards, badges, New video form); video page (phase list, steps with done boxes, doc editors with preview and save, forms, questions, actions with streamed job logs, chat panel); review (player, stills, C to comment with captured frame, box drawing on frame/still, drag a still into a comment, timeline markers, send notes, approve, picks for packaging). Markdown preview: a small renderer (headings, lists, bold, code, links, blockquotes).
- [ ] Check by running the server on the real videos folder and opening the board, agentcli's page and its B review (Read a screenshot via a headless snapshot if available). Commit.

### Task 6: yt, launchd, inbox, prompts, docs

- [ ] `yt new [NAME] [--origin O]` (prompts for a missing name in a terminal), `yt app` (start if not running, open the page), `yt ask NAME "q" [--options "a|b"]`.
- [ ] install.sh: `com.youtube-edit.studio` agent (KeepAlive, the studio server).
- [ ] inbox.sh: a drop whose name matches a scaffolded video still in recording goes into that video instead of being refused.
- [ ] checkpoint-a/b prompts: questions with `yt ask` as well as in the write-up; read answered questions from questions.json.
- [ ] CLAUDE.md: a Dennis request in a thread that names a video works in that video's context; the studio is the main way in. README: the studio section.
- [ ] Run all tests; start the agent; commit and push.
