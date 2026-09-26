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
            self.assertIn(str((Path(d)/'output dir'/'мой урок.marp.md').resolve()),run.call_args.args[0])

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

    def test_invalid_pptx_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            draft=Path(d)/'lesson.marp.md';draft.write_text('# Тема',encoding='utf-8')
            def bad(command,check):
                Path(command[-1]).write_text('invalid',encoding='utf-8')
            with patch('generate_slides.subprocess.run',side_effect=bad),self.assertRaises(ValueError):
                app.export_files(draft,Path(d),['marp'])

    def test_invalid_plans(self):
        for source in ['', '---\n','Просто текст','# Тема\n```py\nx=1','---\nmarp: true\n---\n# Тема']:
            with self.subTest(source=source),self.assertRaises(ValueError):
                app.parse_plan(source)

    def test_todo_rules(self):
        self.assertIn('TODO: добавить тезисы',app.marp_markdown(app.parse_plan('# Тема')))
        self.assertIn('TODO: добавить или проверить формулу',app.marp_markdown(app.parse_plan('# Формулы\nТеорема')))
        self.assertNotIn('TODO: проверить, нужен ли пример',app.marp_markdown(app.parse_plan('# Тема\nПример: 1')))

    def test_conflicting_input_arguments(self):
        with contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit) as cm:
            app.main(['one.md','--plan','two.md','--markdown-only'])
        self.assertEqual(cm.exception.code,2)

    def test_source_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            plan=Path(d)/'lesson.md';source='# Тема\nТезис';plan.write_text(source,encoding='utf-8')
            __import__('os').link(plan,Path(d)/'lesson.marp.md')
            with self.assertRaises(ValueError):app.generate(plan,Path(d),[],markdown_only=True)
            self.assertEqual(plan.read_text(encoding='utf-8'),source)

    def test_metadata_and_regeneration(self):
        with tempfile.TemporaryDirectory() as d:
            plan=Path(d)/'lesson.md';out=Path(d)/'out';plan.write_bytes(b'\xef\xbb\xbf# Topic\nText')
            with patch('generate_slides.subprocess.run',side_effect=fake_marp):
                app.generate(plan,out,['marp'],actor='student',pdf=True)
                app.generate(plan,out,['marp'],actor='student',pdf=True)
            metadata=json.loads((out/'lesson.metadata.json').read_text(encoding='utf-8'))
            self.assertEqual(metadata['plan_sha256'],hashlib.sha256(plan.read_bytes()).hexdigest())
            self.assertEqual(metadata['sha256']['pptx'],hashlib.sha256((out/'lesson.pptx').read_bytes()).hexdigest())
            events=[json.loads(line) for line in (out/'events.xapi.jsonl').read_text(encoding='utf-8').splitlines()]
            self.assertEqual(len(events),2)
            self.assertTrue(events[0]['verb']['id'].endswith(':generated'))
            self.assertTrue(events[1]['verb']['id'].endswith(':regenerated'))
            self.assertNotEqual(events[0]['id'],events[1]['id'])

    def test_lesson_id_must_be_uri(self):
        with contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
            app.main(['x.md','--lesson-id','not a uri'])

    def test_pdf_failure_keeps_old_outputs(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);plan=root/'lesson.md';out=root/'out';out.mkdir()
            plan.write_text('# Урок\nТекст',encoding='utf-8')
            (out/'lesson.pptx').write_bytes(b'old pptx');(out/'lesson.pdf').write_bytes(b'old pdf')
            def fail_pdf(command,check):
                if '--pdf' in command:raise subprocess.CalledProcessError(1,'marp')
                fake_marp(command,check)
            with patch('generate_slides.subprocess.run',side_effect=fail_pdf),self.assertRaises(subprocess.CalledProcessError):
                app.generate(plan,out,['marp'],pdf=True)
            self.assertEqual((out/'lesson.pptx').read_bytes(),b'old pptx')
            self.assertEqual((out/'lesson.pdf').read_bytes(),b'old pdf')
            self.assertFalse((out/'events.xapi.jsonl').exists())

    def test_replacement_failure_rolls_back(self):
        original=Path.replace
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);plan=root/'lesson.md';out=root/'out';out.mkdir()
            plan.write_text('# Урок\nТекст',encoding='utf-8')
            (out/'lesson.pptx').write_bytes(b'old pptx');(out/'lesson.pdf').write_bytes(b'old pdf')
            def fail_once(source,destination):
                if source.name=='lesson.pdf' and source.parent!=out:raise OSError('controlled failure')
                return original(source,destination)
            with patch('generate_slides.subprocess.run',side_effect=fake_marp),patch.object(Path,'replace',fail_once),self.assertRaises(OSError):
                app.generate(plan,out,['marp'],pdf=True)
            self.assertEqual((out/'lesson.pptx').read_bytes(),b'old pptx')
            self.assertEqual((out/'lesson.pdf').read_bytes(),b'old pdf')
            self.assertFalse((out/'events.xapi.jsonl').exists())

    def test_new_partial_output_removed_on_failure(self):
        original=Path.replace
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);plan=root/'lesson.md';out=root/'out'
            plan.write_text('# Урок\nТекст',encoding='utf-8')
            def fail_pdf(source,destination):
                if source.name=='lesson.pdf':raise OSError('controlled failure')
                return original(source,destination)
            with patch('generate_slides.subprocess.run',side_effect=fake_marp),patch.object(Path,'replace',fail_pdf),self.assertRaises(OSError):
                app.generate(plan,out,['marp'],pdf=True)
            self.assertFalse((out/'lesson.pptx').exists())
            self.assertFalse((out/'events.xapi.jsonl').exists())

    def test_extended_example(self):
        source=(Path(__file__).resolve().parents[1]/'examples/markdown-cases.md').read_text(encoding='utf-8')
        slides=app.parse_plan(source)
        self.assertEqual(len(slides),3)
        rendered=app.marp_markdown(slides)
        for part in ['Console.WriteLine', 'Вложенный тезис', 'TODO: добавить тезисы']:
            self.assertIn(part,rendered)
