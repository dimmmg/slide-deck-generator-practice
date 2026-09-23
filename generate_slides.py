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
    if draft.resolve() == plan or (draft.exists() and draft.samefile(plan)):
        raise ValueError("Выходной черновик совпадает с входным файлом. Выберите другую папку.")
    output.mkdir(parents=True, exist_ok=True)
    draft.write_text(marp_markdown(slides), encoding="utf-8")
    if markdown_only:
        return draft, len(slides)
    pptx = output / (stem + ".pptx")
    regenerated = pptx.exists()
    exported = export_files(draft, output, command, pdf)
    return pptx, len(slides)


def marp_command(override=None):
    # Invoke the JS entry point directly: works on Windows without .cmd/shell quoting.
    entry = ROOT / "node_modules/@marp-team/marp-cli/marp-cli.js"
    if override:
        path = Path(override).resolve()
        if path.suffix == ".js":
            return ["node", str(path)]
        return [str(path)]
    if entry.is_file():
        return ["node", str(entry)]
    binary = shutil.which("marp")
    if binary and not binary.lower().endswith((".cmd", ".bat")):
        return [binary]
    raise ValueError("Marp CLI не найден. Выполните npm ci в каталоге проекта.")


def export_files(draft, output, command, pdf=False):
    stem = draft.name.removesuffix(".marp.md")
    target = output / (stem + ".pptx")
    subprocess.run(command + ["--pptx", "--pptx-editable", str(draft), "-o", str(target)], check=True)
    if not target.is_file() or not zipfile.is_zipfile(target):
        raise ValueError("Marp не создал корректный PPTX")
    artifacts = {"pptx": target}
    if pdf:
        target = output / (stem + ".pdf")
        subprocess.run(command + ["--pdf", str(draft), "-o", str(target)], check=True)
        if not target.is_file() or not target.read_bytes().startswith(b"%PDF"):
            raise ValueError("Marp не создал корректный PDF")
        artifacts["pdf"] = target
    return artifacts


def main(argv=None):
    parser = argparse.ArgumentParser(description="Markdown → Marp → редактируемый PPTX")
    parser.add_argument("plan", nargs="?", type=Path)
    parser.add_argument("--plan", dest="plan_option", type=Path)
    parser.add_argument("-o", "--output", type=Path, default=Path("out"))
    parser.add_argument("--markdown-only", action="store_true", help="Создать только Marp Markdown")
    parser.add_argument("--marp", help="Путь к Marp или marp-cli.js")
    parser.add_argument("--pdf", action="store_true", help="Дополнительно создать PDF")
    args = parser.parse_args(argv)
    if bool(args.plan) == bool(args.plan_option):
        parser.error("Укажите один входной файл: позиционно или через --plan")
    try:
        command = [] if args.markdown_only else marp_command(args.marp)
        result, count = generate(args.plan or args.plan_option, args.output, command, pdf=args.pdf, markdown_only=args.markdown_only)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 1
    print(f"Готово: {result} ({count} слайдов).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
