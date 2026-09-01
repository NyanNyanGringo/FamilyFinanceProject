# TreeView - Структура проекта FamilyFinanceProject

Этот документ содержит полную структуру проекта с информацией о файлах, классах и функциях.
Обновляется автоматически после внесения изменений в проект.

**Последнее обновление:** 2026-08-11 21:12:18
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
    ├── 📄 `expense_reclassification_apply_report.json`
    ├── 📄 `expense_reclassification_mapping.json`
    ├── 📄 `expense_reclassification_review.md`
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
    │     ⚡ `parse_expense_record(row, headers)` (строка 36)
    │       📝 Parse a single expense record into a dictionary.
    │     ⚡ `analyze_expenses_by_category(expenses, category, start_date=None, end_date=None)` (строка 56)
    │       📝 Analyze expenses for a specific category within a date range.
    │     ⚡ `get_expense_summary(category=None, months_back=None)` (строка 127)
    │       📝 Get a compact summary of expenses for a category.
    │     ⚡ `main()` (строка 234)
    │       📝 Main function to demonstrate expense data extraction and analysis.
    ├── 📁 **aidocs/** `/Users/user/github/FamilyFinanceProject/aidocs`
    │   ├── 📄 `about_google_sheet.md`
    │   ├── 📄 `architecture.md`
    │   ├── 📄 `code_style.md`
    │   ├── 📄 `commands.md`
    │   ├── 📄 `dev_seed.md`
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
    │       ├── 📄 `ffmpeg_utilities.py` - 2 функций
    │       │     📍 Путь: `lib/utilities/ffmpeg_utilities.py`
    │       │     ⚡ `get_wav_output_path(input_file)` (строка 7)
    │       │     ⚡ `convert_oga_to_wav(input_file)` (строка 11)
    │       │       📝 :return: path to .wav file
    │       ├── 📄 `google_utilities.py` - 14 класс(ов), 32 функций
    │       │     📍 Путь: `lib/utilities/google_utilities.py`
    │       │     ⚡ `_is_dev_mode()` (строка 37)
    │       │     ⚡ `_get_spreadsheet_id()` (строка 41)
    │       │     ⚡ `_authenticate_with_google()` (строка 73)
    │       │       📝 Аутентифицирует пользователя с помощью Google Service Account и возвращает об...
    │       │     ⚡ `_get_credentials()` (строка 95)
    │       │     ⚡ `_build_service(timeout_seconds)` (строка 104)
    │       │     ⚡ `_close_service(service)` (строка 119)
    │       │     ⚡ `_is_transient_google_error(error)` (строка 128)
    │       │     ⚡ `_execute_read(request_factory, attempts=...)` (строка 151)
    │       │     ⚡ `_execute_write(request_factory)` (строка 181)
    │       │     ⚡ `_get_sheet_ids(force_refresh=False)` (строка 204)
    │       │       📝 Получает идентификаторы всех листов в Google Spreadsheet.
    │       │     ⚡ `_get_sheet_row_count(list_name)` (строка 234)
    │       │       📝 Возвращает количество строк листа по его названию.
    │       │     ⚡ `ensure_min_rows(list_name, min_rows=7)` (строка 251)
    │       │       📝 Гарантирует, что лист имеет не меньше min_rows строк (нужно для вставки над с...
    │       │     ⚡ `_single_column_values(value_range)` (строка 313)
    │       │     ⚡ `_normalize_a1_range(range_name)` (строка 326)
    │       │     ⚡ `_load_finance_config_snapshot()` (строка 332)
    │       │     ⚡ `get_finance_config()` (строка 433)
    │       │     ⚡ `reload_finance_config()` (строка 437)
    │       │     ⚡ `get_values(cell_range, transform_to_single_list=False)` (строка 623)
    │       │       📝 Получает значения из Google Sheets по указанному диапазону.
    │       │     ⚡ `update_values(range_name, values, value_input_option='USER_ENTERED')` (строка 652)
    │       │       📝 Обновляет значения в указанном диапазоне Google Sheets.
    │       │     ⚡ `batch_update(body)` (строка 674)
    │       │       📝 Executes one Google Sheets batchUpdate without automatic write retries.
    │       │     ⚡ `get_insert_row_above_request(list_name, insert_above_row)` (строка 684)
    │       │       📝 Создает запрос для вставки новой строки в Google Sheets.
    │       │     ⚡ `get_update_cells_request(list_name, values_to_update, row_index=6, column_index=0)` (строка 721)
    │       │       📝 Создает запрос для обновления ячеек в Google Sheets.
    │       │     ⚡ `get_values_to_update_for_request(request_data)` (строка 747)
    │       │       📝 Формирует список значений для обновления в Google Sheets на основе данных зап...
    │       │     ⚡ `_telegram_id_column(list_name)` (строка 816)
    │       │     ⚡ `find_rows_by_telegram_id(list_name, telegram_message_id)` (строка 828)
    │       │     ⚡ `delete_row_by_telegram_id(list_name, telegram_message_id)` (строка 848)
    │       │       📝 Удаляет строку из Google Sheets по Telegram message ID.
    │       │     ⚡ `insert_and_update_row_batch_update(request_data)` (строка 901)
    │       │       📝 Выполняет пакетное обновление Google Sheets: вставляет новую строку и обновля...
    │       │     ⚡ `reset_input_sheet_preserve_template(list_name)` (строка 938)
    │       │       📝 Удаляет все заполненные строки на вводном листе, сохраняя нижнюю пустую шабло...
    │       │     ⚡ `reset_dev_input_sheets()` (строка 1012)
    │       │       📝 Выполняет reset для всех вводных листов DEV: расходы, доходы, переводы.
    │       │     ⚡ `get_memories()` (строка 1023)
    │       │       📝 Получает список сохранённых воспоминаний из ячейки A1 листа #memory.
    │       │     ⚡ `add_memory(memory_text)` (строка 1045)
    │       │       📝 Добавляет новое воспоминание в ячейку A1 листа #memory.
    │       │     ⚡ `delete_memory(memory_index)` (строка 1082)
    │       │       📝 Удаляет воспоминание по индексу из ячейки A1 листа #memory.
    │       │     🏛️ `GoogleWriteOutcomeUnknownError`(RuntimeError) (строка 69)
    │       │     🏛️ `_GoogleBaseEnumClass`(Enum) (строка 275)
    │       │       📝 Базовый класс для перечислений Google с дополнительными методами.
    │       │       └─ `__str__(self)` (строка 279) [magic]
    │       │       └─ `values(cls)` (строка 283) [@classmethod]
    │       │       └─ `get_item(cls, value)` (строка 287) [@classmethod]
    │       │     🏛️ `FinanceConfigSnapshot` (строка 295)
    │       │     🏛️ `FinanceConfigResult` (строка 303)
    │       │     🏛️ `FinanceConfigUnavailableError`(RuntimeError) (строка 309)
    │       │     🏛️ `FinanceConfigCache` (строка 377)
    │       │       └─ `__init__(self, loader=..., ttl_seconds=..., monotonic=...)` (строка 378) [magic]
    │       │       └─ `get(self, force_refresh=False)` (строка 391)
    │       │       └─ `_is_fresh(self, now)` (строка 424)
    │       │     🏛️ `Category` (строка 441)
    │       │       📝 Compatibility facade for code that does not yet pass a snapshot.
    │       │       └─ `__init__(self)` (строка 444) [magic]
    │       │       └─ `get_expenses(cls)` (строка 451) [@classmethod]
    │       │       └─ `get_incomes(cls)` (строка 455) [@classmethod]
    │       │       └─ `get_accounts(cls)` (строка 459) [@classmethod]
    │       │       └─ `force_update(cls)` (строка 463) [@classmethod]
    │       │     🏛️ `Formulas`(str, _GoogleBaseEnumClass) (строка 467)
    │       │       📝 Класс-строка для хранения формул Google Tables, используемых в проекте.
    │       │     🏛️ `OperationTypes`(str, _GoogleBaseEnumClass) (строка 533)
    │       │       📝 Перечисление типов операций: расходы, переводы, корректировки, доходы.
    │       │     🏛️ `ListName`(str, _GoogleBaseEnumClass) (строка 543)
    │       │       📝 Перечисление названий листов для разных типов операций.
    │       │     🏛️ `Status`(str, _GoogleBaseEnumClass) (строка 554)
    │       │       📝 Перечисление статусов операции: подтверждена, запланирована.
    │       │     🏛️ `TransferType`(str, _GoogleBaseEnumClass) (строка 562)
    │       │       📝 Перечисление типов переводов: перевод, корректировка.
    │       │     🏛️ `ConfigRange`(str, _GoogleBaseEnumClass) (строка 570)
    │       │       📝 Перечисление диапазонов ячеек для конфигурации Google Sheets.
    │       │     🏛️ `RequestData`(BaseModel) (строка 580)
    │       │       📝 Дата-класс для хранения данных запроса к Google Sheets.
    │       │       └─ `validate_data(self)` (строка 597)
    │       ├── 📄 `log_utilities.py` - 1 функций
    │       │     📍 Путь: `lib/utilities/log_utilities.py`
    │       │     ⚡ `get_logger(name='main')` (строка 5)
    │       │       📝 Создаёт и возвращает логгер с заданным именем.
    │       ├── 📄 `openai_utilities.py` - 4 класс(ов), 12 функций
    │       │     📍 Путь: `lib/utilities/openai_utilities.py`
    │       │     ⚡ `get_memory_context()` (строка 30)
    │       │       📝 Получает контекст воспоминаний для добавления в системные сообщения.
    │       │     ⚡ `text2text(prompt, model='gpt-4o-mini')` (строка 50)
    │       │       📝 Отправляет текстовый запрос в OpenAI и возвращает ответ.
    │       │     ⚡ `audio2text(audio_path, prompt='')` (строка 75)
    │       │       📝 Преобразует аудиофайл в текст с помощью OpenAI Whisper.
    │       │     ⚡ `audio2text_for_finance(audio_path, config_snapshot)` (строка 98)
    │       │       📝 Преобразует аудиофайл в текст с финансовым контекстом для FamilyFinanceProject.
    │       │     ⚡ `_get_adjustment_response_format(config_snapshot)` (строка 125)
    │       │     ⚡ `_get_transfer_response_format(config_snapshot)` (строка 194)
    │       │     ⚡ `_get_expenses_response_format(config_snapshot)` (строка 283)
    │       │     ⚡ `_get_incomes_response_format(config_snapshot)` (строка 366)
    │       │     ⚡ `_get_finance_operation_response_format(config_snapshot)` (строка 447)
    │       │     ⚡ `_get_finance_operation_message(user_message, memory_context='')` (строка 520)
    │       │     ⚡ `_get_basic_message(user_message, memory_context='')` (строка 551)
    │       │     ⚡ `request_data(request_builder)` (строка 640)
    │       │       📝 Отправляет запрос к OpenAI API и возвращает ответ в формате JSON.
    │       │     🏛️ `MessageRequest` (строка 580)
    │       │       📝 Класс для формирования сообщений-запросов к OpenAI.
    │       │       └─ `__init__(self, user_message, memory_context=None)` (строка 584) [magic]
    │       │     🏛️ `ResponseFormat` (строка 598)
    │       │       📝 Класс для хранения форматов ответов для разных типов операций.
    │       │       └─ `__init__(self, config_snapshot=None)` (строка 602) [magic]
    │       │     🏛️ `Model` (строка 613)
    │       │       📝 Класс с названиями моделей OpenAI.
    │       │     🏛️ `RequestBuilder`(BaseModel) (строка 626)
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
    │       ├── 📄 `telegram_utilities.py` - 1 функций
    │       │     📍 Путь: `lib/utilities/telegram_utilities.py`
    │       │     ⚡ `_remove_partial_download(path)` (строка 14)
    │       └── 📄 `vosk_utilities.py` - 1 функций
    │             📍 Путь: `lib/utilities/vosk_utilities.py`
    │             ⚡ `audio2text(wav_audio_file, frames=4000)` (строка 18)
    │               📝 Преобразует аудиофайл в текст с помощью модели Vosk.
    ├── 📁 **scripts/** `/Users/user/github/FamilyFinanceProject/scripts`
    │   ├── 📄 `expense_reclassification_apply.py` - 9 класс(ов), 44 функций
    │   │     📍 Путь: `scripts/expense_reclassification_apply.py`
    │   │     ⚡ `sha256_bytes(content)` (строка 139)
    │   │     ⚡ `spreadsheet_id_sha256(spreadsheet_id)` (строка 143)
    │   │     ⚡ `confirmation_token(mapping_sha256)` (строка 147)
    │   │     ⚡ `validate_mapping_binding(actual_sha256, expected_sha256, supplied_confirmation_token)` (строка 151)
    │   │     ⚡ `load_bound_mapping(mapping_path, expected_sha256, supplied_confirmation_token)` (строка 164)
    │   │     ⚡ `validate_mapping_structure(mapping)` (строка 182)
    │   │     ⚡ `require_successful_preview_audits(audit)` (строка 213)
    │   │     ⚡ `validate_changed_record(record)` (строка 220)
    │   │     ⚡ `validate_changed_locator_groups(all_records, changed_records)` (строка 254)
    │   │     ⚡ `group_records_by_stable_id(records)` (строка 279)
    │   │     ⚡ `parse_live_snapshot(response)` (строка 288)
    │   │     ⚡ `validate_settings_and_data_categories(settings, data)` (строка 303)
    │   │     ⚡ `validate_approved_categories(mapping, live)` (строка 319)
    │   │     ⚡ `validate_spreadsheet_identity(mapping, spreadsheet_id, live_expense_sheet_id)` (строка 342)
    │   │     ⚡ `current_operations_by_raw(operations)` (строка 357)
    │   │     ⚡ `match_approved_changes(mapping, current_operations)` (строка 366)
    │   │     ⚡ `match_telegram_locator_group(stable_id, approved_records, current_operations)` (строка 395)
    │   │     ⚡ `match_fingerprint_locator_group(stable_id, approved_records, current_by_raw)` (строка 417)
    │   │     ⚡ `planned_change(stable_id, record, operation)` (строка 445)
    │   │     ⚡ `validate_current_target(record, operation)` (строка 460)
    │   │     ⚡ `build_batch_update_body(expense_sheet_id, changes)` (строка 465)
    │   │     ⚡ `single_category_update(expense_sheet_id, change)` (строка 473)
    │   │     ⚡ `validate_batch_update_body(plan)` (строка 496)
    │   │     ⚡ `prepare_apply_plan(bound_mapping, spreadsheet_id, live)` (строка 504)
    │   │     ⚡ `changed_pair_counts(changes)` (строка 541)
    │   │     ⚡ `dry_run_report(plan)` (строка 549)
    │   │     ⚡ `verify_applied_operations(plan, postwrite_operations)` (строка 570)
    │   │     ⚡ `verify_applied_change(change, operation)` (строка 591)
    │   │     ⚡ `validate_postwrite_non_category_raw(change, actual_raw)` (строка 603)
    │   │     ⚡ `verify_applied_snapshot(plan, mapping, spreadsheet_id, response)` (строка 616)
    │   │     ⚡ `oauth_scope_for_mode(apply)` (строка 642)
    │   │     ⚡ `build_sheets_service(credentials_path, scope)` (строка 646)
    │   │     ⚡ `fetch_live_response(service, spreadsheet_id)` (строка 657)
    │   │     ⚡ `create_batch_update_request(service, spreadsheet_id, body)` (строка 667)
    │   │     ⚡ `dispatch_batch_update(request)` (строка 675)
    │   │     ⚡ `validate_batch_update_response(response, spreadsheet_id, expected_request_count)` (строка 679)
    │   │     ⚡ `execute_apply_workflow(service, spreadsheet_id, plan, mapping, report_path, started_at)` (строка 691)
    │   │     ⚡ `write_apply_report(path, report)` (строка 738)
    │   │     ⚡ `load_spreadsheet_id(env_name)` (строка 746)
    │   │     ⚡ `parse_args()` (строка 755)
    │   │     ⚡ `validate_mode_requirements(apply, mapping_sha256, supplied_confirmation_token, writers_paused)` (строка 789)
    │   │     ⚡ `main()` (строка 805)
    │   │     ⚡ `aborted_report(error)` (строка 853)
    │   │     ⚡ `cli_main()` (строка 862)
    │   │     🏛️ `ApplyError`(RuntimeError) (строка 67)
    │   │     🏛️ `WriteOutcome`(Enum) (строка 71)
    │   │     🏛️ `ApplyExecutionError`(ApplyError) (строка 77)
    │   │       └─ `__init__(self, message, write_outcome, writers_paused_acknowledged)` (строка 78) [magic]
    │   │     🏛️ `BoundMapping` (строка 90)
    │   │     🏛️ `LiveCategories` (строка 96)
    │   │     🏛️ `LiveSnapshot` (строка 103)
    │   │     🏛️ `PlannedChange` (строка 111)
    │   │     🏛️ `PrewriteOperation` (строка 121)
    │   │     🏛️ `ApplyPlan` (строка 127)
    │   ├── 📄 `expense_reclassification_preview.py` - 5 класс(ов), 124 функций
    │   │     📍 Путь: `scripts/expense_reclassification_preview.py`
    │   │     ⚡ `canonical_json(value)` (строка 198)
    │   │     ⚡ `sha256_json(value)` (строка 202)
    │   │     ⚡ `extended_value(cell, field)` (строка 206)
    │   │     ⚡ `display_value(cell)` (строка 214)
    │   │     ⚡ `effective_value(cell)` (строка 218)
    │   │     ⚡ `user_entered_value(cell)` (строка 222)
    │   │     ⚡ `normalized_text(value)` (строка 226)
    │   │     ⚡ `normalized_telegram_id(cell)` (строка 230)
    │   │     ⚡ `padded_cells(row, width)` (строка 240)
    │   │     ⚡ `sheet_block(response, title, width)` (строка 245)
    │   │     ⚡ `has_source_content(cells)` (строка 259)
    │   │     ⚡ `operation_row_hash(cells)` (строка 263)
    │   │     ⚡ `cell_snapshot(cell)` (строка 267)
    │   │     ⚡ `parse_operations(block)` (строка 276)
    │   │     ⚡ `operation_text(operation, index)` (строка 284)
    │   │     ⚡ `is_service_operation(operation)` (строка 289)
    │   │     ⚡ `numeric_value(cell)` (строка 299)
    │   │     ⚡ `fingerprint_payload(operation)` (строка 309)
    │   │     ⚡ `fingerprint_id(operation)` (строка 314)
    │   │     ⚡ `assign_stable_ids(operations)` (строка 318)
    │   │     ⚡ `telegram_id_or_fingerprint(operation, counts)` (строка 325)
    │   │     ⚡ `with_identity(operation, stable_id, match_count)` (строка 332)
    │   │     ⚡ `unique_nonempty(values)` (строка 337)
    │   │     ⚡ `column_values(block, relative_column)` (строка 341)
    │   │     ⚡ `category_data(data_block)` (строка 345)
    │   │     ⚡ `settings_expense_category_lists(block)` (строка 358)
    │   │     ⚡ `contiguous_values_after_header(values, header_index)` (строка 378)
    │   │     ⚡ `snapshot_hash(operations)` (строка 387)
    │   │     ⚡ `validation_rules(operations)` (строка 391)
    │   │     ⚡ `normalized_comment(operation)` (строка 397)
    │   │     ⚡ `has_pattern(text, pattern)` (строка 401)
    │   │     ⚡ `has_any_pattern(text, patterns)` (строка 405)
    │   │     ⚡ `make_decision(after, reason, confidence, rule)` (строка 409)
    │   │     ⚡ `unchanged_decision(before, reason='Категория уже соответствует правилам')` (строка 413)
    │   │     ⚡ `subscription_service(text, subscription_context=False)` (строка 417)
    │   │     ⚡ `is_subscription_candidate(before, text, service)` (строка 429)
    │   │     ⚡ `build_rule_context(operations, categories)` (строка 436)
    │   │     ⚡ `build_same_day_comments(operations)` (строка 453)
    │   │     ⚡ `approved_exception(operation)` (строка 463)
    │   │     ⚡ `user_approved_stable_override(operation)` (строка 481)
    │   │     ⚡ `is_approved_kiting(operation, before, comment)` (строка 489)
    │   │     ⚡ `approved_non_event_exception(operation, before)` (строка 499)
    │   │     ⚡ `is_approved_glasses(operation, before)` (строка 514)
    │   │     ⚡ `semantic_override(operation, context=None)` (строка 524)
    │   │     ⚡ `specific_content_override(before, text, context=None)` (строка 552)
    │   │     ⚡ `specific_personal_override(text)` (строка 566)
    │   │     ⚡ `specific_old_home_purchase_override(text)` (строка 584)
    │   │     ⚡ `narrow_home_subject_override(text)` (строка 621)
    │   │     ⚡ `other_subject_override(text, context=None)` (строка 634)
    │   │     ⚡ `lodging_override(before, text)` (строка 664)
    │   │     ⚡ `psychology_override(before, text)` (строка 672)
    │   │     ⚡ `residency_override(before, text)` (строка 684)
    │   │     ⚡ `personal_subject_override(before, text, context=None)` (строка 692)
    │   │     ⚡ `personal_subscription_override(text, context)` (строка 725)
    │   │     ⚡ `personal_care_or_health(before, text)` (строка 736)
    │   │     ⚡ `valid_category_override(before, text)` (строка 746)
    │   │     ⚡ `classify_animal(operation, context)` (строка 764)
    │   │     ⚡ `animal_groups(text)` (строка 780)
    │   │     ⚡ `animal_preferred_group(groups)` (строка 794)
    │   │     ⚡ `classify_car(operation)` (строка 799)
    │   │     ⚡ `classify_transport(operation)` (строка 820)
    │   │     ⚡ `classify_home(operation)` (строка 834)
    │   │     ⚡ `home_comment_is_ambiguous(text)` (строка 843)
    │   │     ⚡ `classify_office(operation)` (строка 851)
    │   │     ⚡ `classify_ip(operation)` (строка 867)
    │   │     ⚡ `classify_printing(operation, context)` (строка 882)
    │   │     ⚡ `same_day_operations(operations, date_value, target)` (строка 896)
    │   │     ⚡ `classify_subscription(operation, context)` (строка 900)
    │   │     ⚡ `classify_personal(operation, context)` (строка 920)
    │   │     ⚡ `classify_removed(operation, context)` (строка 940)
    │   │     ⚡ `classify_old_home(operation)` (строка 967)
    │   │     ⚡ `classify_operation(operation, context)` (строка 977)
    │   │     ⚡ `classify_all(operations, categories)` (строка 992)
    │   │     ⚡ `diagnostics(response)` (строка 998)
    │   │     ⚡ `block_hash(block)` (строка 1030)
    │   │     ⚡ `category_snapshot_hash(settings_block, data_block)` (строка 1034)
    │   │     ⚡ `raw_row(operation)` (строка 1038)
    │   │     ⚡ `effective_row(operation)` (строка 1042)
    │   │     ⚡ `display_row(operation)` (строка 1046)
    │   │     ⚡ `changed_indexes(operations, decisions, allowed)` (строка 1050)
    │   │     ⚡ `report_sort_key(operation, decision, order)` (строка 1056)
    │   │     ⚡ `report_numbers(operations, decisions, allowed)` (строка 1061)
    │   │     ⚡ `locator_record(operation)` (строка 1065)
    │   │     ⚡ `operation_record(operation, decision, number)` (строка 1079)
    │   │     ⚡ `eur_value(operation)` (строка 1097)
    │   │     ⚡ `category_summary(operations, decisions)` (строка 1104)
    │   │     ⚡ `summary_record(after, indexes, operations)` (строка 1112)
    │   │     ⚡ `pair_counts(operations, decisions)` (строка 1118)
    │   │     ⚡ `identity_audit(operations, decisions)` (строка 1123)
    │   │     ⚡ `collision_records(groups, operations, decisions)` (строка 1140)
    │   │     ⚡ `validate_invariants(operations, decisions, categories, service_count)` (строка 1153)
    │   │     ⚡ `invariant_checks(operations, decisions, categories, service_count, removed, changed, existing_events, new_events, identity)` (строка 1187)
    │   │     ⚡ `approved_event_distribution(operations, decisions, events)` (строка 1215)
    │   │     ⚡ `regression_ids_pass(operations, decisions)` (строка 1221)
    │   │     ⚡ `regression_id_cardinalities(operations, decisions)` (строка 1228)
    │   │     ⚡ `user_approved_overrides_pass(operations, decisions, overrides=None)` (строка 1248)
    │   │     ⚡ `user_approved_override_cardinalities(operations, decisions, overrides=None)` (строка 1259)
    │   │     ⚡ `build_mapping(response, spreadsheet_id, spreadsheet_env, started_at, finished_at)` (строка 1280)
    │   │     ⚡ `mapping_document(response, spreadsheet_id, spreadsheet_env, started_at, finished_at, source_rows, settings_block, data_block, categories, audit, records, operations, decisions)` (строка 1306)
    │   │     ⚡ `markdown_escape(value)` (строка 1348)
    │   │     ⚡ `format_operation_amount(record)` (строка 1352)
    │   │     ⚡ `format_eur_amount(record)` (строка 1358)
    │   │     ⚡ `compact_attention_row(record)` (строка 1365)
    │   │     ⚡ `full_markdown_row(record)` (строка 1370)
    │   │     ⚡ `render_markdown(mapping)` (строка 1375)
    │   │     ⚡ `markdown_header(mapping, audit)` (строка 1386)
    │   │     ⚡ `markdown_summary(summary)` (строка 1406)
    │   │     ⚡ `markdown_attention(reviews)` (строка 1413)
    │   │     ⚡ `markdown_full_list(changed, allowed)` (строка 1420)
    │   │     ⚡ `markdown_category(category, records)` (строка 1431)
    │   │     ⚡ `validate_artifacts(mapping, markdown)` (строка 1438)
    │   │     ⚡ `parse_markdown_report(markdown)` (строка 1465)
    │   │     ⚡ `markdown_row_numbers(section)` (строка 1487)
    │   │     ⚡ `records_follow_report_sort(records, allowed)` (строка 1491)
    │   │     ⚡ `record_date_number(record)` (строка 1504)
    │   │     ⚡ `summary_matches_records(summary, records)` (строка 1510)
    │   │     ⚡ `pair_counts_match_records(pair_summary, records)` (строка 1540)
    │   │     ⚡ `verify_category_snapshot(response, expected_hash)` (строка 1546)
    │   │     ⚡ `write_artifacts(output_dir, mapping, markdown)` (строка 1555)
    │   │     ⚡ `load_spreadsheet_id(env_name)` (строка 1568)
    │   │     ⚡ `build_readonly_service(credentials_path)` (строка 1575)
    │   │     ⚡ `fetch_snapshot(service, spreadsheet_id, ranges)` (строка 1586)
    │   │     ⚡ `parse_args()` (строка 1591)
    │   │     ⚡ `main()` (строка 1600)
    │   │     🏛️ `PreviewError`(RuntimeError) (строка 158)
    │   │     🏛️ `GridBlock` (строка 163)
    │   │     🏛️ `Operation` (строка 172)
    │   │     🏛️ `Decision` (строка 182)
    │   │     🏛️ `RuleContext` (строка 190)
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
    ├── 📁 **src/** `/Users/user/github/FamilyFinanceProject/src`
    │   ├── 📄 `dev_seed.py` - 5 класс(ов), 14 функций
    │   │     📍 Путь: `src/dev_seed.py`
    │   │     ⚡ `_parse_date_string(value)` (строка 43)
    │   │       📝 Пытается распарсить строковую дату из ячейки Sheets.
    │   │     ⚡ `sheet_serial_to_date(value)` (строка 62)
    │   │       📝 Преобразует значение ячейки (serial или строка) в date.
    │   │     ⚡ `date_to_serial(value)` (строка 78)
    │   │       📝 Преобразует date в Sheets serial number.
    │   │     ⚡ `read_start_date_from_settings()` (строка 85)
    │   │       📝 Читает дату начала таблицы из ⚙️Настройки!C12.
    │   │     ⚡ `_pad_values(rows, width, max_rows)` (строка 143)
    │   │     ⚡ `seed_dev_settings(template=..., overwrite=False)` (строка 150)
    │   │       📝 Заполняет лист ⚙️Настройки подготовленными значениями.
    │   │     ⚡ `_choose_salary_category(income_categories)` (строка 252)
    │   │     ⚡ `_pick_accounts(accounts)` (строка 263)
    │   │       📝 Возвращает (spend, savings, cash) при наличии хотя бы одного счета.
    │   │     ⚡ `_infer_currency(account_name)` (строка 278)
    │   │     ⚡ `_to_account_amount(base_rub_amount, account_name)` (строка 286)
    │   │     ⚡ `_ensure_positive_balance(ledger, account, needed_base_rub, for_date)` (строка 292)
    │   │     ⚡ `simulate_dev_history(seed, start_date, end_date, config=..., overrides=...)` (строка 316)
    │   │     ⚡ `apply_dev_history(sim, reset=True, batch_size=200)` (строка 619)
    │   │       📝 Применяет результаты симуляции в DEV-таблицу.
    │   │     ⚡ `run_dev_seed(seed=None, overwrite_settings=False, reset=True, batch_size=None)` (строка 670)
    │   │       📝 Удобный вход: читает дату начала, при желании заливает настройки, симулирует ...
    │   │     🏛️ `DevSettingsTemplate` (строка 97)
    │   │     🏛️ `SimulationConfig` (строка 211)
    │   │     🏛️ `DataOverrides` (строка 229)
    │   │     🏛️ `SimulationResult` (строка 236)
    │   │     🏛️ `ApplyReport` (строка 245)
    │   └── 📄 `server.py` - 1 класс(ов), 16 функций
    │         📍 Путь: `src/server.py`
    │         ⚡ `build_operation_tracking_id(chat_id, source_message_id, operation_sequence)` (строка 65)
    │           📝 Build a stable operation ID unique to a Telegram source message.
    │         ⚡ `replace_last_string(original_text, text_to_add)` (строка 80)
    │           📝 Заменяет последнюю строку в тексте на новую строку.
    │         ⚡ `_remove_audio_files(*paths)` (строка 156)
    │         ⚡ `_request_openai_data(user_message, response_format, finance_operation, memory_context)` (строка 168)
    │         ⚡ `format_json_to_telegram_text(json)` (строка 234)
    │           📝 Форматирует JSON-словарь в текст для Telegram.
    │         ⚡ `is_text_has_status(text)` (строка 251)
    │           📝 Проверяет, есть ли в тексте строка, начинающаяся с "Статус: ".
    │         ⚡ `remove_status_in_text(text)` (строка 265)
    │           📝 Удаляет строку со статусом из текста, если она существует и находится в после...
    │         ⚡ `set_status_to_text(text, status)` (строка 284)
    │           📝 Устанавливает новый статус в текст. Если статус уже есть, заменяет его.
    │         ⚡ `get_delete_button_keyboard(message_id)` (строка 426)
    │           📝 Создаёт клавиатуру с одной кнопкой "Удалить".
    │         ⚡ `get_delete_confirmation_keyboard(message_id)` (строка 442)
    │           📝 Создаёт клавиатуру для подтверждения удаления.
    │         ⚡ `get_reply_keyboard_markup(use_confirm_button=True, use_reject_button=True, message_id=None)` (строка 461)
    │           📝 Создаёт клавиатуру для Telegram с двумя кнопками: "Подтвердить" и "Отменить".
    │         ⚡ `get_response_format_according_to_operation_type(operation_type, response_formats)` (строка 504)
    │           📝 Возвращает формат ответа для указанного типа операции.
    │         ⚡ `clarify_request_message(request_message, config_snapshot)` (строка 529)
    │           📝 Валидирует и корректирует значения в сообщении запроса.
    │         ⚡ `_format_config_timestamp(config_snapshot)` (строка 1108)
    │         ⚡ `_stale_config_message(config_snapshot)` (строка 1112)
    │         ⚡ `run()` (строка 1380)
    │         🏛️ `Audio2TextModels` (строка 53)
    │           📝 Класс для выбора модели преобразования аудио в текст.
    └── 📁 **tests/** `/Users/user/github/FamilyFinanceProject/tests`
        ├── 📄 `test_dev_seed_simulation.py` - 1 класс(ов)
        │     📍 Путь: `tests/test_dev_seed_simulation.py`
        │     🏛️ `DevSeedSimulationTests`(unittest.TestCase) (строка 17)
        │       └─ `setUp(self)` (строка 18)
        │       └─ `test_date_roundtrip(self)` (строка 35)
        │       └─ `test_deterministic_simulation(self)` (строка 39)
        │       └─ `test_adjustment_rules(self)` (строка 84)
        │       └─ `test_generates_multiple_dates(self)` (строка 103)
        │       └─ `test_salary_present(self)` (строка 114)
        │       └─ `test_no_negative_ledger(self)` (строка 125)
        │       └─ `test_expenses_and_transfers_present(self)` (строка 135)
        │       └─ `test_apply_uses_fresh_batch_update_seam(self)` (строка 148)
        ├── 📄 `test_expense_reclassification_apply.py` - 1 класс(ов), 7 функций
        │     📍 Путь: `tests/test_expense_reclassification_apply.py`
        │     ⚡ `cell(value=None)` (строка 47)
        │     ⚡ `expense_operation(before='Покупки в Дом', comment='Ведро', row=7, telegram_id=None, amount=10)` (строка 57)
        │     ⚡ `identified(*operations)` (строка 83)
        │     ⚡ `changed_record(operation, number, after=...)` (строка 87)
        │     ⚡ `live_categories(regular=..., events=...)` (строка 92)
        │     ⚡ `mapping_document(records, categories=None)` (строка 96)
        │     ⚡ `prepared_single_target(approved_row=7, current_row=20)` (строка 127)
        │     🏛️ `ExpenseReclassificationApplyTests`(unittest.TestCase) (строка 136)
        │       └─ `test_mapping_binding_requires_exact_hash_or_token(self)` (строка 137)
        │       └─ `test_row_shift_resolves_by_stable_id_and_raw_not_snapshot_row(self)` (строка 148)
        │       └─ `test_duplicate_current_telegram_id_aborts(self)` (строка 156)
        │       └─ `test_fingerprint_collision_with_same_decision_matches_exact_group(self)` (строка 167)
        │       └─ `test_fingerprint_collision_with_different_decisions_aborts(self)` (строка 185)
        │       └─ `test_unrelated_new_current_operation_is_ignored_and_not_targeted(self)` (строка 198)
        │       └─ `test_full_raw_drift_aborts_even_when_unique_telegram_still_matches(self)` (строка 214)
        │       └─ `test_drift_aborts_before_batch_body_is_constructed(self)` (строка 222)
        │       └─ `test_unique_telegram_accepts_effective_and_display_drift_when_raw_is_exact(self)` (строка 239)
        │       └─ `test_raw_formula_or_value_drift_is_rejected_for_unique_telegram(self)` (строка 256)
        │       └─ `test_fingerprint_locator_uses_exact_raw_despite_effective_eur_drift(self)` (строка 271)
        │       └─ `test_settings_and_data_category_drift_aborts(self)` (строка 288)
        │       └─ `test_current_categories_must_equal_approved_snapshot(self)` (строка 303)
        │       └─ `test_batch_body_has_only_one_cell_user_entered_value_updates(self)` (строка 313)
        │       └─ `test_postwrite_verification_checks_category_and_all_other_raw_fields(self)` (строка 336)
        │       └─ `test_postwrite_verification_checks_every_untargeted_prewrite_row(self)` (строка 350)
        │       └─ `test_batch_update_response_is_bound_to_sheet_and_request_count(self)` (строка 376)
        │       └─ `test_dry_run_report_cannot_claim_a_write(self)` (строка 395)
        │       └─ `test_only_explicit_apply_mode_uses_full_scope(self)` (строка 405)
        │       └─ `test_pre_dispatch_failure_reports_write_false(self)` (строка 409)
        │       └─ `test_transport_failure_after_dispatch_reports_unknown(self)` (строка 421)
        │       └─ `test_request_construction_failure_remains_pre_dispatch_false(self)` (строка 447)
        │       └─ `test_postwrite_verification_failure_reports_write_true(self)` (строка 466)
        │       └─ `test_confirmed_response_success_reports_write_true_and_pause_ack(self)` (строка 499)
        │       └─ `test_apply_rejects_mapping_sha_without_confirmation_token(self)` (строка 536)
        │       └─ `test_apply_requires_confirmation_token_and_writers_pause(self)` (строка 540)
        ├── 📄 `test_expense_reclassification_preview.py` - 1 класс(ов), 5 функций
        │     📍 Путь: `tests/test_expense_reclassification_preview.py`
        │     ⚡ `cell(value=None, formatted=None, validation=None)` (строка 42)
        │     ⚡ `operation(values, row=7)` (строка 55)
        │     ⚡ `expense_operation(before, comment, date=1, amount=10, currency='EUR', row=7)` (строка 60)
        │     ⚡ `rule_context(*operations, subscription_counts=None, same_day_comments=None)` (строка 64)
        │     ⚡ `artifact_record(number, date, confidence, changed=True)` (строка 74)
        │     🏛️ `PreviewPureFunctionTests`(unittest.TestCase) (строка 97)
        │       └─ `test_unique_telegram_id_is_preferred(self)` (строка 98)
        │       └─ `test_duplicate_telegram_id_falls_back_to_fingerprint(self)` (строка 107)
        │       └─ `test_service_row_is_recognized_by_content(self)` (строка 116)
        │       └─ `test_allowed_categories_are_deduplicated(self)` (строка 121)
        │       └─ `test_lodging_word_boundary_does_not_match_trotelnik(self)` (строка 132)
        │       └─ `test_mobile_rule_does_not_match_automobile(self)` (строка 135)
        │       └─ `test_psychologist_for_driving_documents_is_not_therapy(self)` (строка 138)
        │       └─ `test_psychology_webinar_is_education(self)` (строка 144)
        │       └─ `test_beauty_in_health_is_reclassified(self)` (строка 149)
        │       └─ `test_gym_food_is_products(self)` (строка 154)
        │       └─ `test_markdown_escapes_pipes_and_newlines(self)` (строка 159)
        │       └─ `test_tire_stem_does_not_match_inside_car_word(self)` (строка 162)
        │       └─ `test_car_driving_authorization_is_not_maintenance(self)` (строка 170)
        │       └─ `test_gifted_money_does_not_turn_hairbrush_into_gift(self)` (строка 178)
        │       └─ `test_pull_and_bear_typo_is_clothing(self)` (строка 184)
        │       └─ `test_orthopedic_insoles_are_health(self)` (строка 189)
        │       └─ `test_animal_consultation_about_does_not_match_leash(self)` (строка 194)
        │       └─ `test_nextgard_is_veterinary(self)` (строка 199)
        │       └─ `test_blank_animal_comment_uses_medium_same_day_context(self)` (строка 202)
        │       └─ `test_ip_must_be_standalone_in_subscription_business_rule(self)` (строка 211)
        │       └─ `test_explicit_subscription_for_ip_uses_business_rule(self)` (строка 220)
        │       └─ `test_home_specific_items_outrank_clothing_hints(self)` (строка 228)
        │       └─ `test_therapeutic_shampoo_stays_in_health(self)` (строка 241)
        │       └─ `test_color_adjective_is_not_a_flower_gift(self)` (строка 247)
        │       └─ `test_mixed_home_carts_are_review(self)` (строка 258)
        │       └─ `test_home_unknown_or_shop_only_comment_is_review(self)` (строка 272)
        │       └─ `test_home_specific_subjects_override_default(self)` (строка 280)
        │       └─ `test_personal_subscription_uses_cross_category_history(self)` (строка 291)
        │       └─ `test_single_personal_subscription_is_not_high_confidence_monthly(self)` (строка 301)
        │       └─ `test_spaced_cyrillic_vdsina_joins_recurring_series(self)` (строка 310)
        │       └─ `test_repeated_kling_forgotten_subscription_is_monthly(self)` (строка 319)
        │       └─ `test_sport_subscription_uses_subject_category(self)` (строка 328)
        │       └─ `test_settings_lists_are_parsed_independently(self)` (строка 334)
        │       └─ `test_settings_parser_requires_exactly_two_headers(self)` (строка 346)
        │       └─ `test_regression_ids_require_exact_cardinality(self)` (строка 351)
        │       └─ `test_runtime_artifact_validator_detects_markdown_drift(self)` (строка 372)
        │       └─ `test_cable_routing_is_not_sanitary_pad_self_care(self)` (строка 392)
        │       └─ `test_ambiguous_gel_home_purchase_is_review(self)` (строка 403)
        │       └─ `test_animal_food_with_secondary_item_is_mixed_review(self)` (строка 408)
        │       └─ `test_home_mixed_care_items_are_review(self)` (строка 419)
        │       └─ `test_birthday_trampoline_series_is_entertainment(self)` (строка 426)
        │       └─ `test_yandex_disk_spellings_share_monthly_history(self)` (строка 433)
        │       └─ `test_apple_and_icloud_share_monthly_history(self)` (строка 443)
        │       └─ `test_subscription_context_spelling_aliases_join_history(self)` (строка 460)
        │       └─ `test_ambiguous_home_comments_and_specific_care(self)` (строка 479)
        │       └─ `test_home_unknown_shampoo_and_hair_ties_are_review(self)` (строка 489)
        │       └─ `test_other_unreal_and_decor_are_review_candidates(self)` (строка 496)
        │       └─ `test_entertainment_app_subscriptions_are_reclassified(self)` (строка 503)
        │       └─ `test_non_event_apartments_are_lodging(self)` (строка 510)
        │       └─ `test_non_event_cottage_genitive_is_lodging(self)` (строка 518)
        │       └─ `test_entertainment_explicit_products_and_steam_game(self)` (строка 524)
        │       └─ `test_approved_glasses_override_gift_word(self)` (строка 533)
        │       └─ `test_user_approved_override_uses_only_stable_identity(self)` (строка 547)
        │       └─ `test_user_approved_override_requires_exact_cardinality(self)` (строка 559)
        │       └─ `test_blank_printing_is_user_approved_other(self)` (строка 571)
        │       └─ `test_explicit_printing_subject_still_routes_by_subject(self)` (строка 579)
        │       └─ `test_parking_and_toll_use_renamed_category(self)` (строка 591)
        ├── 📄 `test_finance_config_runtime.py` - 2 класс(ов), 1 функций
        │     📍 Путь: `tests/test_finance_config_runtime.py`
        │     ⚡ `snapshot(name)` (строка 21)
        │     🏛️ `FinanceConfigCacheTests`(unittest.TestCase) (строка 30)
        │       └─ `test_snapshot_is_immutable(self)` (строка 31)
        │       └─ `test_ttl_uses_monotonic_clock_and_replaces_snapshot_atomically(self)` (строка 37)
        │       └─ `test_failed_refresh_returns_last_known_good_snapshot(self)` (строка 63)
        │       └─ `test_failed_initial_load_raises_typed_error(self)` (строка 83)
        │       └─ `test_concurrent_cache_miss_loads_once(self)` (строка 93)
        │     🏛️ `GoogleReadExecutionTests`(unittest.TestCase) (строка 114)
        │       └─ `test_transient_timeout_retries_with_fresh_service(self)` (строка 115)
        │       └─ `test_http_408_429_and_5xx_are_transient(self)` (строка 161)
        │       └─ `test_non_transient_error_is_not_retried(self)` (строка 176)
        │       └─ `test_transient_read_failure_stops_after_three_attempts(self)` (строка 191)
        │       └─ `test_write_does_not_retry_ambiguous_timeout(self)` (строка 214)
        │       └─ `test_write_factory_failure_is_not_marked_as_unknown(self)` (строка 229)
        │       └─ `test_delete_propagates_read_failure(self)` (строка 238)
        │       └─ `test_delete_propagates_ambiguous_write_without_retry(self)` (строка 252)
        │       └─ `test_credentials_are_loaded_once_for_fresh_services(self)` (строка 274)
        │       └─ `test_snapshot_loader_uses_one_batch_get(self)` (строка 303)
        │       └─ `test_snapshot_loader_rejects_partial_batch_response(self)` (строка 330)
        │       └─ `test_snapshot_loader_rejects_malformed_values_and_wrong_range(self)` (строка 346)
        │       └─ `test_snapshot_loader_rejects_empty_config_ranges(self)` (строка 378)
        └── 📄 `test_voice_runtime.py` - 7 класс(ов), 1 функций
              📍 Путь: `tests/test_voice_runtime.py`
              ⚡ `config_snapshot()` (строка 23)
              🏛️ `FinanceSnapshotPlumbingTests`(unittest.TestCase) (строка 32)
                └─ `test_whisper_prompt_uses_passed_snapshot(self)` (строка 33)
                └─ `test_response_formats_keep_passed_snapshot(self)` (строка 48)
                └─ `test_validation_uses_passed_snapshot(self)` (строка 66)
              🏛️ `OperationTrackingIdTests`(unittest.TestCase) (строка 82)
                └─ `test_same_source_message_in_different_chats_does_not_collide(self)` (строка 83)
                └─ `test_long_components_use_stable_callback_safe_id(self)` (строка 91)
              🏛️ `AudioLifecycleTests`(unittest.IsolatedAsyncioTestCase) (строка 111)
              🏛️ `TelegramDownloadLifecycleTests`(unittest.IsolatedAsyncioTestCase) (строка 314)
              🏛️ `BotInitializationTests`(unittest.IsolatedAsyncioTestCase) (строка 418)
              🏛️ `WriteReconciliationTests`(unittest.IsolatedAsyncioTestCase) (строка 518)
                └─ `request(self, tracking_id='123-1')` (строка 519)
              🏛️ `VoiceOperationSnapshotTests`(unittest.IsolatedAsyncioTestCase) (строка 704)
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

- **Всего файлов:** 63
- **Python файлов:** 24
- **Строк кода:** 337,998
- **Классов:** 51
- **Функций:** 272
- **Методов:** 143

### Распределение файлов по типам:
- `.md`: 26 файлов
- `.py`: 24 файлов
- `.json`: 4 файлов
- `.sh`: 3 файлов
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
