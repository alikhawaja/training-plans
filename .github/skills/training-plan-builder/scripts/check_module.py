"""Check module structure without external packages; does not execute its labs."""

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import unquote

HEADINGS = (
    "Purpose and outcomes",
    "Starting point",
    "Concept introduction",
    "Guided lab",
    "Independent exercise",
    "Failure or variation",
    "Verification and evidence",
    "Troubleshooting",
    "Reset and handoff",
    "Knowledge check",
    "Reference implementation",
)


def check(path):
    text = path.read_text(encoding="utf-8")
    errors = []
    prose = re.sub(r"^```[^\n]*\n.*?^```\s*$", "", text, flags=re.MULTILINE | re.DOTALL)
    if not re.match(r"^# Module \d+: .+", text):
        errors.append("title must use '# Module N: Title'")
    headings = re.findall(r"^## (.+)$", prose, re.MULTILINE)
    if headings != list(HEADINGS):
        errors.append("use the eleven template section headings in their defined order")
    sections = re.split(r"^## .+\n", prose, flags=re.MULTILINE)[1:]
    if any(not section.strip() for section in sections):
        errors.append("a required section is empty")
    if len(re.findall(r"^```", text, re.MULTILINE)) % 2:
        errors.append("unbalanced triple-backtick fences")
    if "```mermaid\n" not in text:
        errors.append("include a Mermaid concept diagram")
    if re.search(r"\{\{.+?\}\}", text, re.DOTALL):
        errors.append("unresolved authoring-template placeholder")
    if re.search(r"\b\d+(?:\s*[-–]\s*\d+)?\s*(?:minutes?|hours?|days?|weeks?)\b", prose, re.I):
        errors.append("remove duration estimates; describe learning outcomes instead")
    if re.search(r"\b(?:day\s+\d+|suggested time|completion estimate)\b", prose, re.I):
        errors.append("remove schedule/completion-estimate language")
    for link in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text):
        if re.match(r"(?:[a-z][a-z0-9+.-]*:|#)", link, re.I):
            continue
        target = unquote(link.split("#", 1)[0])
        if not (path.parent / target).exists():
            errors.append(f"missing local link target: {link}")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("modules", nargs="+", type=Path)
    args = parser.parse_args()
    failed = False
    for path in args.modules:
        if not path.is_file():
            errors = ["module file does not exist"]
        else:
            errors = check(path)
        if errors:
            failed = True
            for error in errors:
                print(f"{path}: {error}", file=sys.stderr)
        else:
            print(f"PASS: {path} (structural checks only)")
    return int(failed)


if __name__ == "__main__":
    sys.exit(main())
