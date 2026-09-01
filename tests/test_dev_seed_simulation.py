import unittest
from datetime import date
from unittest.mock import patch

from src import dev_seed
from src.dev_seed import (
    DataOverrides,
    SimulationConfig,
    SimulationResult,
    date_to_serial,
    sheet_serial_to_date,
    simulate_dev_history,
)
from lib.utilities.google_utilities import ListName, TransferType


class DevSeedSimulationTests(unittest.TestCase):
    def setUp(self):
        self.overrides = DataOverrides(
            accounts=["ACC1", "ACC2", "ACC3"],
            expense_categories=["Продукты", "Еда вне дома"],
            income_categories=["Зарплата"],
        )
        self.config = SimulationConfig(
            active_prob_weekday=0.9,
            active_prob_weekend=0.9,
            daily_ops_min=4,
            daily_ops_max=5,
            monthly_salary_min=100_000,
            monthly_salary_max=120_000,
        )
        self.start = date(2023, 1, 1)
        self.end = date(2023, 1, 10)

    def test_date_roundtrip(self):
        serial = date_to_serial(self.start)
        self.assertEqual(sheet_serial_to_date(serial), self.start)

    def test_deterministic_simulation(self):
        sim1 = simulate_dev_history(
            seed=42,
            start_date=self.start,
            end_date=self.end,
            config=self.config,
            overrides=self.overrides,
        )
        sim2 = simulate_dev_history(
            seed=42,
            start_date=self.start,
            end_date=self.end,
            config=self.config,
            overrides=self.overrides,
        )

        self.assertEqual(len(sim1.transactions), len(sim2.transactions))
        snapshot1 = [
            (
                tx.list_name,
                tx.date,
                getattr(tx, "amount", None),
                getattr(tx, "expenses_category", None),
                getattr(tx, "incomes_category", None),
                getattr(tx, "transfer_type", None),
                getattr(tx, "account", None),
                getattr(tx, "replenishment_account", None),
            )
            for tx in sim1.transactions
        ]
        snapshot2 = [
            (
                tx.list_name,
                tx.date,
                getattr(tx, "amount", None),
                getattr(tx, "expenses_category", None),
                getattr(tx, "incomes_category", None),
                getattr(tx, "transfer_type", None),
                getattr(tx, "account", None),
                getattr(tx, "replenishment_account", None),
            )
            for tx in sim2.transactions
        ]
        self.assertEqual(snapshot1, snapshot2)

    def test_adjustment_rules(self):
        sim = simulate_dev_history(
            seed=7,
            start_date=self.start,
            end_date=self.end,
            config=self.config,
            overrides=self.overrides,
        )
        adjustments = [
            tx
            for tx in sim.transactions
            if tx.list_name == ListName.transfers and tx.transfer_type == TransferType.adjustment
        ]
        self.assertGreater(len(adjustments), 0)
        for tx in adjustments:
            self.assertEqual(tx.amount, 0)
            self.assertEqual(tx.account, tx.replenishment_account)
            self.assertIsNotNone(tx.replenishment_amount)

    def test_generates_multiple_dates(self):
        sim = simulate_dev_history(
            seed=9,
            start_date=self.start,
            end_date=date(2023, 1, 15),
            config=self.config,
            overrides=self.overrides,
        )
        unique_dates = {tx.date for tx in sim.transactions}
        self.assertGreater(len(unique_dates), 3)

    def test_salary_present(self):
        sim = simulate_dev_history(
            seed=11,
            start_date=self.start,
            end_date=date(2023, 3, 1),
            config=self.config,
            overrides=self.overrides,
        )
        incomes = [tx for tx in sim.transactions if tx.list_name == ListName.incomes]
        self.assertGreater(len(incomes), 1)  # минимум две зарплаты за два месяца

    def test_no_negative_ledger(self):
        sim = simulate_dev_history(
            seed=13,
            start_date=self.start,
            end_date=date(2023, 2, 28),
            config=self.config,
            overrides=self.overrides,
        )
        self.assertTrue(all(v >= 0 for v in sim.ledger_summary.values()))

    def test_expenses_and_transfers_present(self):
        sim = simulate_dev_history(
            seed=17,
            start_date=self.start,
            end_date=date(2023, 1, 31),
            config=self.config,
            overrides=self.overrides,
        )
        expenses = [tx for tx in sim.transactions if tx.list_name == ListName.expenses]
        transfers = [tx for tx in sim.transactions if tx.list_name == ListName.transfers]
        self.assertGreater(len(expenses), 0)
        self.assertGreater(len(transfers), 0)

    def test_apply_uses_fresh_batch_update_seam(self):
        transaction = dev_seed.RequestData(
            list_name=ListName.expenses,
            expenses_category="Продукты",
            account="ACC1",
            amount=100,
        )
        simulation = SimulationResult(
            run_id="test-run",
            seed=1,
            transactions=[transaction],
            ledger_summary={},
        )
        insert_request = {"insert": True}
        update_request = {"update": True}

        with patch.object(dev_seed, "ensure_min_rows"), patch.object(
            dev_seed,
            "get_insert_row_above_request",
            return_value=insert_request,
        ), patch.object(
            dev_seed,
            "get_update_cells_request",
            return_value=update_request,
        ), patch.object(
            dev_seed,
            "batch_update",
        ) as batch_update:
            report = dev_seed.apply_dev_history(simulation, reset=False)

        batch_update.assert_called_once_with(
            {"requests": [insert_request, update_request]}
        )
        self.assertEqual(report.inserted, 1)
        self.assertEqual(report.batches_sent, 1)


if __name__ == "__main__":
    unittest.main()
