import contextlib
import io
import json
import hashlib
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
import generate_slides as app

def fake_marp(command, check):
    target = Path(command[command.index('-o') + 1])
    if target.suffix == '.pptx':
        with zipfile.ZipFile(target, 'w') as z:
            z.writestr('ppt/presentation.xml', '<presentation/>')
    else:
        target.write_bytes(b'%PDF-1.7 test')

class GeneratorTests(unittest.TestCase):
    def test_help(self):
        with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as cm:
            app.main(['--help'])
        self.assertEqual(cm.exception.code, 0)

    def test_missing_argument(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as cm:
            app.main([])
        self.assertEqual(cm.exception.code, 2)

    def test_markdown_content(self):
        source = '# C#\n- [Источник](https://example.org)\n  - Вложенный тезис\n```cs\n# код\n---\n```\n---\n## Итог ##\nТекст'
        slides = app.parse_plan(source)
        self.assertEqual(len(slides), 2)
        self.assertEqual(slides[0][0], 'C#')
        self.assertEqual(slides[1][0], 'Итог')
        for part in ['  - Вложенный тезис', '# код', '[Источник](https://example.org)']:
            self.assertIn(part, app.marp_markdown(slides))

    def test_markdown_only_cli(self):
        with tempfile.TemporaryDirectory() as d:
            plan = Path(d)/'lesson.md'; out = Path(d)/'out'
            plan.write_text('# Тема\n- Тезис', encoding='utf-8')
            with contextlib.redirect_stdout(io.StringIO()):
                result = app.main(['--plan', str(plan), '--output', str(out), '--markdown-only'])
            self.assertEqual(result, 0)
            self.assertIn('# Тема', (out/'lesson.marp.md').read_text(encoding='utf-8'))
            self.assertFalse((out/'lesson.pptx').exists())
