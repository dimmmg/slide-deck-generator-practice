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

    def test_editable_pptx(self):
        with tempfile.TemporaryDirectory() as d:
            plan=Path(d)/'lesson.md';plan.write_text('# Тема\nТекст',encoding='utf-8')
            with patch('generate_slides.subprocess.run', side_effect=fake_marp) as run:
                pptx,count=app.generate(plan,Path(d)/'out',['node','marp.js'])
            self.assertTrue(pptx.exists())
            self.assertEqual(count,1)
            self.assertIn('--pptx-editable',run.call_args.args[0])

    def test_windows_entry(self):
        with patch('generate_slides.Path.is_file', return_value=True):
            command=app.marp_command()
        self.assertEqual(command[0],'node')
        self.assertTrue(command[1].endswith('marp-cli.js'))

    def test_path_with_spaces(self):
        with tempfile.TemporaryDirectory(prefix='slides space ') as d:
            plan=Path(d)/'мой урок.md';plan.write_text('# Тема\nТекст',encoding='utf-8')
            with patch('generate_slides.subprocess.run',side_effect=fake_marp) as run:
                app.generate(plan,Path(d)/'output dir',['node','marp.js'])
            self.assertIn(str(Path(d)/'output dir'/'мой урок.marp.md'),run.call_args.args[0])

    def test_pdf_export(self):
        with tempfile.TemporaryDirectory() as d:
            plan=Path(d)/'lesson.md';plan.write_text('# Урок\nТекст',encoding='utf-8')
            with patch('generate_slides.subprocess.run',side_effect=fake_marp) as run:
                app.generate(plan,Path(d)/'out',['marp'],pdf=True)
            self.assertEqual(run.call_count,2)
            self.assertTrue((Path(d)/'out/lesson.pdf').read_bytes().startswith(b'%PDF'))

    def test_failed_converter_cli(self):
        with tempfile.TemporaryDirectory() as d:
            plan=Path(d)/'lesson.md';plan.write_text('# Урок\nТекст',encoding='utf-8')
            stdout=io.StringIO();stderr=io.StringIO()
            with patch('generate_slides.marp_command',return_value=['marp']), patch('generate_slides.subprocess.run',side_effect=subprocess.CalledProcessError(1,'marp')), contextlib.redirect_stdout(stdout),contextlib.redirect_stderr(stderr):
                result=app.main(['--plan',str(plan),'--output',str(Path(d)/'out')])
            self.assertEqual(result,1)
            self.assertNotIn('Готово',stdout.getvalue())
            self.assertIn('Ошибка',stderr.getvalue())

    def test_missing_input_file(self):
        with tempfile.TemporaryDirectory() as d, contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(app.main(['--plan',str(Path(d)/'missing.md'),'--markdown-only']),1)
