import asyncio
import os
import tempfile
import threading
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from lib.utilities.google_utilities import (
    FinanceConfigResult,
    FinanceConfigSnapshot,
    FinanceConfigUnavailableError,
    GoogleWriteOutcomeUnknownError,
    ListName,
    RequestData,
)
from lib.utilities.openai_utilities import ResponseFormat, audio2text_for_finance
from lib.utilities import telegram_utilities
from src import server


def config_snapshot() -> FinanceConfigSnapshot:
    return FinanceConfigSnapshot(
        expenses=("Wine", "Food"),
        incomes=("Salary",),
        accounts=("Cash", "Card"),
        loaded_at=datetime(2026, 8, 11, 12, 0, tzinfo=timezone.utc),
    )


class FinanceSnapshotPlumbingTests(unittest.TestCase):
    def test_whisper_prompt_uses_passed_snapshot(self):
        current = config_snapshot()

        with patch(
            "lib.utilities.openai_utilities.audio2text",
            return_value="610 dinar wine",
        ) as transcribe:
            result = audio2text_for_finance("voice.wav", current)

        self.assertEqual(result, "610 dinar wine")
        prompt = transcribe.call_args.kwargs["prompt"]
        self.assertIn("Wine", prompt)
        self.assertIn("Salary", prompt)
        self.assertIn("Cash", prompt)

    def test_response_formats_keep_passed_snapshot(self):
        current = config_snapshot()

        response_formats = ResponseFormat(current)

        self.assertIs(response_formats.config_snapshot, current)
        expense_properties = response_formats.expenses_response_format["json_schema"][
            "schema"
        ]["properties"]
        self.assertEqual(
            expense_properties["expenses_category"]["items"]["enum"],
            ["Wine", "Food"],
        )
        self.assertEqual(
            expense_properties["account"]["items"]["enum"],
            ["Cash", "Card"],
        )

    def test_validation_uses_passed_snapshot(self):
        current = config_snapshot()

        result = server.clarify_request_message(
            {
                "expenses_category": "wine",
                "account": "cash",
                "amount": 610,
            },
            current,
        )

        self.assertEqual(result["expenses_category"], "Wine")
        self.assertEqual(result["account"], "Cash")


class OperationTrackingIdTests(unittest.TestCase):
    def test_same_source_message_in_different_chats_does_not_collide(self):
        first_chat_id = server.build_operation_tracking_id(-1001001, 456, 1)
        second_chat_id = server.build_operation_tracking_id(-1001002, 456, 1)

        self.assertEqual(first_chat_id, "-1001001:456:1")
        self.assertEqual(second_chat_id, "-1001002:456:1")
        self.assertNotEqual(first_chat_id, second_chat_id)

    def test_long_components_use_stable_callback_safe_id(self):
        tracking_id = server.build_operation_tracking_id(
            int("9" * 80),
            int("8" * 80),
            int("7" * 80),
        )
        repeated = server.build_operation_tracking_id(
            int("9" * 80),
            int("8" * 80),
            int("7" * 80),
        )

        self.assertEqual(tracking_id, repeated)
        self.assertTrue(tracking_id.startswith("op-"))
        self.assertLessEqual(
            len(f"delete_confirm_{tracking_id}".encode("utf-8")),
            server.TELEGRAM_CALLBACK_DATA_MAX_BYTES,
        )


class AudioLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_custom_text_skips_download_and_conversion(self):
        current = config_snapshot()

        with patch.object(
            server,
            "download_voice_message",
            new=AsyncMock(),
        ) as download, patch.object(server, "convert_oga_to_wav") as convert:
            result = await server.get_text_from_audio(
                update=object(),
                context=object(),
                audio2text_model=server.Audio2TextModels.whisper,
                config_snapshot=current,
                custom_text="test message",
            )

        self.assertEqual(result, "test message")
        download.assert_not_awaited()
        convert.assert_not_called()

    async def test_created_audio_files_are_removed_after_success(self):
        current = config_snapshot()
        with tempfile.TemporaryDirectory() as directory:
            oga_path = os.path.join(directory, "voice.oga")
            wav_path = os.path.join(directory, "voice.wav")
            with open(oga_path, "wb") as oga_file:
                oga_file.write(b"oga")
            with open(wav_path, "wb") as wav_file:
                wav_file.write(b"wav")

            with patch.object(
                server,
                "download_voice_message",
                new=AsyncMock(return_value=oga_path),
            ), patch.object(
                server,
                "convert_oga_to_wav",
                return_value=wav_path,
            ), patch.object(
                server,
                "audio2text_for_finance",
                return_value="voice text",
            ):
                result = await server.get_text_from_audio(
                    update=object(),
                    context=object(),
                    audio2text_model=server.Audio2TextModels.whisper,
                    config_snapshot=current,
                )

            self.assertEqual(result, "voice text")
            self.assertFalse(os.path.exists(oga_path))
            self.assertFalse(os.path.exists(wav_path))

    async def test_created_audio_files_are_removed_when_transcription_fails(self):
        current = config_snapshot()
        with tempfile.TemporaryDirectory() as directory:
            oga_path = os.path.join(directory, "voice.oga")
            wav_path = os.path.join(directory, "voice.wav")
            with open(oga_path, "wb") as oga_file:
                oga_file.write(b"oga")
            with open(wav_path, "wb") as wav_file:
                wav_file.write(b"wav")

            with patch.object(
                server,
                "download_voice_message",
                new=AsyncMock(return_value=oga_path),
            ), patch.object(
                server,
                "convert_oga_to_wav",
                return_value=wav_path,
            ), patch.object(
                server,
                "audio2text_for_finance",
                side_effect=RuntimeError("transcription failed"),
            ):
                with self.assertRaisesRegex(RuntimeError, "transcription failed"):
                    await server.get_text_from_audio(
                        update=object(),
                        context=object(),
                        audio2text_model=server.Audio2TextModels.whisper,
                        config_snapshot=current,
                    )

            self.assertFalse(os.path.exists(oga_path))
            self.assertFalse(os.path.exists(wav_path))

    async def test_partial_wav_is_removed_when_ffmpeg_fails(self):
        current = config_snapshot()
        with tempfile.TemporaryDirectory() as directory:
            oga_path = os.path.join(directory, "voice.oga")
            wav_path = os.path.join(directory, "voice.wav")
            with open(oga_path, "wb") as oga_file:
                oga_file.write(b"oga")

            def fail_conversion(_):
                with open(wav_path, "wb") as wav_file:
                    wav_file.write(b"partial")
                raise RuntimeError("ffmpeg failed")

            with patch.object(
                server,
                "download_voice_message",
                new=AsyncMock(return_value=oga_path),
            ), patch.object(
                server,
                "convert_oga_to_wav",
                side_effect=fail_conversion,
            ):
                with self.assertRaisesRegex(RuntimeError, "ffmpeg failed"):
                    await server.get_text_from_audio(
                        update=object(),
                        context=object(),
                        audio2text_model=server.Audio2TextModels.whisper,
                        config_snapshot=current,
                    )

            self.assertFalse(os.path.exists(oga_path))
            self.assertFalse(os.path.exists(wav_path))

    async def test_cancellation_waits_for_ffmpeg_before_audio_cleanup(self):
        current = config_snapshot()
        with tempfile.TemporaryDirectory() as directory:
            oga_path = os.path.join(directory, "voice.oga")
            wav_path = os.path.join(directory, "voice.wav")
            with open(oga_path, "wb") as oga_file:
                oga_file.write(b"oga")

            conversion_started = threading.Event()
            finish_conversion = threading.Event()

            def delayed_conversion(_):
                conversion_started.set()
                if not finish_conversion.wait(timeout=2):
                    raise TimeoutError("test conversion release timed out")
                with open(wav_path, "wb") as wav_file:
                    wav_file.write(b"late wav")
                return wav_path

            with patch.object(
                server,
                "download_voice_message",
                new=AsyncMock(return_value=oga_path),
            ), patch.object(
                server,
                "convert_oga_to_wav",
                side_effect=delayed_conversion,
            ):
                task = asyncio.create_task(
                    server.get_text_from_audio(
                        update=object(),
                        context=object(),
                        audio2text_model=server.Audio2TextModels.whisper,
                        config_snapshot=current,
                    )
                )
                started = await asyncio.wait_for(
                    asyncio.to_thread(conversion_started.wait, 1),
                    timeout=2,
                )
                self.assertTrue(started)
                task.cancel()
                await asyncio.sleep(0)
                finish_conversion.set()

                with self.assertRaises(asyncio.CancelledError):
                    await asyncio.wait_for(task, timeout=2)

            self.assertFalse(os.path.exists(oga_path))
            self.assertFalse(os.path.exists(wav_path))

    async def test_cleanup_failure_does_not_mask_transcription_result(self):
        current = config_snapshot()

        with patch.object(
            server,
            "download_voice_message",
            new=AsyncMock(return_value="voice.oga"),
        ), patch.object(
            server,
            "convert_oga_to_wav",
            return_value="voice.wav",
        ), patch.object(
            server,
            "audio2text_for_finance",
            return_value="voice text",
        ), patch.object(
            server.os,
            "remove",
            side_effect=PermissionError("cannot unlink"),
        ):
            result = await server.get_text_from_audio(
                update=object(),
                context=object(),
                audio2text_model=server.Audio2TextModels.whisper,
                config_snapshot=current,
            )

        self.assertEqual(result, "voice text")


class TelegramDownloadLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_download_success_returns_created_path(self):
        with tempfile.TemporaryDirectory() as directory:
            async def download(path):
                with open(path, "wb") as voice_file:
                    voice_file.write(b"voice")

            telegram_file = SimpleNamespace(
                download_to_drive=AsyncMock(side_effect=download)
            )
            context = SimpleNamespace(
                bot=SimpleNamespace(get_file=AsyncMock(return_value=telegram_file))
            )
            update = SimpleNamespace(
                message=SimpleNamespace(voice=SimpleNamespace(file_id="file-id"))
            )

            with patch.object(
                telegram_utilities,
                "get_voice_messages_path",
                return_value=directory,
            ):
                path = await telegram_utilities.download_voice_message(update, context)

            self.assertTrue(os.path.exists(path))

    async def test_partial_download_is_removed_on_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            async def fail_download(path):
                with open(path, "wb") as voice_file:
                    voice_file.write(b"partial")
                raise RuntimeError("download failed")

            telegram_file = SimpleNamespace(
                download_to_drive=AsyncMock(side_effect=fail_download)
            )
            context = SimpleNamespace(
                bot=SimpleNamespace(get_file=AsyncMock(return_value=telegram_file))
            )
            update = SimpleNamespace(
                message=SimpleNamespace(voice=SimpleNamespace(file_id="file-id"))
            )

            with patch.object(
                telegram_utilities,
                "get_voice_messages_path",
                return_value=directory,
            ):
                with self.assertRaisesRegex(RuntimeError, "download failed"):
                    await telegram_utilities.download_voice_message(update, context)

            self.assertEqual(os.listdir(directory), [])

    async def test_partial_download_is_removed_on_cancellation(self):
        with tempfile.TemporaryDirectory() as directory:
            async def cancel_download(path):
                with open(path, "wb") as voice_file:
                    voice_file.write(b"partial")
                raise asyncio.CancelledError

            telegram_file = SimpleNamespace(
                download_to_drive=AsyncMock(side_effect=cancel_download)
            )
            context = SimpleNamespace(
                bot=SimpleNamespace(get_file=AsyncMock(return_value=telegram_file))
            )
            update = SimpleNamespace(
                message=SimpleNamespace(voice=SimpleNamespace(file_id="file-id"))
            )

            with patch.object(
                telegram_utilities,
                "get_voice_messages_path",
                return_value=directory,
            ):
                with self.assertRaises(asyncio.CancelledError):
                    await telegram_utilities.download_voice_message(update, context)

            self.assertEqual(os.listdir(directory), [])

    async def test_cleanup_failure_does_not_mask_download_failure(self):
        telegram_file = SimpleNamespace(
            download_to_drive=AsyncMock(side_effect=RuntimeError("download failed"))
        )
        context = SimpleNamespace(
            bot=SimpleNamespace(get_file=AsyncMock(return_value=telegram_file))
        )
        update = SimpleNamespace(
            message=SimpleNamespace(voice=SimpleNamespace(file_id="file-id"))
        )

        with patch.object(
            telegram_utilities,
            "get_voice_messages_path",
            return_value="/tmp",
        ), patch.object(
            telegram_utilities.os,
            "remove",
            side_effect=PermissionError("cannot unlink"),
        ):
            with self.assertRaisesRegex(RuntimeError, "download failed"):
                await telegram_utilities.download_voice_message(update, context)


