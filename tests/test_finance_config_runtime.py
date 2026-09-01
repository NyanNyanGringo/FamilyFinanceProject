import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import httplib2

from lib.utilities import google_utilities
from lib.utilities.google_utilities import (
    ConfigRange,
    FinanceConfigCache,
    FinanceConfigSnapshot,
    FinanceConfigUnavailableError,
    GoogleWriteOutcomeUnknownError,
)


def snapshot(name: str) -> FinanceConfigSnapshot:
    return FinanceConfigSnapshot(
        expenses=(f"expense-{name}",),
        incomes=(f"income-{name}",),
        accounts=(f"account-{name}",),
        loaded_at=datetime(2026, 8, 11, 12, 0, tzinfo=timezone.utc),
    )


class FinanceConfigCacheTests(unittest.TestCase):
    def test_snapshot_is_immutable(self):
        current = snapshot("one")

        with self.assertRaises(FrozenInstanceError):
            current.expenses = ("changed",)

    def test_ttl_uses_monotonic_clock_and_replaces_snapshot_atomically(self):
        clock = [100.0]
        snapshots = [snapshot("one"), snapshot("two")]
        loader_calls = []

        def loader():
            loader_calls.append(True)
            return snapshots[len(loader_calls) - 1]

        cache = FinanceConfigCache(
            loader=loader,
            ttl_seconds=300,
            monotonic=lambda: clock[0],
        )

        first = cache.get()
        clock[0] = 399.9
        cached = cache.get()
        clock[0] = 400.0
        refreshed = cache.get()

        self.assertIs(first.snapshot, snapshots[0])
        self.assertIs(cached.snapshot, snapshots[0])
        self.assertIs(refreshed.snapshot, snapshots[1])
        self.assertEqual(len(loader_calls), 2)

    def test_failed_refresh_returns_last_known_good_snapshot(self):
        current = snapshot("good")
        loader_calls = 0

        def loader():
            nonlocal loader_calls
            loader_calls += 1
            if loader_calls == 1:
                return current
            raise TimeoutError("temporary timeout")

        cache = FinanceConfigCache(loader=loader, ttl_seconds=300)
        cache.get()

        result = cache.get(force_refresh=True)

        self.assertIs(result.snapshot, current)
        self.assertTrue(result.used_stale)
        self.assertEqual(result.refresh_error, "temporary timeout")

    def test_failed_initial_load_raises_typed_error(self):
        cache = FinanceConfigCache(
            loader=lambda: (_ for _ in ()).throw(TimeoutError("timeout"))
        )

        with self.assertRaises(FinanceConfigUnavailableError) as raised:
            cache.get()

        self.assertIsInstance(raised.exception.__cause__, TimeoutError)

    def test_concurrent_cache_miss_loads_once(self):
        loader_calls = 0
        loader_lock = threading.Lock()
        current = snapshot("shared")

        def loader():
            nonlocal loader_calls
            with loader_lock:
                loader_calls += 1
            time.sleep(0.03)
            return current

        cache = FinanceConfigCache(loader=loader, ttl_seconds=300)

        with ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(lambda _: cache.get(), range(8)))

        self.assertEqual(loader_calls, 1)
        self.assertTrue(all(result.snapshot is current for result in results))


