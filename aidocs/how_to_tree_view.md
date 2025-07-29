

## Description

treeview.md is an automatically generated document that provides a complete structure of the project.


## How To Use

After code changes, you should trigger the generation of treeview.md using:
```
poetry run python scripts/generate_treeview.py
```

Find and read scripts/treeview.md to understand project structure easily.


## Script ignores

* `.git`, `__pycache__`, `.venv`, `venv`, `.idea`
* `node_modules`, `.pytest_cache`, `.coverage`
* `ffmpeg`, `voice_messages`, `google_credentials`
* `.DS_Store`, `*.pyc`, `.env`, and other system files
* Temporary files: `*.tmp`, `*.temp`, `*.cache`, `*.bak`


## Supported Languages

The script is ready to analyze files in the following languages (currently full support only for Python):
Python, JavaScript, TypeScript, Java, C/C++, C#, Go, Rust, PHP, Ruby, Swift, Kotlin, Scala, R, Objective-C, Fortran, Julia, Lua
poetry run python generate\_treeview\.py