class BotInitializationTests(unittest.IsolatedAsyncioTestCase):
    async def test_startup_config_failure_does_not_prevent_command_setup(self):
        application = object()

        with patch.object(
            server,
            "reload_finance_config",
            side_effect=FinanceConfigUnavailableError("unavailable"),
        ), patch.object(
            server,
            "set_bot_commands",
            new=AsyncMock(),
        ) as set_commands:
            await server.initialize_bot(application)

        set_commands.assert_awaited_once_with(application)

    async def test_startup_success_loads_config_before_command_setup(self):
        application = object()
        current = config_snapshot()

        with patch.object(
            server,
            "reload_finance_config",
            return_value=FinanceConfigResult(snapshot=current),
        ) as reload_config, patch.object(
            server,
            "set_bot_commands",
            new=AsyncMock(),
        ) as set_commands:
            await server.initialize_bot(application)

        reload_config.assert_called_once_with()
        set_commands.assert_awaited_once_with(application)

    async def test_registered_commands_include_reload_config(self):
        application = SimpleNamespace(
            bot=SimpleNamespace(set_my_commands=AsyncMock())
        )

        await server.set_bot_commands(application)

        commands = application.bot.set_my_commands.await_args.args[0]
        self.assertIn("reload_config", [command.command for command in commands])

    async def test_manual_reload_reports_successful_snapshot(self):
        current = config_snapshot()
        update = SimpleNamespace(
            message=SimpleNamespace(reply_text=AsyncMock()),
        )

        with patch.object(
            server,
            "reload_finance_config",
            return_value=FinanceConfigResult(snapshot=current),
        ):
            await server.reload_config_handler(update, object())

        message = update.message.reply_text.await_args.args[0]
        self.assertIn("Категории и счета обновлены", message)
        self.assertIn("Расходы: 2", message)
        self.assertIn("счета: 2", message)

    async def test_manual_reload_reports_last_known_good_on_failure(self):
        current = config_snapshot()
        update = SimpleNamespace(
            message=SimpleNamespace(reply_text=AsyncMock()),
        )

        with patch.object(
            server,
            "reload_finance_config",
            return_value=FinanceConfigResult(
                snapshot=current,
                used_stale=True,
                refresh_error="timeout",
            ),
        ):
            await server.reload_config_handler(update, object())

        message = update.message.reply_text.await_args.args[0]
        self.assertIn("Обновить категории и счета не удалось", message)
        self.assertIn("2026-08-11", message)

    async def test_manual_reload_without_cache_reports_failure(self):
        update = SimpleNamespace(
            message=SimpleNamespace(reply_text=AsyncMock()),
        )

        with patch.object(
            server,
            "reload_finance_config",
            side_effect=FinanceConfigUnavailableError("unavailable"),
        ):
            await server.reload_config_handler(update, object())

        message = update.message.reply_text.await_args.args[0]
        self.assertIn("Не удалось загрузить категории и счета", message)


