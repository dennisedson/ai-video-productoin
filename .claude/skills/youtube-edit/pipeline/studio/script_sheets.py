#!/usr/bin/env python3
"""script_sheets.py: SCRIPT.md -> teleprompter.txt and recording-sheet.md, and its links into references.md.

SCRIPT.md: "## " sections; read-aloud lines as "> " blockquotes (the teleprompter gets only these); demo beats as
lines starting "→ demo:" (or "-> demo:"); anything Dennis pastes in fenced blocks opened with ```copy: <label>.

  python3 script_sheets.py NAME
"""
import os, re, sys, textwrap

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core

WIDTH = 32
URL = re.compile(r"https?://[^\s)>\]`'\"|]+")


def build(script):
    tp, outline, copies, links = [], [], [], []
    section, in_copy, label, buf = "", False, "", []
    for raw in script.splitlines():
        line = raw.rstrip()
        if in_copy:
            if line.strip().startswith("```"):
                copies.append((label, "\n".join(buf))); in_copy = False
                for u in URL.findall("\n".join(buf)):
                    links.append((label, u.rstrip(".,;")))
            else:
                buf.append(line)
            continue
        m = re.match(r"^\s*```copy:\s*(.*)$", line)
        if m:
            in_copy, label, buf = True, m.group(1).strip() or "Copy", []
            outline.append("   - paste: %s" % label)
            continue
        if line.startswith("## "):
            section = line[3:].strip()
            tp += ["", "— %s —" % section.upper(), ""]
            outline.append("\n## %s" % section)
            continue
        if line.startswith("# "):
            continue
        if line.lstrip().startswith(">"):
            text = line.lstrip()[1:].strip()
            if text:
                tp += textwrap.wrap(text, WIDTH, break_long_words=False) or [text]
                tp.append("")
            continue
        m = re.match(r"^\s*(?:→|->)\s*demo:\s*(.*)$", line, re.I)
        if m:
            tp += ["→ DEMO: %s" % m.group(1).strip(), ""]
            outline.append("- demo: %s" % m.group(1).strip())
            continue
        for u in URL.findall(line):
            links.append((section or "script", u.rstrip(".,;")))
    teleprompter = re.sub(r"\n{3,}", "\n\n", "\n".join(tp)).strip() + "\n"
    sheet = ["# Recording sheet", "", "## Outline"] + outline + ["", "## Copy and paste, in order", ""]
    for i, (lab, body) in enumerate(copies, 1):
        sheet += ["%d. %s" % (i, lab), "", "```", body, "```", ""]
    seen, uniq = set(), []
    for lab, u in links:
        if u not in seen:
            seen.add(u); uniq.append((lab, u))
    return teleprompter, "\n".join(sheet).rstrip() + "\n", uniq


def merge_references(path, links):
    text = open(path).read() if os.path.isfile(path) else "| Label | URL | Used for | Status | Checked |\n| --- | --- | --- | --- | --- |\n"
    have = set(URL.findall(text))
    add = ["| %s | %s | script | unchecked | |" % (lab.replace("|", "/"), u) for lab, u in links if u not in have]
    if add:
        if not text.endswith("\n"):
            text += "\n"
        text += "\n".join(add) + "\n"
        open(path, "w").write(text)
    return len(add)


def run(name):
    w = core.video_dir(name)
    tp, sheet, links = build(open(os.path.join(w, "SCRIPT.md")).read())
    open(os.path.join(w, "teleprompter.txt"), "w").write(tp)
    open(os.path.join(w, "recording-sheet.md"), "w").write(sheet)
    n = merge_references(os.path.join(w, "references.md"), links)
    print("teleprompter.txt: %d lines; recording-sheet.md; %d new link%s in references.md" % (tp.count("\n"), n, "" if n == 1 else "s"))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    run(sys.argv[1])
