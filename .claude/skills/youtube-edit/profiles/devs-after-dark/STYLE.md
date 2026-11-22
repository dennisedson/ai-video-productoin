# Devs:After Dark profile

The video podcast (devsafterdark.com): "The internet, *after* bedtime." Hosts Nick James Laporte, Dennis Edson,
A.J. La Porte, plus a guest; conversational episodes of 30–75 min recorded as a one-hour Zoom call, plus short clips.
Tokens read from the live site (2026-11-22).

## Colour
| Token | Value | Use |
|---|---|---|
| `--cyan` (key word) | Amber `#FBBF24` | key words (italic), pips, the one accent per frame |
| `--blue` (wash) | Night `#0F1116` | backgrounds; cards `#161922`, paper `#1C2030` |
| `--white` | Cream `#F3EEE2` | all type |
| `--magenta` (payoff) | Sky `#7DD3FC` | rare second accent: links, a payoff |
| `--amber` (secondary) | Mute `#8A8D99` | labels, secondary text |
Hairlines `rgba(255,255,255,.10)`.

## Type
- Headlines, lower lines, titles: Playfair Display 700, tight (-0.02em); the key word in **amber italic** (as "after").
- Body and UI: Inter 400–700.
- Labels, episode numbers, timestamps: JetBrains Mono 500, caps, tracked +0.14em, Mute.

## Voice and pacing (a podcast, not a tutorial)
- Late-night, playful, self-aware. Overlays are sparse: the conversation is the show.
- Name lower thirds the first time each person speaks; topic cards at chapter changes; a callout only when something is
  named that viewers would look up (a tool, a repo, a person) — about one every few minutes, not per sentence.
- No sound effects under talk.

## Logo and intro
- Logo: `assets/DevsAfterDark-colon-white.svg` (wide) and `-stacked.svg`; one path per letter, "After" in amber.
- Intro (`intro/`, 15.4 s, draft): cold open 0-9.15 s = a teaser of 3-4 short moments from THIS episode (picked in
  the editorial pass: funny, surprising or quotable lines, each a complete thought, theme low underneath), then the wordmark builds on "DAD-Decisive Hit" (shared/DAD-audio):
  Devs rises on the drums (9.15), the colon blinks on the hits (9.65, 10.15), Dark drops, After wipes in along its slant,
  the decisive hit (12.22) punches it with an amber glow, the tagline in the quiet after. `tools/intro_gen.py` builds it.

## Was missing (now supplied)
- The logo file (the site's `logo.webp` wordmark, "Devs:AfterDark"): put the original (SVG or transparent PNG) in
  `assets/` before building the intro and end card.