class WriteReconciliationTests(unittest.IsolatedAsyncioTestCase):
    def request(self, tracking_id: str = "123-1") -> RequestData:
        return RequestData(
            list_name=ListName.expenses,
            expenses_category="Wine",
            account="Cash",
            amount=610,
            telegram_message_id=tracking_id,
        )

    async def test_ambiguous_write_found_once_is_reconciled_as_success(self):
        request = self.request()

        with patch.object(
            server,
            "insert_and_update_row_batch_update",
            side_effect=GoogleWriteOutcomeUnknownError("unknown"),
        ) as write, patch.object(
            server,
            "find_rows_by_telegram_id",
            return_value=(7,),
        ) as find:
            saved = await server._write_finance_operation(request)

        self.assertTrue(saved)
        write.assert_called_once_with(request)
        find.assert_called_once_with(ListName.expenses, "123-1")

    async def test_ambiguous_write_without_exact_match_is_not_retried(self):
        request = self.request()

        with patch.object(
            server,
            "insert_and_update_row_batch_update",
            side_effect=GoogleWriteOutcomeUnknownError("unknown"),
        ) as write, patch.object(
            server,
            "find_rows_by_telegram_id",
            return_value=(),
        ):
            saved = await server._write_finance_operation(request)

        self.assertFalse(saved)
        write.assert_called_once_with(request)

    async def test_reconciliation_read_failure_stays_unknown(self):
        request = self.request()

        with patch.object(
            server,
            "insert_and_update_row_batch_update",
            side_effect=GoogleWriteOutcomeUnknownError("unknown"),
        ) as write, patch.object(
            server,
            "find_rows_by_telegram_id",
            side_effect=TimeoutError("read failed"),
        ):
            saved = await server._write_finance_operation(request)

        self.assertFalse(saved)
        write.assert_called_once_with(request)

    async def test_confirm_callback_preserves_tracking_id_in_request(self):
        tracking_id = "-1001001:456:1"
        message = SimpleNamespace(message_id=999, reply_markup=None)
        query = SimpleNamespace(
            answer=AsyncMock(),
            message=message,
            data=f"confirm_{tracking_id}",
        )
        update = SimpleNamespace(callback_query=query)
        context = SimpleNamespace(
            user_data={
                f"msg_{tracking_id}": {
                    "operation_type": server.OperationTypes.expenses,
                    "request_message": {
                        "expenses_category": "Wine",
                        "account": "Cash",
                        "amount": 610,
                        "status": "Committed",
                        "comment": "wine",
                    },
                    "source_inputted_text": "610 dinar wine",
                    "body_text": "body",
                }
            }
        )

        with patch.object(
            server,
            "_write_finance_operation",
            new=AsyncMock(return_value=True),
        ) as write, patch.object(
            server,
            "edit_message",
            new=AsyncMock(),
        ):
            await server.operation_button_handler(update, context)

        request = write.await_args.args[0]
        self.assertEqual(request.telegram_message_id, tracking_id)

    async def test_delete_callback_reports_ambiguous_outcome_without_not_found(self):
        tracking_id = "-1001001:456:1"
        message = SimpleNamespace(message_id=999, reply_markup=None)
        query = SimpleNamespace(
            answer=AsyncMock(),
            message=message,
            data=f"delete_confirm_{tracking_id}",
        )
        message_data_key = f"msg_{tracking_id}"
        context = SimpleNamespace(
            user_data={
                message_data_key: {
                    "body_text": "body",
                    "source_inputted_text": "610 dinar wine",
                    "saved_to_sheets": True,
                    "list_name": ListName.expenses,
                }
            }
        )

        with patch.object(
            server,
            "delete_row_by_telegram_id",
            side_effect=GoogleWriteOutcomeUnknownError("unknown"),
        ) as delete, patch.object(
            server,
            "edit_message",
            new=AsyncMock(),
        ) as edit_message:
            await server.operation_button_handler(
                SimpleNamespace(callback_query=query),
                context,
            )

        delete.assert_called_once_with(ListName.expenses, tracking_id)
        status = edit_message.await_args.kwargs["status"]
        self.assertEqual(
            status,
            "Результат удаления неизвестен. Проверьте Google Sheets.",
        )
        self.assertNotIn("не найдена", status)
        self.assertIn(message_data_key, context.user_data)

    async def test_delete_callback_reports_api_failure_without_not_found(self):
        tracking_id = "-1001001:456:1"
        message = SimpleNamespace(message_id=999, reply_markup=None)
        query = SimpleNamespace(
            answer=AsyncMock(),
            message=message,
            data=f"delete_confirm_{tracking_id}",
        )
        message_data_key = f"msg_{tracking_id}"
        context = SimpleNamespace(
            user_data={
                message_data_key: {
                    "body_text": "body",
                    "source_inputted_text": "610 dinar wine",
                    "saved_to_sheets": True,
                    "list_name": ListName.expenses,
                }
            }
        )

        with patch.object(
            server,
            "delete_row_by_telegram_id",
            side_effect=TimeoutError("read failed"),
        ) as delete, patch.object(
            server,
            "edit_message",
            new=AsyncMock(),
        ) as edit_message:
            await server.operation_button_handler(
                SimpleNamespace(callback_query=query),
                context,
            )

        delete.assert_called_once_with(ListName.expenses, tracking_id)
        status = edit_message.await_args.kwargs["status"]
        self.assertIn("Не удалось удалить", status)
        self.assertNotIn("не найдена", status)
        self.assertIn(message_data_key, context.user_data)


