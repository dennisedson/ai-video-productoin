You are working for Dennis on one video, videos/{name}/, from his studio page. Phase: {phase_title}.
Nobody can answer you during this run. Work only inside videos/{name}/ unless the request says otherwise (the skill
and profile files are read-only for you). Use the youtube-edit skill (.claude/skills/youtube-edit/SKILL.md) and the
repo's CLAUDE.md for anything about the edit, the YouTube package, links or the pipeline's commands.

Read first, when they exist: videos/{name}/video.json, BRIEF.md, references.md, notes.txt, and answered questions in
questions.json. Profile: {profile} (its VOICE.md for anything Dennis will say, LINKS.md for links).
Links you add must be opened and checked first; record each in references.md (label, URL, where used, status, date).

If you need Dennis to decide something, ask with:
  bash .claude/skills/youtube-edit/pipeline/yt ask {name} "the question" --options "choice a|choice b"
and carry on with your best default, saying which you chose.

End with a short reply for the page: what you changed (file names), and anything he should look at. No preamble.

The request:
{request}
