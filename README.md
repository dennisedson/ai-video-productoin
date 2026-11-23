# ai-video-production

Dennis's YouTube editing setup: the youtube-edit skill (WeAreNoCode's, customised) with its hands-off pipeline, the
`hubspot` and `devs-after-dark` profiles, and the shared sound effects and images. It runs locally in Claude Code on a
Mac and renders 4K with HyperFrames.

The repo is the Claude Code project folder. Clone it, open Claude Code on it, and the skill and `CLAUDE.md` load.
`videos/` is ignored, so footage, edits and renders never leave the machine that made them.

| Path | What it is |
|---|---|
| `.claude/skills/youtube-edit/` | the skill: `SKILL.md`, `scripts/`, `pipeline/`, `profiles/`, `formats/`, `assets/` |
| `CLAUDE.md` | how Claude Code handles approvals and notes, and what differs between the two Macs |
| `shared/` | the `--shared` folder every edit uses: `sfx/`, `img/`, `DAD-Audio/` |
| `WeAreNoCode-YouTube-Editor/` | the style guide (with the "Yours" column), setup notes and licences |
| `videos/` | one folder per video (`videos/<name>/raw/`) and the pipeline inbox `videos/_inbox/`; not in git |

Connectors are optional. Tella and Epidemic Sound help when they're there; without them you record the screen with
anything and use `shared/sfx` and music you're licensed to use.

---

## Set up a new Mac (the work Mac)

