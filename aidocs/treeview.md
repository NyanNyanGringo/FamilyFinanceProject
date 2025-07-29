# TreeView - Структура проекта FamilyFinanceProject

Этот документ содержит полную структуру проекта с информацией о файлах, классах и функциях.
Обновляется автоматически после внесения изменений в проект.

**Последнее обновление:** 2025-07-27 12:32:00
**Версия скрипта:** v002

## Структура проекта

```
📁 FamilyFinanceProject/
    ├── 📄 `.gitignore`
    ├── 📄 `.gitpmoji.env`
    ├── 📄 `README.md`
    ├── 📄 `config.py`
    │     📍 Путь: `config.py`
    ├── 📄 `conversationbot`
    ├── 📄 `gpt.sh`
    ├── 📄 `install.sh`
    ├── 📄 `prepare-commit-msg.sh`
    ├── 📄 `pyproject.toml`
    ├── 📄 `run_server.py`
    │     📍 Путь: `run_server.py`
    ├── 📄 `test.py` - 1 функций
    │     📍 Путь: `test.py`
    │     ⚡ `parse_ftp_log(file_path)` (строка 5)
    │       📝 Parse an FTP log file to generate upload statistics by user.
    ├── 📁 **aidocs/** `/Users/user/github/FamilyFinanceProject/aidocs`
    │   ├── 📄 `how_to_tree_view.md`
    │   ├── 📄 `prd.md`
    │   └── 📄 `treeview.md`
    ├── 📁 **lib/** `/Users/user/github/FamilyFinanceProject/lib`
    │   └── 📁 **utilities/** `/Users/user/github/FamilyFinanceProject/lib/utilities`
    │       ├── 📄 `date_utilities.py` - 1 функций
    │       │     📍 Путь: `lib/utilities/date_utilities.py`
    │       │     ⚡ `get_google_sheets_current_date()` (строка 4)
    │       │       📝 Возвращает текущую дату в формате Google Sheets (количество дней с 30 декабря...
    │       ├── 📄 `ffmpeg_utilities.py` - 1 функций
    │       │     📍 Путь: `lib/utilities/ffmpeg_utilities.py`
    │       │     ⚡ `convert_oga_to_wav(input_file)` (строка 7)
    │       │       📝 :return: path to .wav file
    │       ├── 📄 `google_utilities.py` - 9 класс(ов), 7 функций
    │       │     📍 Путь: `lib/utilities/google_utilities.py`
    │       │     ⚡ `_authenticate_with_google()` (строка 48)
    │       │       📝 Аутентифицирует пользователя с помощью Google OAuth и возвращает объект учётн...
    │       │     ⚡ `_get_sheet_ids()` (строка 86)
    │       │       📝 Получает идентификаторы всех листов в Google Spreadsheet.
    │       │     ⚡ `get_values(cell_range, transform_to_single_list=False)` (строка 333)
    │       │       📝 Получает значения из Google Sheets по указанному диапазону.
    │       │     ⚡ `get_insert_row_above_request(list_name, insert_above_row)` (строка 362)
    │       │       📝 Создает запрос для вставки новой строки в Google Sheets.
    │       │     ⚡ `get_update_cells_request(list_name, values_to_update, row_index=6, column_index=0)` (строка 399)
    │       │       📝 Создает запрос для обновления ячеек в Google Sheets.
    │       │     ⚡ `get_values_to_update_for_request(request_data)` (строка 424)
    │       │       📝 Формирует список значений для обновления в Google Sheets на основе данных зап...
    │       │     ⚡ `insert_and_update_row_batch_update(request_data)` (строка 472)
    │       │       📝 Выполняет пакетное обновление Google Sheets: вставляет новую строку и обновля...
    │       │     🏛️ `_GoogleBaseEnumClass`(Enum) (строка 117)
    │       │       📝 Базовый класс для перечислений Google с дополнительными методами.
    │       │       └─ `__str__(self)` (строка 121) [magic]
    │       │       └─ `values(cls)` (строка 125) [@classmethod]
    │       │       └─ `get_item(cls, value)` (строка 129) [@classmethod]
    │       │     🏛️ `Category` (строка 136)
    │       │       📝 Класс для работы с категориями расходов, доходов и счетов.
    │       │       └─ `__init__(self)` (строка 145) [magic]
    │       │       └─ `get_expenses(cls)` (строка 150) [@classmethod]
    │       │       └─ `get_incomes(cls)` (строка 155) [@classmethod]
    │       │       └─ `get_accounts(cls)` (строка 160) [@classmethod]
    │       │       └─ `_update(cls)` (строка 165) [@classmethod]
    │       │     🏛️ `Formulas`(str, _GoogleBaseEnumClass) (строка 180)
    │       │       📝 Класс-строка для хранения формул Google Tables, используемых в проекте.
    │       │     🏛️ `OperationTypes`(str, _GoogleBaseEnumClass) (строка 246)
    │       │       📝 Перечисление типов операций: расходы, переводы, корректировки, доходы.
    │       │     🏛️ `ListName`(str, _GoogleBaseEnumClass) (строка 256)
    │       │       📝 Перечисление названий листов для разных типов операций.
    │       │     🏛️ `Status`(str, _GoogleBaseEnumClass) (строка 265)
    │       │       📝 Перечисление статусов операции: подтверждена, запланирована.
    │       │     🏛️ `TransferType`(str, _GoogleBaseEnumClass) (строка 273)
    │       │       📝 Перечисление типов переводов: перевод, корректировка.
    │       │     🏛️ `ConfigRange`(str, _GoogleBaseEnumClass) (строка 281)
    │       │       📝 Перечисление диапазонов ячеек для конфигурации Google Sheets.
    │       │     🏛️ `RequestData`(BaseModel) (строка 291)
    │       │       📝 Дата-класс для хранения данных запроса к Google Sheets.
    │       │       └─ `validate_data(self)` (строка 307)
    │       ├── 📄 `log_utilities.py` - 1 функций
    │       │     📍 Путь: `lib/utilities/log_utilities.py`
    │       │     ⚡ `get_logger(name='main')` (строка 5)
    │       │       📝 Создаёт и возвращает логгер с заданным именем.
    │       ├── 📄 `openai_utilities.py` - 4 класс(ов), 11 функций
    │       │     📍 Путь: `lib/utilities/openai_utilities.py`
    │       │     ⚡ `text2text(prompt, model='gpt-4o-mini')` (строка 24)
    │       │       📝 Отправляет текстовый запрос в OpenAI и возвращает ответ.
    │       │     ⚡ `audio2text(audio_path, prompt='')` (строка 49)
    │       │       📝 Преобразует аудиофайл в текст с помощью OpenAI Whisper.
    │       │     ⚡ `audio2text_for_finance(audio_path)` (строка 73)
    │       │       📝 Преобразует аудиофайл в текст с финансовым контекстом для FamilyFinanceProject.
    │       │     ⚡ `_get_adjustment_response_format()` (строка 94)
    │       │     ⚡ `_get_transfer_response_format()` (строка 163)
    │       │     ⚡ `_get_expenses_response_format()` (строка 252)
    │       │     ⚡ `_get_incomes_response_format()` (строка 335)
    │       │     ⚡ `_get_finance_operation_response_format()` (строка 416)
    │       │     ⚡ `_get_finance_operation_message(user_message)` (строка 489)
    │       │     ⚡ `_get_basic_message(user_message)` (строка 520)
    │       │     ⚡ `request_data(request_builder)` (строка 598)
    │       │       📝 Отправляет запрос к OpenAI API и возвращает ответ в формате JSON.
    │       │     🏛️ `MessageRequest` (строка 549)
    │       │       📝 Класс для формирования сообщений-запросов к OpenAI.
    │       │       └─ `__init__(self, user_message)` (строка 553) [magic]
    │       │     🏛️ `ResponseFormat` (строка 558)
    │       │       📝 Класс для хранения форматов ответов для разных типов операций.
    │       │       └─ `__init__(self)` (строка 562) [magic]
    │       │     🏛️ `Model` (строка 571)
    │       │       📝 Класс с названиями моделей OpenAI.
    │       │     🏛️ `RequestBuilder`(BaseModel) (строка 584)
    │       │       📝 Дата-класс для построения запроса к OpenAI.
    │       ├── 📄 `os_utilities.py` - 1 класс(ов), 5 функций
    │       │     📍 Путь: `lib/utilities/os_utilities.py`
    │       │     ⚡ `get_voice_messages_path(create=False)` (строка 12)
    │       │       📝 Возвращает путь к папке с голосовыми сообщениями. Создаёт папку при необходим...
    │       │     ⚡ `get_ffmpeg_executable_path()` (строка 30)
    │       │       📝 Возвращает путь к исполняемому файлу ffmpeg в зависимости от ОС.
    │       │     ⚡ `get_vosk_model_path()` (строка 50)
    │       │       📝 Возвращает путь к модели Vosk. Бросает ошибку, если модель не найдена.
    │       │     ⚡ `get_google_filepath(auth_type)` (строка 74)
    │       │       📝 Возвращает путь к файлу авторизации Google по типу.
    │       │     ⚡ `_get_root_path()` (строка 90)
    │       │       📝 Возвращает корневой путь проекта.
    │       │     🏛️ `GoogleAuthType`(enum.Enum) (строка 65)
    │       │       📝 Перечисление типов файлов авторизации Google.
    │       ├── 📄 `telegram_utilities.py`
    │       │     📍 Путь: `lib/utilities/telegram_utilities.py`
    │       └── 📄 `vosk_utilities.py` - 1 функций
    │             📍 Путь: `lib/utilities/vosk_utilities.py`
    │             ⚡ `audio2text(wav_audio_file, frames=4000)` (строка 18)
    │               📝 Преобразует аудиофайл в текст с помощью модели Vosk.
    ├── 📁 **models/** `/Users/user/github/FamilyFinanceProject/models`
    │   └── 📄 `.gitkeep`
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
        ├── 📄 `server.py` - 1 класс(ов), 9 функций
        │     📍 Путь: `src/server.py`
        │     ⚡ `replace_last_string(original_text, text_to_add)` (строка 44)
        │       📝 Заменяет последнюю строку в тексте на новую строку.
        │     ⚡ `format_json_to_telegram_text(json)` (строка 88)
        │       📝 Форматирует JSON-словарь в текст для Telegram.
        │     ⚡ `is_text_has_status(text)` (строка 105)
        │       📝 Проверяет, есть ли в тексте строка, начинающаяся с "Статус: ".
        │     ⚡ `remove_status_in_text(text)` (строка 119)
        │       📝 Удаляет строку со статусом из текста, если она существует и находится в после...
        │     ⚡ `set_status_to_text(text, status)` (строка 138)
        │       📝 Устанавливает новый статус в текст. Если статус уже есть, заменяет его.
        │     ⚡ `get_reply_keyboard_markup(use_confirm_button=True, use_reject_button=True)` (строка 210)
        │       📝 Создаёт клавиатуру для Telegram с двумя кнопками: "Подтвердить" и "Отменить".
        │     ⚡ `get_response_format_according_to_operation_type(operation_type)` (строка 240)
        │       📝 Возвращает формат ответа для указанного типа операции.
        │     ⚡ `clarify_request_message(request_message)` (строка 262)
        │       📝 Валидирует и корректирует значения в сообщении запроса.
        │     ⚡ `run()` (строка 480)
        │     🏛️ `Audio2TextModels` (строка 33)
        │       📝 Класс для выбора модели преобразования аудио в текст.
        └── 📁 **agents/** `/Users/user/github/FamilyFinanceProject/src/agents`
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

- **Всего файлов:** 25
- **Python файлов:** 13
- **Строк кода:** 3,679
- **Классов:** 16
- **Функций:** 38
- **Методов:** 23

### Распределение файлов по типам:
- `.py`: 13 файлов
- `.md`: 4 файлов
- `.sh`: 3 файлов
- `.env`: 1 файлов
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
