

## Описание

`aidocs/treeview.md` — это автоматически генерируемый документ, который содержит полную структуру проекта.


## Как использовать

После изменений в коде обновите `aidocs/treeview.md` командой:
```
poetry run python scripts/generate_treeview.py
```

Откройте и прочитайте `aidocs/treeview.md`, чтобы быстро разобраться в структуре проекта.


## Что игнорирует скрипт

* `.git`, `__pycache__`, `.venv`, `venv`, `.idea`
* `node_modules`, `.pytest_cache`, `.coverage`
* `ffmpeg`, `voice_messages`, `google_credentials`
* `.DS_Store`, `*.pyc`, `.env` и другие системные файлы
* Временные файлы: `*.tmp`, `*.temp`, `*.cache`, `*.bak`


## Поддерживаемые языки

Скрипт готов анализировать файлы на следующих языках (в данный момент полноценная поддержка реализована только для Python):
Python, JavaScript, TypeScript, Java, C/C++, C#, Go, Rust, PHP, Ruby, Swift, Kotlin, Scala, R, Objective-C, Fortran, Julia, Lua