### 0. Check with IT first
Find out whether you're allowed to:
- clone a private repo from your personal GitHub account
- install Homebrew, and packages from npm and pip
- download the Parakeet speech-to-text model (`npx hyperframes models install parakeet`)
- run Google Chrome (HyperFrames renders through it, in the background)
- use Claude Code on this machine, and with which account (probably HubSpot's, not your personal one)
- add a LaunchAgent (only for the hands-off pipeline in step 8; everything else works without it)

### 1. Clone the repo

    git clone https://github.com/dennisedson/ai-video-production.git ~/Video

Any folder works; the rest of this guide calls it the Video folder. If git asks for a password, sign in with
`gh auth login` or a personal access token.

### 2. Open Claude Code on the folder
- Claude desktop app → New → **Claude Code**
- **Local**, not cloud, so footage and renders stay on the machine
- Folder: the Video folder
- Permissions: **Auto** if your work setup allows it, otherwise **Ask**
- Model: the latest Opus for setup

### 3. Turn on the browser and install Chrome
Settings → Claude Code → turn on the browser setting. Install Google Chrome if it isn't there.

### 4. Install the dependencies and run the tests
Paste this into Claude Code:

> The youtube-edit skill is already installed in .claude/skills/youtube-edit. Run its setup check: verify Node 22+,
> HyperFrames (npx hyperframes --version and npx hyperframes doctor), FFmpeg/ffprobe, Python 3 with numpy, auto-editor,
> Parakeet (npx hyperframes models install parakeet) and Chrome. Install whatever is missing with Homebrew and pip, and
> ask me before anything that needs admin rights. Also download the local GSAP copy and the HyperFrames media skill
> (npx hyperframes skills update media-use). The sound effects are already in shared/sfx; don't copy them again. Then
> run the tests from the scripts folder: cd .claude/skills/youtube-edit/scripts && python3 -m unittest tests

- If Homebrew's Python refuses `pip install numpy`, use `brew install numpy`.
- `hyperframes doctor` may flag Kokoro TTS, MusicGen and Docker. The skill uses none of them; ignore those.
- You're done when the tests end with **OK**.

### 5. Start a new thread
Skills load when a thread starts. Open a new Claude Code thread on the Video folder and ask "what skills do you
have?" `youtube-edit` should be in the list.

### 6. Smoke test with a 30–60 s hook
- Record a talking-head hook (4K, 30 fps, nothing baked in). Fluffed a line? Pause about 2 s and restart the sentence.
- Put it in `videos/test-hook/raw/`
- Prompt: "Use the HubSpot profile. Please use my YouTube editing skill to edit this hook: videos/test-hook/raw/<file>"
- **Checkpoint A:** `PAPER-CUT.md` (what gets cut) and the camera grade sheet. The home camera wants `blacks`; with a
  different camera or room, look at the sheet before choosing.
- **Checkpoint B:** `storyboard.json` and `snaps/sheet.png` (the planned overlays). Claude also writes `render.json`.

### 7. Render
In Terminal, from the Video folder:

    bash .claude/skills/youtube-edit/scripts/render-mac.sh videos/test-hook

One command, no AI in the loop. It builds the graded 4K cut, renders, levels to -14 LUFS, checks the result, adds the
intro sting and end card when `render.json` has `bookends`, and copies the file to `~/Movies/YouTube Renders/<name>/`.
On a failure it prints the step to resume from (`--from STEP`); `--dry-run` shows the commands.

### 8. Optional: the hands-off pipeline
Needs the `claude` command line signed in once and permission to add a LaunchAgent. From the Video folder:

    bash .claude/skills/youtube-edit/pipeline/install.sh

Then drop recordings into `videos/_inbox/<name>/` (camera file, screen file for a tutorial, optional `notes.txt` such
as "HubSpot profile"). A notification comes at each checkpoint; approve or send notes in a Claude Code thread
("approve <name>, grade blacks"). `yt status`, `yt log <name>`, `yt run <name> cut|storyboard|render`.
`--budget N` caps each Claude stage (default $20); `uninstall.sh` removes it. `install.sh` writes
`pipeline/config.sh` for that machine; it isn't in git.

If IT blocks LaunchAgents, skip this step: run the same stages by hand in a Claude Code thread and render with step 7.

---

## Render work videos on the home Mac

The home Mac renders much faster, so the work Mac does the edit (the cut, the storyboard, both checkpoints) and the
home Mac does the 4K render. Nothing AI runs on the home Mac for this, so the personal Claude account isn't involved.
The work Mac sends only what the render needs (about 1.5 GB of a 10 GB project), gets the finished video back, delivers
it to `~/Movies/YouTube Renders/<name>/` as usual, and deletes the files from the home Mac.

**If the home Mac isn't mounted, it asks, and never renders on the work Mac without asking.** When the render is
about to start:
- from a Claude Code thread (approving at Checkpoint B): Claude runs `yt host` and asks you whether to mount the home
  Mac or render on the work Mac;
- unattended: a dialog on the work Mac: **Check again** (after you mount it), **Render on this Mac**, or **Later**.
  Later (or no answer in 4 hours) leaves the video in `awaiting-host` with a notification; start it again with
  `yt run <name> render`, or `yt run <name> render --here` to render on the work Mac.

Devs:After Dark doesn't use this: it's edited and rendered on the home Mac only.

### Home Mac (once)
1. `git pull` in the Video folder, then `bash .claude/skills/youtube-edit/pipeline/install.sh --serve-renders`.
   That loads a second agent that watches `videos/_render-inbox/` and checks in every minute.
2. System Settings → General → Sharing → **File Sharing** on. Under Shared Folders add the Video folder
   (`~/AI/claude-cowork/Video`) and give your user Read & Write.
3. The home Mac renders only while it's awake and you're logged in. If it sleeps, the work Mac sees that (the agent
   stops checking in) and asks. Energy settings: keep it awake on power while the display is off.

### Work Mac (once)
1. `git pull` in the Video folder.
2. Finder → Go → Connect to Server → `smb://<home Mac's name>.local` → choose **Video**. Tick "Remember this password
   in my keychain". It mounts at `/Volumes/Video`. To mount it at login, add it to System Settings → General → Login
   Items.
3. `bash .claude/skills/youtube-edit/pipeline/install.sh --render-host /Volumes/Video --priority background` (use the
   path it actually mounted at; `--render-host none` turns this off). `--priority background` runs the cut and
   storyboard stages on the efficiency cores so the fans stay down; they take longer (`--priority normal` undoes it).
   The checkpoints already work at 1080p on both Macs: only the final render builds 4K.
4. `yt host` should say `home Mac ready`. The first time, macOS may ask whether Terminal can use network volumes:
   allow it.

### Going back to the known-good version
The tag `before-remote-render` (commit `dfbf480`) is the setup both Macs ran on 2026-11-22: renders on each Mac, 4K
checkpoints, the inbox agent only. `videos/` isn't in git, so going back or forward never touches footage or edits,
and a video started on either version renders on the other. On either Mac, from the Video folder, with no stage
running (`yt status`):

    bash .claude/skills/youtube-edit/pipeline/uninstall.sh      # stops both agents (this version knows both)
    git checkout before-remote-render
    bash .claude/skills/youtube-edit/pipeline/install.sh        # the old installer: inbox agent only, fresh config

Forward again: `git checkout main && git pull`, then `install.sh` with the flags you use on that Mac. If the tag
isn't there (`git tag` shows nothing), use `dfbf480` in its place, or create it once: `git tag before-remote-render
dfbf480 && git push origin before-remote-render`.

### If something goes wrong
- `yt host` says what's missing: not mounted, the agent isn't installed, or the home Mac hasn't checked in.
- A render that fails on the home Mac comes back as `failed` with its log in `videos/<name>/render-remote.log`. The
  files stay on the home Mac (`videos/_render-inbox/<name>/`): `yt run <name> render` sends them again, or resume
  there with `render-mac.sh videos/_render-inbox/<name> --from STEP`.
- If the share drops during a render, the home Mac keeps rendering and the work Mac keeps waiting for 10 minutes, then
  stops. Mount it again and run `yt run <name> render` to send it again.

---

## Turn the home Mac's folder into a clone (once)

The home folder (`~/AI/claude-cowork/Video`) already has these files, so connect it to the repo instead of cloning
again. Don't change the skill until this is done. In Terminal:

    cd ~/AI/claude-cowork/Video
    git init -b main
    git remote add origin https://github.com/dennisedson/ai-video-production.git
    git fetch origin
    git reset origin/main          # points at the repo; your files are untouched
    git status                     # expect only CLAUDE.md (the repo adds a "Machines" section)
    git checkout -- .              # take the repo's versions
    git branch --set-upstream-to=origin/main
    rm .repo-export.tgz            # left over from building the repo

`videos/`, `Claude outputs/` and the upstream `WeAreNoCode-YouTube-Editor/youtube-edit/` copy are ignored and stay
as they are.

## Keeping the two Macs in step

- After a change to the skill or a profile (including "save this to the skill"): ask Claude Code to commit and push,
  or run `git add -A && git commit -m "..." && git push`.
- Before an edit on the other Mac: `git pull`. Threads load the skill when they start, so pull before opening one.
- If both Macs changed the skill, `git pull` merges; `SKILL.md` is long, so commit small and often to avoid conflicts.

## Music and sound
- Sound effects: `shared/sfx` (the free HyperFrames library).
- Music on the work Mac: no Epidemic Sound connector. Use music HubSpot is licensed to use, put the file in the
  video's folder and tell Claude which one. A personal or creator Epidemic Sound licence may not cover a company
  channel, so check before using those tracks in HubSpot videos.

## Licences
The skill started as WeAreNoCode's starter kit (MIT, see `WeAreNoCode-YouTube-Editor/LICENSES/`). The HubSpot fonts in
`profiles/hubspot/fonts/` are HubSpot's and the Devs:After Dark assets are Dennis's; keep the repo private.

---

## Context for a Claude project on the work account

Claude Code gets its context from `CLAUDE.md`. A Claude project on the work account is for planning chats (scripts,
video ideas, review notes) that should know about the setup.

**Name:** HubSpot Video Production

**Description:** Editing HubSpot developer videos locally with Claude Code and the youtube-edit skill.

**Instructions** (paste into the project's instructions):

> I'm Dennis, a Senior Developer Advocate on HubSpot's builder relations team. I make developer videos (talking-head
> hooks and screen tutorials) and edit them with Claude Code on this Mac, using the youtube-edit skill (originally
> WeAreNoCode's, customised by me). The setup lives in my private repo dennisedson/ai-video-production, cloned on my home
> Mac and this work Mac.
>
> How the setup works:
> - Edits run locally in Claude Code on the Video folder; renders always run on the Mac with
>   `.claude/skills/youtube-edit/scripts/render-mac.sh`, never in the cloud. Footage stays on the machine.
> - Every HubSpot video uses the `hubspot` profile: Orange #FF4800 key words, Deep Teal #042729 background, Cream cards
>   with Neutral text, HubSpot Sans for words and HubSpot Serif for headlines. A 3 s intro sting goes after the hook
>   (never before it), and a 15 s end card ("Up next" plus YouTube end-screen placeholders) goes after the sign-off.
> - No connectors on this machine: no Tella, no Epidemic Sound. Screen recordings come in as plain files; music must be
>   HubSpot-licensed; sound effects come from `shared/sfx`.
> - Each edit stops at two checkpoints for my approval: A (the paper cut plus the camera grade, usually `blacks`) and
>   B (the storyboard with its overlay sheet and a 1080p preview).
> - Tutorials are two files (face + screen). The face card goes on the side I look toward, never facing off-screen.
>   The video opens full frame on me until the screen matters, and any stretch of 8 s or more with nothing worth
>   watching on screen goes full frame too.
>
> When I ask for help in this project: write scripts and hooks for camera (short sentences, a clear first line that
> names the topic), plan tutorials so the screen is worth watching, and turn my review notes into timestamped
> instructions I can paste into Claude Code. Keep answers short.

**Knowledge:** add this README and `WeAreNoCode-YouTube-Editor/STYLE-GUIDE.md`.