class VoiceOperationSnapshotTests(unittest.IsolatedAsyncioTestCase):
    async def test_no_cache_stops_before_download_openai_and_write(self):
        processing_message = SimpleNamespace(message_id=123)
        update = SimpleNamespace(
            message=SimpleNamespace(reply_text=AsyncMock(return_value=processing_message))
        )
        context = SimpleNamespace(user_data={})

        with patch.object(
            server,
            "get_finance_config",
            side_effect=FinanceConfigUnavailableError("unavailable"),
        ), patch.object(
            server,
            "get_memory_context",
        ) as memory_context, patch.object(
            server,
            "get_text_from_audio",
            new=AsyncMock(),
        ) as get_text, patch.object(
            server,
            "_request_openai_data",
        ) as openai_request, patch.object(
            server,
            "_write_finance_operation",
            new=AsyncMock(),
        ) as write, patch.object(
            server,
            "edit_message",
            new=AsyncMock(),
        ):
            await server.voice_message_handler(update, context)

        memory_context.assert_not_called()
        get_text.assert_not_awaited()
        openai_request.assert_not_called()
        write.assert_not_awaited()

    async def test_stale_snapshot_warns_and_continues(self):
        current = config_snapshot()
        processing_message = SimpleNamespace(message_id=123)
        reply_text = AsyncMock(return_value=processing_message)
        update = SimpleNamespace(message=SimpleNamespace(reply_text=reply_text))
        context = SimpleNamespace(user_data={})

        with patch.object(
            server,
            "get_finance_config",
            return_value=FinanceConfigResult(
                snapshot=current,
                used_stale=True,
                refresh_error="timeout",
            ),
        ), patch.object(
            server,
            "get_memory_context",
            return_value="",
        ), patch.object(
            server,
            "get_text_from_audio",
            new=AsyncMock(return_value="voice text"),
        ) as get_text, patch.object(
            server,
            "_request_openai_data",
            return_value={"operations": []},
        ), patch.object(
            server,
            "edit_message",
            new=AsyncMock(),
        ):
            await server.voice_message_handler(update, context)

        self.assertEqual(reply_text.await_count, 2)
        self.assertIn(
            "последнюю успешную версию",
            reply_text.await_args_list[1].args[0],
        )
        get_text.assert_awaited_once()

    async def test_multi_operation_reuses_snapshot_memory_and_unique_tracking_ids(self):
        current = config_snapshot()
        formats = ResponseFormat(current)
        processing_message = SimpleNamespace(message_id=123)
        second_operation_message = SimpleNamespace(message_id=124)
        reply_text = AsyncMock(
            side_effect=[processing_message, second_operation_message]
        )
        update = SimpleNamespace(
            message=SimpleNamespace(
                chat_id=-1001001,
                message_id=456,
                reply_text=reply_text,
            )
        )
        context = SimpleNamespace(user_data={})
        finance_response = {
            "operations": [
                {
                    "user_request_is_relevant": True,
                    "operation_type": "Расходы",
                    "source_inputted_text": "610 dinar wine",
                    "message_to_user": "ok",
                },
                {
                    "user_request_is_relevant": True,
                    "operation_type": "Расходы",
                    "source_inputted_text": "200 dinar food",
                    "message_to_user": "ok",
                }
            ]
        }
        wine_response = {
            "expenses_category": "Wine",
            "account": "Cash",
            "amount": 610,
            "status": "Committed",
            "comment": "wine",
            "final_answer": "ok",
        }
        food_response = {
            "expenses_category": "Food",
            "account": "Cash",
            "amount": 200,
            "status": "Committed",
            "comment": "food",
            "final_answer": "ok",
        }

        with patch.object(
            server,
            "get_finance_config",
            return_value=FinanceConfigResult(snapshot=current),
        ), patch.object(
            server,
            "get_memory_context",
            return_value="memory-context",
        ) as memory_context, patch.object(
            server,
            "_write_finance_operation",
            new=AsyncMock(side_effect=[True, True]),
        ) as write, patch.object(
            server,
            "get_reply_keyboard_markup",
        ) as confirmation_keyboard, patch.object(
            server,
            "get_delete_button_keyboard",
            wraps=server.get_delete_button_keyboard,
        ) as delete_keyboard, patch.object(
            server,
            "get_text_from_audio",
            new=AsyncMock(return_value="610 dinar wine"),
        ) as get_text, patch.object(
            server,
            "ResponseFormat",
            return_value=formats,
        ) as response_format, patch.object(
            server,
            "_request_openai_data",
            side_effect=[finance_response, wine_response, food_response],
        ) as openai_request, patch.object(
            server,
            "clarify_request_message",
            wraps=server.clarify_request_message,
        ) as clarify, patch.object(
            server,
            "edit_message",
            new=AsyncMock(),
        ) as edit_message:
            await server.voice_message_handler(update, context)

        self.assertIs(get_text.await_args.args[3], current)
        memory_context.assert_called_once_with()
        response_format.assert_called_once_with(current)
        self.assertEqual(clarify.call_count, 2)
        self.assertTrue(
            all(call.args[1] is current for call in clarify.call_args_list)
        )
        self.assertIs(
            openai_request.call_args_list[0].args[1],
            formats.finance_operation_response,
        )
        self.assertIs(
            openai_request.call_args_list[1].args[1],
            formats.expenses_response_format,
        )
        self.assertIs(
            openai_request.call_args_list[2].args[1],
            formats.expenses_response_format,
        )
        self.assertTrue(
            all(
                call.args[3] == "memory-context"
                for call in openai_request.call_args_list
            )
        )
        tracking_ids = [call.args[0].telegram_message_id for call in write.await_args_list]
        self.assertEqual(
            tracking_ids,
            ["-1001001:456:1", "-1001001:456:2"],
        )
        confirmation_keyboard.assert_not_called()
        self.assertEqual(reply_text.await_count, 2)
        self.assertIn("следующую операцию", reply_text.await_args_list[1].args[0])
        self.assertEqual(
            [call.args[0] for call in delete_keyboard.call_args_list],
            ["-1001001:456:1", "-1001001:456:2"],
        )
        final_calls = [
            call
            for call in edit_message.await_args_list
            if call.kwargs.get("status") == "✅ Сохранено в Google Sheets"
        ]
        self.assertEqual(len(final_calls), 2)
        self.assertIs(final_calls[0].kwargs["message"], processing_message)
        self.assertIs(
            final_calls[1].kwargs["message"],
            second_operation_message,
        )
        callback_data = [
            call.kwargs["reply_markup"].inline_keyboard[0][0].callback_data
            for call in final_calls
        ]
        self.assertEqual(
            callback_data,
            ["delete_-1001001:456:1", "delete_-1001001:456:2"],
        )


if __name__ == "__main__":
    unittest.main()
