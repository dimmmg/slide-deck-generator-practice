#!/usr/bin/env python3
"""Local Markdown → Marp → editable PPTX lesson generator (Python 3.9+)."""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = "urn:slide-deck-generator:"


def parse_plan(source):
    """Keep Markdown body intact; headings outside fenced code start slides."""
    lines = source.lstrip("\ufeff").splitlines()
    if lines and lines[0].strip() == "---":
        # Distinguish YAML front matter from an initial slide separator.
        end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
        if end and any(re.match(r"^[\w-]+\s*:", x) for x in lines[1:end]):
            raise ValueError("Входной план должен быть без YAML front matter; используйте # заголовки и ---.")
    slides, title, body, fence = [], None, [], None
    has_heading = False

    def finish():
        nonlocal title, body
        content = "\n".join(body).strip()
        if title or content:
            slides.append((title or "Продолжение", content))
        title, body = None, []

    for line in lines:
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if fence:
            body.append(line)
            if marker and marker[1][0] == fence[0] and len(marker[1]) >= len(fence) and not marker[2].strip():
                fence = None
            continue
        if marker:
            fence = marker[1]
            body.append(line)
            continue
        if re.fullmatch(r"\s*---\s*", line):
            finish()
            continue
        heading = re.match(r"^ {0,3}#{1,6}\s+(.+?)\s*$", line)
        if heading:
            has_heading = True
            finish()
            title = re.sub(r"\s+#+\s*$", "", heading[1]).strip()
        else:
            body.append(line)
    if fence:
        raise ValueError("Незакрытый блок кода: добавьте закрывающую строку ограждения.")
    finish()
    if not slides:
        raise ValueError("План пуст: добавьте заголовок и тезисы.")
    if not has_heading:
        raise ValueError("В плане нужен хотя бы один Markdown-заголовок (# или ##).")
    return slides


def marp_markdown(slides):
    pages = ["# " + title + "\n\n" + body for title, body in slides]
    return "---\nmarp: true\ntheme: default\npaginate: true\n---\n\n" + "\n\n---\n\n".join(pages) + "\n"


def generate(plan, output, command, actor="student", lesson_id=None, pdf=False, markdown_only=False):
    plan, output = Path(plan).resolve(), Path(output).resolve()
    raw = plan.read_text(encoding="utf-8-sig")
    slides = parse_plan(raw)
    stem = plan.stem
    draft = output / (stem + ".marp.md")
    output.mkdir(parents=True, exist_ok=True)
    draft.write_text(marp_markdown(slides), encoding="utf-8")
    return draft, len(slides)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Markdown → Marp → редактируемый PPTX")
    parser.add_argument("plan", nargs="?", type=Path)
    parser.add_argument("--plan", dest="plan_option", type=Path)
    parser.add_argument("-o", "--output", type=Path, default=Path("out"))
    parser.add_argument("--markdown-only", action="store_true", help="Создать только Marp Markdown")
    args = parser.parse_args(argv)
    if not (args.plan or args.plan_option):
        parser.error("Укажите входной файл")
    try:
        command = []
        result, count = generate(args.plan or args.plan_option, args.output, command)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 1
    print(f"Готово: {result} ({count} слайдов).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
