# Локальная история

После успешного экспорта создаётся lesson.metadata.json и дописывается events.xapi.jsonl.
Первый запуск — generated, наличие предыдущего PPTX — regenerated.
Пример: --actor student --lesson-id urn:lesson:demo --mock-lrs.
--mock-lrs оставлен для совместимости с ТЗ: удалённого LRS и сетевой отправки нет.
Журнал содержит псевдоним, название занятия и URI файлов. Не добавляйте личные данные.
Get-Content out/events.xapi.jsonl -Encoding UTF8 показывает кириллицу в PowerShell.
SHA-256 считается по реальным байтам каждого файла, включая BOM исходного плана.