class GoogleReadExecutionTests(unittest.TestCase):
    def test_transient_timeout_retries_with_fresh_service(self):
        execute_calls = 0
        services = []

        class Request:
            def execute(self, num_retries):
                nonlocal execute_calls
                execute_calls += 1
                self.assert_num_retries = num_retries
                if execute_calls < 3:
                    raise TimeoutError("timeout")
                return {"ok": True}

        class Service:
            def __init__(self):
                self.request = Request()
                self.closed = False

            def close(self):
                self.closed = True

        def build_service(timeout_seconds):
            self.assertEqual(
                timeout_seconds,
                google_utilities.GOOGLE_READ_TIMEOUT_SECONDS,
            )
            service = Service()
            services.append(service)
            return service

        with patch.object(google_utilities, "_build_service", side_effect=build_service), patch.object(
            google_utilities.time,
            "sleep",
        ) as sleep:
            result = google_utilities._execute_read(lambda service: service.request)

        self.assertEqual(result, {"ok": True})
        self.assertEqual(execute_calls, 3)
        self.assertEqual(len(services), 3)
        self.assertTrue(all(service.closed for service in services))
        self.assertEqual(sleep.call_args_list[0].args, (0.5,))
        self.assertEqual(sleep.call_args_list[1].args, (1.0,))
        self.assertTrue(
            all(service.request.assert_num_retries == 0 for service in services)
        )

    def test_http_408_429_and_5xx_are_transient(self):
        def error(status):
            response = httplib2.Response({"status": str(status), "reason": "test"})
            return google_utilities.HttpError(response, b"error")

        self.assertTrue(google_utilities._is_transient_google_error(error(408)))
        self.assertTrue(google_utilities._is_transient_google_error(error(429)))
        self.assertTrue(google_utilities._is_transient_google_error(error(503)))
        self.assertFalse(google_utilities._is_transient_google_error(error(400)))
        self.assertFalse(
            google_utilities._is_transient_google_error(
                httplib2.RelativeURIError("invalid URI")
            )
        )

    def test_non_transient_error_is_not_retried(self):
        service = MagicMock()
        request = MagicMock()
        request.execute.side_effect = ValueError("invalid range")

        with patch.object(google_utilities, "_build_service", return_value=service) as build_service, patch.object(
            google_utilities.time,
            "sleep",
        ) as sleep:
            with self.assertRaisesRegex(ValueError, "invalid range"):
                google_utilities._execute_read(lambda _: request)

        build_service.assert_called_once()
        sleep.assert_not_called()

    def test_transient_read_failure_stops_after_three_attempts(self):
        services = []

        def build_service(_):
            service = MagicMock()
            service.request.execute.side_effect = TimeoutError("timeout")
            services.append(service)
            return service

        with patch.object(
            google_utilities,
            "_build_service",
            side_effect=build_service,
        ), patch.object(google_utilities.time, "sleep") as sleep:
            with self.assertRaisesRegex(TimeoutError, "timeout"):
                google_utilities._execute_read(lambda service: service.request)

        self.assertEqual(len(services), 3)
        self.assertEqual(sleep.call_count, 2)
        self.assertTrue(
            all(service.request.execute.call_count == 1 for service in services)
        )

    def test_write_does_not_retry_ambiguous_timeout(self):
        service = MagicMock()
        request = MagicMock()
        request.execute.side_effect = TimeoutError("unknown write outcome")

        with patch.object(google_utilities, "_build_service", return_value=service) as build_service:
            with self.assertRaises(GoogleWriteOutcomeUnknownError) as raised:
                google_utilities._execute_write(lambda _: request)

        self.assertIsInstance(raised.exception.__cause__, TimeoutError)
        build_service.assert_called_once_with(
            google_utilities.GOOGLE_WRITE_TIMEOUT_SECONDS
        )
        request.execute.assert_called_once_with(num_retries=0)

    def test_write_factory_failure_is_not_marked_as_unknown(self):
        service = MagicMock()

        with patch.object(google_utilities, "_build_service", return_value=service):
            with self.assertRaisesRegex(ValueError, "invalid request"):
                google_utilities._execute_write(
                    lambda _: (_ for _ in ()).throw(ValueError("invalid request"))
                )

    def test_delete_propagates_read_failure(self):
        with patch.object(
            google_utilities,
            "find_rows_by_telegram_id",
            side_effect=TimeoutError("read failed"),
        ), patch.object(google_utilities, "_execute_write") as execute_write:
            with self.assertRaisesRegex(TimeoutError, "read failed"):
                google_utilities.delete_row_by_telegram_id(
                    google_utilities.ListName.expenses,
                    "tracking-id",
                )

        execute_write.assert_not_called()

    def test_delete_propagates_ambiguous_write_without_retry(self):
        with patch.object(
            google_utilities,
            "find_rows_by_telegram_id",
            return_value=(7,),
        ), patch.object(
            google_utilities,
            "_get_sheet_ids",
            return_value={str(google_utilities.ListName.expenses): 123},
        ), patch.object(
            google_utilities,
            "_execute_write",
            side_effect=GoogleWriteOutcomeUnknownError("unknown"),
        ) as execute_write:
            with self.assertRaisesRegex(GoogleWriteOutcomeUnknownError, "unknown"):
                google_utilities.delete_row_by_telegram_id(
                    google_utilities.ListName.expenses,
                    "tracking-id",
                )

        execute_write.assert_called_once()

    def test_credentials_are_loaded_once_for_fresh_services(self):
        credentials = object()

        with patch.object(
            google_utilities,
            "_CREDENTIALS",
            None,
        ), patch.object(
            google_utilities,
            "_authenticate_with_google",
            return_value=credentials,
        ) as authenticate, patch.object(
            google_utilities.google_auth_httplib2,
            "AuthorizedHttp",
            return_value=object(),
        ), patch.object(
            google_utilities.httplib2,
            "Http",
            return_value=object(),
        ), patch.object(
            google_utilities,
            "build",
            side_effect=[object(), object()],
        ):
            google_utilities._build_service(5)
            google_utilities._build_service(5)

        authenticate.assert_called_once_with()

    def test_snapshot_loader_uses_one_batch_get(self):
        service = MagicMock()
        request = service.spreadsheets.return_value.values.return_value.batchGet.return_value
        request.execute.return_value = {
            "valueRanges": [
                {"range": "'*data'!AK7:AK199", "values": [["Food"], ["Travel"]]},
                {"range": "'*data'!AL7:AL199", "values": [["Salary"]]},
                {"range": "'*data'!M7:M199", "values": [["Cash"], ["Card"]]},
            ]
        }

        with patch.object(google_utilities, "_build_service", return_value=service):
            result = google_utilities._load_finance_config_snapshot()

        self.assertEqual(result.expenses, ("Food", "Travel"))
        self.assertEqual(result.incomes, ("Salary",))
        self.assertEqual(result.accounts, ("Cash", "Card"))
        service.spreadsheets.return_value.values.return_value.batchGet.assert_called_once_with(
            spreadsheetId=google_utilities.SPREADSHEET_ID,
            ranges=[
                str(ConfigRange.expenses),
                str(ConfigRange.incomes),
                str(ConfigRange.accounts),
            ],
        )
        request.execute.assert_called_once_with(num_retries=0)

    def test_snapshot_loader_rejects_partial_batch_response(self):
        service = MagicMock()
        request = service.spreadsheets.return_value.values.return_value.batchGet.return_value
        request.execute.return_value = {
            "valueRanges": [
                {"values": [["Food"]]},
                {"values": [["Salary"]]},
            ]
        }

        with patch.object(google_utilities, "_build_service", return_value=service):
            with self.assertRaisesRegex(ValueError, "Expected 3 finance config ranges"):
                google_utilities._load_finance_config_snapshot()

        request.execute.assert_called_once_with(num_retries=0)

    def test_snapshot_loader_rejects_malformed_values_and_wrong_range(self):
        malformed_responses = [
            {"valueRanges": "not-a-list"},
            {
                "valueRanges": [
                    {"values": [[123]]},
                    {"values": [["Salary"]]},
                    {"values": [["Cash"]]},
                ]
            },
            {
                "valueRanges": [
                    {"range": "'*data'!AZ7:AZ199", "values": [["Food"]]},
                    {"values": [["Salary"]]},
                    {"values": [["Cash"]]},
                ]
            },
        ]

        for response in malformed_responses:
            with self.subTest(response=response):
                service = MagicMock()
                request = service.spreadsheets.return_value.values.return_value.batchGet.return_value
                request.execute.return_value = response
                with patch.object(
                    google_utilities,
                    "_build_service",
                    return_value=service,
                ):
                    with self.assertRaises(ValueError):
                        google_utilities._load_finance_config_snapshot()

    def test_snapshot_loader_rejects_empty_config_ranges(self):
        service = MagicMock()
        request = service.spreadsheets.return_value.values.return_value.batchGet.return_value
        request.execute.return_value = {
            "valueRanges": [
                {"values": []},
                {"values": [["Salary"]]},
                {"values": [["Cash"]]},
            ]
        }

        with patch.object(google_utilities, "_build_service", return_value=service):
            with self.assertRaisesRegex(ValueError, "incomplete finance configuration"):
                google_utilities._load_finance_config_snapshot()


if __name__ == "__main__":
    unittest.main()
