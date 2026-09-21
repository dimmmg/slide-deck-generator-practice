# Установка и запуск в Windows

Установите Python 3.13, Node.js LTS, LibreOffice и Chrome либо Edge.
После установки откройте новое окно PowerShell. Проверьте python --version,
node --version, npm.cmd --version. Если Node не найден при существующем node.exe:
`$env:Path = "C:\Program Files\nodejs;" + $env:Path`.
В папке проекта выполните npm.cmd ci и python -m unittest discover -s tests -v.
Запуск: python generate_slides.py --plan examples/lesson.md --output out
Marp editable PPTX — экспериментальная возможность. Проверьте редактирование
текста в PowerPoint/LibreOffice; точное совпадение оформления не гарантируется.
Для кириллицы в PowerShell используйте Get-Content -Encoding UTF8.
--marp принимает путь к marp-cli.js или исполняемому файлу, не к .cmd-обёртке.
