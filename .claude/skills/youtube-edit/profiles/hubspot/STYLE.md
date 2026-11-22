# Profile: HubSpot

For HubSpot work. Dennis names the profile at the start of an edit ("use the HubSpot profile"); it goes into
`storyboard.json` as `"profile": "hubspot"` and `compose.py` applies it. From the "Yours" column of
`WeAreNoCode-YouTube-Editor/STYLE-GUIDE.md`; anything not listed here keeps the house rule in SKILL.md.

## Colours (the house token names stay; their values change)
| Token | Role | Value |
|---|---|---|
| `--cyan` | highlight: key words, ticks, bars | HubSpot Orange `#FF4800` |
| `--blue` | deep anchor, gradient end, the wash | Deep Teal `#042729` |
| `--magenta` | punchline, the payoff word | Pink `#FCC3DC` |
| `--amber` | money and stakes | Sage `#B9CDBE` |
| text | | White on dark scenes, Neutral `#141414` on a bright room, `#110C0A` on cards |

Highlighted words are never dark; only one gradient per frame.

## Fonts (`profiles/hubspot/fonts/`)
- **HubSpot Sans** (Book 400, Medium 500, Bold 700; stack `"HubSpot Sans", -apple-system, system-ui, "Segoe UI", sans-serif`): lower lines, labels, pills, tags, everything that is not a headline.
  The style guide names Lexend Deca here; Dennis supplied HubSpot Sans, so it is used until he says otherwise.
- **HubSpot Serif** (Book 400, Medium 500): headlines and big callouts (`.slabel`, `.st-title`, or class `serif` on a
  hand-built element). Medium is the heaviest weight; no stroke, no faux bold.
- Big numbers: HubSpot Serif Medium, every digit written out, white on dark / Neutral on bright, counting up.
- Sentence case. A big-statement headline may end with the orange dot `●`.

## Cards
- Solid, never frosted, matched to the HubSpot developer docs site: Cream `#F5F0EE`, no border, no shadow, 14px radius on
  cards (pills and tags stay pill-shaped), 24px padding, text `#110C0A`, the key word in Orange. (The style guide said
  `#F8F5EE` with a 1px Deep-Teal border at ~12% and a 16px radius; the docs site wins.)
- On dark scenes the Deep-Teal code-block window is the card.
- Default for words: one line at the bottom, key words in Orange, with a tight Deep-Teal edge so Orange holds over
  footage (it vanished on a red shirt).
- Punchline chip: the Deep-Teal card (`rgba(4,39,41,.94)`), white words, the payoff word in Pink, a pink hairline.

## App windows
A clean, designed window with HubSpot's code-block chrome: a Deep-Teal `#042729` frame, 16px radius, macOS dots (red
`#FF6058` / yellow `#FFBE2E` / green `#28C840`) or one sage "live" dot, JetBrains Mono for any code. Never a raw screenshot.

## Bookends
- Intro sting (`intro/`, 3 s): series line in Sage with an Orange dot, the episode title in HubSpot Serif Cream letter
  by letter, an Orange underline, and the HubSpot sprocket (the official file, `assets/hubspot-sprocket.svg`) building
  itself: it spins in as the ring pops, the spokes grow, the end circles snap on, and it always ends upright (never leave
  the logo rotated). Whoosh in, soft bass hit, whoosh out.
- End card (`outro/`, 15 s): the sprocket builds above the text; "Up next" + the next video in Serif when one is named,
  else "Thanks for watching" + "Keep building" (YouTube's "Best for viewer" fills the box); Orange underline, an outlined 16:9 box (YouTube's video
  element) and a Pink-edged circle (the subscribe element), fade to black at the end.
- `tools/sprocket_patch.py` wrote the sprocket into both templates (the piece clips are measured on the official file).
