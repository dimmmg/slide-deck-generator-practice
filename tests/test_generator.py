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
