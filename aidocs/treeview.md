# TreeView - Структура проекта FamilyFinanceProject

Этот документ содержит полную структуру проекта с информацией о файлах, классах и функциях.
Обновляется автоматически после внесения изменений в проект.

**Последнее обновление:** 2026-01-14 14:49:56
**Версия скрипта:** v002

## Структура проекта

```
📁 FamilyFinanceProject/
    ├── 📄 `.dockerignore`
    ├── 📄 `.gitignore`
    ├── 📄 `.google_service_account_credentials.json`
    ├── 📄 `AGENTS.md`
    ├── 📄 `CLAUDE.md`
    ├── 📄 `Dockerfile`
    ├── 📄 `README-Docker.md`
    ├── 📄 `README.md`
    ├── 📄 `config.py`
    │     📍 Путь: `config.py`
    ├── 📄 `deploy-simple.sh`
    ├── 📄 `docker-compose.dev.yml`
    ├── 📄 `docker-compose.yml`
    ├── 📄 `pyproject.toml`
    ├── 📄 `pyrightconfig.json`
    ├── 📄 `run_server.py`
    │     📍 Путь: `run_server.py`
    ├── 📄 `test.py`
    │     📍 Путь: `test.py`
    ├── 📄 `test2.py` - 5 функций
    │     📍 Путь: `test2.py`
    │     ⚡ `read_expenses_sheet()` (строка 19)
    │       📝 Read all data from the expenses sheet.
    │     ⚡ `parse_expense_record(row, headers)` (строка 42)
    │       📝 Parse a single expense record into a dictionary.
    │     ⚡ `analyze_expenses_by_category(expenses, category, start_date=None, end_date=None)` (строка 62)
    │       📝 Analyze expenses for a specific category within a date range.
    │     ⚡ `get_expense_summary(category=None, months_back=None)` (строка 133)
    │       📝 Get a compact summary of expenses for a category.
    │     ⚡ `main()` (строка 240)
    │       📝 Main function to demonstrate expense data extraction and analysis.
    ├── 📁 **aidocs/** `/Users/user/github/FamilyFinanceProject/aidocs`
    │   ├── 📄 `about_google_sheet.md`
    │   ├── 📄 `architecture.md`
    │   ├── 📄 `code_style.md`
    │   ├── 📄 `commands.md`
    │   ├── 📄 `how_to_tree_view.md`
    │   ├── 📄 `infrastructure.md`
    │   ├── 📄 `prd.md`
    │   ├── 📄 `safety.md`
    │   ├── 📄 `tests.md`
    │   ├── 📄 `treeview.md`
    │   ├── 📁 **sessions/** `/Users/user/github/FamilyFinanceProject/aidocs/sessions`
    │   │   ├── 📄 `session_0000.md`
    │   │   ├── 📄 `session_0001.md`
    │   │   ├── 📄 `session_0002.md`
    │   │   ├── 📄 `session_0003.md`
    │   │   ├── 📄 `session_0004.md`
    │   │   ├── 📄 `session_0005.md`
    │   │   ├── 📄 `session_0006.md`
    │   │   ├── 📄 `session_0007.md`
    │   │   ├── 📄 `session_0008.md`
    │   │   └── 📄 `session_0009.md`
    │   └── 📁 **tasks/** `/Users/user/github/FamilyFinanceProject/aidocs/tasks`
    ├── 📁 **docker/** `/Users/user/github/FamilyFinanceProject/docker`
    │   ├── 📄 `entrypoint.sh`
    │   └── 📄 `healthcheck.sh`
    ├── 📁 **lib/** `/Users/user/github/FamilyFinanceProject/lib`
    │   ├── 📄 `__init__.py`
    │   │     📍 Путь: `lib/__init__.py`
    │   └── 📁 **utilities/** `/Users/user/github/FamilyFinanceProject/lib/utilities`
    │       ├── 📄 `__init__.py`
    │       │     📍 Путь: `lib/utilities/__init__.py`
    │       ├── 📄 `date_utilities.py` - 1 функций
    │       │     📍 Путь: `lib/utilities/date_utilities.py`
    │       │     ⚡ `get_google_sheets_current_date()` (строка 4)
    │       │       📝 Возвращает текущую дату в формате Google Sheets (количество дней с 30 декабря...
    │       ├── 📄 `ffmpeg_utilities.py` - 1 функций
    │       │     📍 Путь: `lib/utilities/ffmpeg_utilities.py`
    │       │     ⚡ `convert_oga_to_wav(input_file)` (строка 7)
    │       │       📝 :return: path to .wav file
    │       ├── 📄 `google_utilities.py` - 9 класс(ов), 11 функций
    │       │     📍 Путь: `lib/utilities/google_utilities.py`
    │       │     ⚡ `_authenticate_with_google()` (строка 30)
    │       │       📝 Аутентифицирует пользователя с помощью Google Service Account и возвращает об...
    │       │     ⚡ `_get_sheet_ids()` (строка 47)
    │       │       📝 Получает идентификаторы всех листов в Google Spreadsheet.
    │       │     ⚡ `get_values(cell_range, transform_to_single_list=False)` (строка 297)
    │       │       📝 Получает значения из Google Sheets по указанному диапазону.
    │       │     ⚡ `get_insert_row_above_request(list_name, insert_above_row)` (строка 326)
    │       │       📝 Создает запрос для вставки новой строки в Google Sheets.
    │       │     ⚡ `get_update_cells_request(list_name, values_to_update, row_index=6, column_index=0)` (строка 363)
    │       │       📝 Создает запрос для обновления ячеек в Google Sheets.
    │       │     ⚡ `get_values_to_update_for_request(request_data)` (строка 388)
    │       │       📝 Формирует список значений для обновления в Google Sheets на основе данных зап...
    │       │     ⚡ `delete_row_by_telegram_id(list_name, telegram_message_id)` (строка 457)
    │       │       📝 Удаляет строку из Google Sheets по Telegram message ID.
    │       │     ⚡ `insert_and_update_row_batch_update(request_data)` (строка 529)
    │       │       📝 Выполняет пакетное обновление Google Sheets: вставляет новую строку и обновля...
    │       │     ⚡ `get_memories()` (строка 562)
    │       │       📝 Получает список сохранённых воспоминаний из ячейки A1 листа #memory.
    │       │     ⚡ `add_memory(memory_text)` (строка 584)
    │       │       📝 Добавляет новое воспоминание в ячейку A1 листа #memory.
    │       │     ⚡ `delete_memory(memory_index)` (строка 620)
    │       │       📝 Удаляет воспоминание по индексу из ячейки A1 листа #memory.
    │       │     🏛️ `_GoogleBaseEnumClass`(Enum) (строка 78)
    │       │       📝 Базовый класс для перечислений Google с дополнительными методами.
    │       │       └─ `__str__(self)` (строка 82) [magic]
    │       │       └─ `values(cls)` (строка 86) [@classmethod]
    │       │       └─ `get_item(cls, value)` (строка 90) [@classmethod]
    │       │     🏛️ `Category` (строка 97)
    │       │       📝 Класс для работы с категориями расходов, доходов и счетов.
    │       │       └─ `__init__(self)` (строка 106) [magic]
    │       │       └─ `get_expenses(cls)` (строка 111) [@classmethod]
    │       │       └─ `get_incomes(cls)` (строка 116) [@classmethod]
    │       │       └─ `get_accounts(cls)` (строка 121) [@classmethod]
    │       │       └─ `_update(cls)` (строка 126) [@classmethod]
    │       │     🏛️ `Formulas`(str, _GoogleBaseEnumClass) (строка 141)
    │       │       📝 Класс-строка для хранения формул Google Tables, используемых в проекте.
    │       │     🏛️ `OperationTypes`(str, _GoogleBaseEnumClass) (строка 207)
    │       │       📝 Перечисление типов операций: расходы, переводы, корректировки, доходы.
    │       │     🏛️ `ListName`(str, _GoogleBaseEnumClass) (строка 217)
    │       │       📝 Перечисление названий листов для разных типов операций.
    │       │     🏛️ `Status`(str, _GoogleBaseEnumClass) (строка 228)
    │       │       📝 Перечисление статусов операции: подтверждена, запланирована.
    │       │     🏛️ `TransferType`(str, _GoogleBaseEnumClass) (строка 236)
    │       │       📝 Перечисление типов переводов: перевод, корректировка.
    │       │     🏛️ `ConfigRange`(str, _GoogleBaseEnumClass) (строка 244)
    │       │       📝 Перечисление диапазонов ячеек для конфигурации Google Sheets.
    │       │     🏛️ `RequestData`(BaseModel) (строка 254)
    │       │       📝 Дата-класс для хранения данных запроса к Google Sheets.
    │       │       └─ `validate_data(self)` (строка 271)
    │       ├── 📄 `log_utilities.py` - 1 функций
    │       │     📍 Путь: `lib/utilities/log_utilities.py`
    │       │     ⚡ `get_logger(name='main')` (строка 5)
    │       │       📝 Создаёт и возвращает логгер с заданным именем.
    │       ├── 📄 `openai_utilities.py` - 4 класс(ов), 12 функций
    │       │     📍 Путь: `lib/utilities/openai_utilities.py`
    │       │     ⚡ `_get_memory_context()` (строка 24)
    │       │       📝 Получает контекст воспоминаний для добавления в системные сообщения.
    │       │     ⚡ `text2text(prompt, model='gpt-4o-mini')` (строка 44)
    │       │       📝 Отправляет текстовый запрос в OpenAI и возвращает ответ.
    │       │     ⚡ `audio2text(audio_path, prompt='')` (строка 69)
    │       │       📝 Преобразует аудиофайл в текст с помощью OpenAI Whisper.
    │       │     ⚡ `audio2text_for_finance(audio_path)` (строка 93)
    │       │       📝 Преобразует аудиофайл в текст с финансовым контекстом для FamilyFinanceProject.
    │       │     ⚡ `_get_adjustment_response_format()` (строка 114)
    │       │     ⚡ `_get_transfer_response_format()` (строка 183)
    │       │     ⚡ `_get_expenses_response_format()` (строка 272)
    │       │     ⚡ `_get_incomes_response_format()` (строка 355)
    │       │     ⚡ `_get_finance_operation_response_format()` (строка 436)
    │       │     ⚡ `_get_finance_operation_message(user_message)` (строка 509)
    │       │     ⚡ `_get_basic_message(user_message)` (строка 540)
    │       │     ⚡ `request_data(request_builder)` (строка 618)
    │       │       📝 Отправляет запрос к OpenAI API и возвращает ответ в формате JSON.
    │       │     🏛️ `MessageRequest` (строка 569)
    │       │       📝 Класс для формирования сообщений-запросов к OpenAI.
    │       │       └─ `__init__(self, user_message)` (строка 573) [magic]
    │       │     🏛️ `ResponseFormat` (строка 578)
    │       │       📝 Класс для хранения форматов ответов для разных типов операций.
    │       │       └─ `__init__(self)` (строка 582) [magic]
    │       │     🏛️ `Model` (строка 591)
    │       │       📝 Класс с названиями моделей OpenAI.
    │       │     🏛️ `RequestBuilder`(BaseModel) (строка 604)
    │       │       📝 Дата-класс для построения запроса к OpenAI.
    │       ├── 📄 `os_utilities.py` - 4 функций
    │       │     📍 Путь: `lib/utilities/os_utilities.py`
    │       │     ⚡ `get_voice_messages_path(create=False)` (строка 12)
    │       │       📝 Возвращает путь к папке с голосовыми сообщениями. Создаёт папку при необходим...
    │       │     ⚡ `get_ffmpeg_executable_path()` (строка 30)
    │       │       📝 Возвращает путь к исполняемому файлу ffmpeg в зависимости от ОС.
    │       │     ⚡ `get_vosk_model_path()` (строка 50)
    │       │       📝 Возвращает путь к модели Vosk. Бросает ошибку, если модель не найдена.
    │       │     ⚡ `_get_root_path()` (строка 68)
    │       │       📝 Возвращает корневой путь проекта.
    │       ├── 📄 `telegram_utilities.py`
    │       │     📍 Путь: `lib/utilities/telegram_utilities.py`
    │       └── 📄 `vosk_utilities.py` - 1 функций
    │             📍 Путь: `lib/utilities/vosk_utilities.py`
    │             ⚡ `audio2text(wav_audio_file, frames=4000)` (строка 18)
    │               📝 Преобразует аудиофайл в текст с помощью модели Vosk.
    ├── 📁 **scripts/** `/Users/user/github/FamilyFinanceProject/scripts`
    │   └── 📄 `generate_treeview.py` - 1 класс(ов), 1 функций
    │         📍 Путь: `scripts/generate_treeview.py`
    │         ⚡ `main()` (строка 488)
    │           📝 Главная функция.
    │         🏛️ `TreeViewGenerator` (строка 17)
    │           └─ `__init__(self, project_root)` (строка 18) [magic]
    │           └─ `should_ignore(self, path)` (строка 48)
    │           └─ `get_function_signature(self, node)` (строка 78)
    │           └─ `extract_python_structure(self, file_path)` (строка 118)
    │           └─ `_get_node_name(self, node)` (строка 191)
    │           └─ `_get_decorator_name(self, decorator)` (строка 202)
    │           └─ `build_tree(self, directory, prefix='', is_last=True)` (строка 213)
    │           └─ `generate_markdown(self)` (строка 330)
    │           └─ `_get_timestamp(self)` (строка 381)
    │           └─ `_generate_statistics(self)` (строка 386)
    │           └─ `generate(self, output_path)` (строка 462)
    │           └─ `_count_files(self)` (строка 476)
    └── 📁 **src/** `/Users/user/github/FamilyFinanceProject/src`
        └── 📄 `server.py` - 1 класс(ов), 11 функций
              📍 Путь: `src/server.py`
              ⚡ `replace_last_string(original_text, text_to_add)` (строка 56)
                📝 Заменяет последнюю строку в тексте на новую строку.
              ⚡ `format_json_to_telegram_text(json)` (строка 102)
                📝 Форматирует JSON-словарь в текст для Telegram.
              ⚡ `is_text_has_status(text)` (строка 119)
                📝 Проверяет, есть ли в тексте строка, начинающаяся с "Статус: ".
              ⚡ `remove_status_in_text(text)` (строка 133)
                📝 Удаляет строку со статусом из текста, если она существует и находится в после...
              ⚡ `set_status_to_text(text, status)` (строка 152)
                📝 Устанавливает новый статус в текст. Если статус уже есть, заменяет его.
              ⚡ `get_delete_button_keyboard(message_id)` (строка 294)
                📝 Создаёт клавиатуру с одной кнопкой "Удалить".
              ⚡ `get_delete_confirmation_keyboard(message_id)` (строка 310)
                📝 Создаёт клавиатуру для подтверждения удаления.
              ⚡ `get_reply_keyboard_markup(use_confirm_button=True, use_reject_button=True, message_id=None)` (строка 329)
                📝 Создаёт клавиатуру для Telegram с двумя кнопками: "Подтвердить" и "Отменить".
              ⚡ `get_response_format_according_to_operation_type(operation_type)` (строка 372)
                📝 Возвращает формат ответа для указанного типа операции.
              ⚡ `clarify_request_message(request_message)` (строка 394)
                📝 Валидирует и корректирует значения в сообщении запроса.
              ⚡ `run()` (строка 1083)
              🏛️ `Audio2TextModels` (строка 44)
                📝 Класс для выбора модели преобразования аудио в текст.
```

## Легенда

- 📁 - Директория
- 📄 - Файл
- 📍 - Путь к файлу
- ⚡ - Функция
- 🏛️ - Класс
- └─ - Метод класса
- 📝 - Описание (docstring)
- [async] - Асинхронная функция
- [@decorator] - Декоратор
- [magic] - Магический метод

## Статистика проекта

- **Всего файлов:** 51
- **Python файлов:** 16
- **Строк кода:** 5,889
- **Классов:** 15
- **Функций:** 48
- **Методов:** 23

### Распределение файлов по типам:
- `.md`: 24 файлов
- `.py`: 16 файлов
- `.sh`: 3 файлов
- `.json`: 2 файлов
- `.yml`: 2 файлов
- `.toml`: 1 файлов

## Поддерживаемые языки

Скрипт анализирует файлы следующих языков программирования:
Python, JavaScript, TypeScript, Java, C/C++, C#, Go, Rust, PHP, Ruby, Swift, Kotlin, Scala, R, Objective-C, Fortran, Julia, Lua

## Игнорируемые файлы и директории

Автоматически исключаются:
- Системные и временные файлы
- Директории виртуальных окружений
- Кэш и артефакты сборки
- Файлы конфигурации IDE
