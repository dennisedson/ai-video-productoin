# Headshots for thumbnails

Drop headshots here (JPG, PNG, HEIC, WebP). They are git-ignored, so copy them to each Mac yourself.

- A PNG that's already cut out (transparent background) is used as it is; anything else is cut out automatically.
- Use one for a single thumbnail ("thumbnail 1: use dennis.jpg"), or for every video on a profile: set `"face":
  "dennis.jpg"` in `.claude/skills/youtube-edit/profiles/<profile>/thumbnail/config.json` (`"frame"` = a frame from
  the video, the default).
- A guest's headshot goes in that video's own folder (`videos/<name>/`) instead.
- Best results: head and shoulders, looking at or near the camera, at least 1500 px tall, even light.
