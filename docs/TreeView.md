✅ TreeView.md успешно создан: /Users/user/github/FamilyFinanceProject/docs/TreeView.md
📊 Обработано 34 файлов

📌 Для автоматического обновления TreeView.md после изменений,
   запускайте: poetry run python generate_treeview.py
изменений в проект.

**Последнее обновление:** 2025-06-18 15:26:16
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
    ├── 📄 `generate_treeview.py` - 1 класс(ов), 1 функций
    │     📍 Путь: `generate_treeview.py`
    │     ⚡ `main()` (строка 488)
    │       📝 Главная функция.
    │     🏛️ `TreeViewGenerator` (строка 17)
    │       └─ `__init__(self, project_root)` (строка 18) [magic]
    │       └─ `should_ignore(self, path)` (строка 48)
    │       └─ `get_function_signature(self, node)` (строка 78)
    │       └─ `extract_python_structure(self, file_path)` (строка 118)
    │       └─ `_get_node_name(self, node)` (строка 191)
    │       └─ `_get_decorator_name(self, decorator)` (строка 202)
    │       └─ `build_tree(self, directory, prefix='', is_last=True)` (строка 213)
    │       └─ `generate_markdown(self)` (строка 330)
    │       └─ `_get_timestamp(self)` (строка 381)
    │       └─ `_generate_statistics(self)` (строка 386)
    │       └─ `generate(self, output_path)` (строка 462)
    │       └─ `_count_files(self)` (строка 476)
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
    ├── 📁 **docs/** `/Users/user/github/FamilyFinanceProject/docs`
    │   ├── 📄 `PRD.md`
    │   ├── 📄 `TreeView.md`
    │   ├── 📄 `treeview_usage.md`
    │   └── 📁 **session_01/** `/Users/user/github/FamilyFinanceProject/docs/session_01`
    │       └── 📄 `session_01.md`
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
    │       │     ⚡ `get_values(cell_range, transform_to_single_list=False)` (строка 334)
    │       │       📝 Получает значения из Google Sheets по указанному диапазону.
    │       │     ⚡ `get_insert_row_above_request(list_name, insert_above_row)` (строка 363)
    │       │       📝 Создает запрос для вставки новой строки в Google Sheets.
    │       │     ⚡ `get_update_cells_request(list_name, values_to_update, row_index=6, column_index=0)` (строка 400)
    │       │       📝 Создает запрос для обновления ячеек в Google Sheets.
    │       │     ⚡ `get_values_to_update_for_request(request_data)` (строка 425)
    │       │       📝 Формирует список значений для обновления в Google Sheets на основе данных зап...
    │       │     ⚡ `insert_and_update_row_batch_update(request_data)` (строка 488)
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
    │       │       └─ `validate_data(self)` (строка 308)
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
    └── 📁 **src/** `/Users/user/github/FamilyFinanceProject/src`
        ├── 📄 `agent_integration.py` - 1 класс(ов)
        │     📍 Путь: `src/agent_integration.py`
        │     🏛️ `AgentSystemIntegration` (строка 19)
        │       📝 Класс для интеграции агентов с существующей системой.
        │       └─ `__init__(self)` (строка 22) [magic]
        │       └─ `_setup_agents(self)` (строка 29)
        │       └─ `enable(self)` (строка 259)
        │       └─ `disable(self)` (строка 264)
        ├── 📄 `server.py` - 1 класс(ов), 9 функций
        │     📍 Путь: `src/server.py`
        │     ⚡ `replace_last_string(original_text, text_to_add)` (строка 47)
        │       📝 Заменяет последнюю строку в тексте на новую строку.
        │     ⚡ `format_json_to_telegram_text(json)` (строка 91)
        │       📝 Форматирует JSON-словарь в текст для Telegram.
        │     ⚡ `is_text_has_status(text)` (строка 108)
        │       📝 Проверяет, есть ли в тексте строка, начинающаяся с "Статус: ".
        │     ⚡ `remove_status_in_text(text)` (строка 122)
        │       📝 Удаляет строку со статусом из текста, если она существует и находится в после...
        │     ⚡ `set_status_to_text(text, status)` (строка 141)
        │       📝 Устанавливает новый статус в текст. Если статус уже есть, заменяет его.
        │     ⚡ `get_reply_keyboard_markup(use_confirm_button=True, use_reject_button=True)` (строка 213)
        │       📝 Создаёт клавиатуру для Telegram с двумя кнопками: "Подтвердить" и "Отменить".
        │     ⚡ `get_response_format_according_to_operation_type(operation_type)` (строка 243)
        │       📝 Возвращает формат ответа для указанного типа операции.
        │     ⚡ `clarify_request_message(request_message)` (строка 265)
        │       📝 Валидирует и корректирует значения в сообщении запроса.
        │     ⚡ `run()` (строка 515)
        │     🏛️ `Audio2TextModels` (строка 36)
        │       📝 Класс для выбора модели преобразования аудио в текст.
        └── 📁 **agents/** `/Users/user/github/FamilyFinanceProject/src/agents`
            ├── 📄 `__init__.py`
            │     📍 Путь: `src/agents/__init__.py`
            ├── 📄 `base.py` - 3 класс(ов)
            │     📍 Путь: `src/agents/base.py`
            │     🏛️ `AgentRequest` (строка 17)
            │       📝 Стандартизированный запрос к агенту.
            │       └─ `__post_init__(self)` (строка 25) [magic]
            │     🏛️ `AgentResponse` (строка 31)
            │       📝 Стандартизированный ответ от агента.
            │       └─ `__post_init__(self)` (строка 40) [magic]
            │     🏛️ `BaseAgent`(ABC) (строка 45)
            │       📝 Базовый класс для всех агентов.
            │       └─ `__init__(self, name)` (строка 48) [magic]
            │       └─ `create_error_response(self, error_message)` (строка 91)
            │       └─ `create_success_response(self, message, data=None)` (строка 108)
            ├── 📄 `expense.py` - 1 класс(ов)
            │     📍 Путь: `src/agents/expense.py`
            │     🏛️ `ExpenseAgent`(BaseAgent) (строка 14)
            │       📝 Агент для обработки операций расходов.
            │       └─ `__init__(self)` (строка 17) [magic]
            │       └─ `_validate_expense_data(self, expense_data)` (строка 98)
            │       └─ `_create_google_request(self, expense_data, message_id=None)` (строка 133)
            │       └─ `_format_success_message(self, expense_data)` (строка 154)
            ├── 📄 `income.py` - 1 класс(ов)
            │     📍 Путь: `src/agents/income.py`
            │     🏛️ `IncomeAgent`(BaseAgent) (строка 14)
            │       📝 Агент для обработки операций доходов.
            │       └─ `__init__(self)` (строка 17) [magic]
            │       └─ `_validate_income_data(self, income_data)` (строка 98)
            │       └─ `_create_google_request(self, income_data)` (строка 133)
            │       └─ `_format_success_message(self, income_data)` (строка 152)
            ├── 📄 `orchestrator.py` - 1 класс(ов)
            │     📍 Путь: `src/agents/orchestrator.py`
            │     🏛️ `MainOrchestrator`(BaseAgent) (строка 17)
            │       📝 Главный агент-диспетчер.
            │       └─ `__init__(self)` (строка 20) [magic]
            │       └─ `register_agent(self, operation_type, agent)` (строка 26)
            ├── 📄 `reply.py` - 1 класс(ов)
            │     📍 Путь: `src/agents/reply.py`
            │     🏛️ `ReplyAgent`(BaseAgent) (строка 20)
            │       📝 Агент для обработки редактирования операций через reply.
            │       └─ `__init__(self)` (строка 23) [magic]
            │       └─ `_get_reply_chain(self, message)` (строка 27)
            │       └─ `_get_full_reply_chain(self, message)` (строка 57)
            │       └─ `_find_operation_in_chain(self, chain)` (строка 111)
            │       └─ `_find_operation_by_message_id(self, message_id)` (строка 231)
            │       └─ `_get_operation_type(self, list_name)` (строка 312)
            │       └─ `_delete_operation(self, operation_info)` (строка 389)
            │       └─ `_apply_changes(self, operation_info, edit_request)` (строка 427)
            │       └─ `_get_sheet_id(self, list_name)` (строка 491)
            │       └─ `_get_column_mapping(self, list_name)` (строка 497)
            │       └─ `_get_cell_value(self, field, value)` (строка 526)
            │       └─ `_format_edit_success_message(self, edit_request)` (строка 533)
            └── 📄 `transfer.py` - 1 класс(ов)
                  📍 Путь: `src/agents/transfer.py`
                  🏛️ `TransferAgent`(BaseAgent) (строка 14)
                    📝 Агент для обработки переводов между счетами и корректировок балансов.
                    └─ `__init__(self)` (строка 17) [magic]
                    └─ `_validate_operation_data(self, operation_data, is_adjustment)` (строка 131)
                    └─ `_create_google_request(self, operation_data, is_adjustment)` (строка 181)
                    └─ `_format_success_message(self, operation_data, is_adjustment)` (строка 215)
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

- **Всего файлов:** 34
- **Python файлов:** 21
- **Строк кода:** 5,585
- **Классов:** 25
- **Функций:** 38
- **Методов:** 58

### Распределение файлов по типам:
- `.py`: 21 файлов
- `.md`: 5 файлов
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
