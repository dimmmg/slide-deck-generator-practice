# Slide deck generator

Учебный проект Горбовского Дмитрия Олеговича, 14321-ДБ, 3 курс.
Генератор помогает преподавателю превратить план занятия в черновик презентации.
Вход — Markdown с заголовками и разделителями. Целевой результат — редактируемый
PPTX через Marp, опционально PDF, локальные метаданные и xAPI JSONL.
Интерфейс — Python CLI. Сложные макеты, веб-интерфейс и удалённый LRS не входят в MVP.
Ранние учебные версии вводят эти возможности постепенно; состав этапа указан в STEP.md снаружи проекта.

## Быстрый запуск

```powershell
npm.cmd ci
python generate_slides.py --plan examples/lesson.md --output out
```

[Установка в Windows](docs/windows.md).

## Проверка и документация

python -m unittest discover -s tests -v

--pdf добавляет PDF; --markdown-only создаёт только черновик.
--actor задаёт псевдоним, --lesson-id — URI занятия; журнал всегда локальный.

[Архитектура](docs/architecture.md), [сценарии](docs/use-cases.md),
[приёмка](docs/acceptance.md), [ограничения](docs/reliability.md),
[подготовка релиза](docs/release.md).
