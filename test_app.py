import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app


CSV_HEADER = "Dato;Tekst;Bel\u00f8b;Saldo\n"
AMOUNT_KEY = "bel\u00f8b"


class SaveViewDataDirTests(unittest.TestCase):
    def setUp(self):
        self._old_data_dir = os.environ.get("SAVEVIEW_DATA_DIR")
        self._old_dropbox_remote = os.environ.get("SAVEVIEW_DROPBOX_REMOTE")

    def tearDown(self):
        if self._old_data_dir is None:
            os.environ.pop("SAVEVIEW_DATA_DIR", None)
        else:
            os.environ["SAVEVIEW_DATA_DIR"] = self._old_data_dir
        if self._old_dropbox_remote is None:
            os.environ.pop("SAVEVIEW_DROPBOX_REMOTE", None)
        else:
            os.environ["SAVEVIEW_DROPBOX_REMOTE"] = self._old_dropbox_remote

    def test_read_csv_content_when_data_dir_points_to_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "single.csv"
            csv_content = CSV_HEADER + "01.01.2026;bilopsparing;1.000,00;1.000,00\n"
            csv_path.write_text(csv_content, encoding="utf-8")

            os.environ["SAVEVIEW_DATA_DIR"] = str(csv_path)

            files, source = app.list_input_files()
            self.assertEqual(source, "local")
            self.assertEqual(files, ["single.csv"])

            loaded = app.read_csv_content(source, files[0])
            self.assertEqual(loaded.splitlines(), csv_content.splitlines())

    def test_read_csv_content_when_data_dir_points_to_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            csv_path = data_dir / "month.csv"
            csv_content = CSV_HEADER + "01.01.2026;Ferieopsparing;2.000,00;2.000,00\n"
            csv_path.write_text(csv_content, encoding="utf-8")

            os.environ["SAVEVIEW_DATA_DIR"] = str(data_dir)

            files, source = app.list_input_files()
            self.assertEqual(source, "local")
            self.assertEqual(files, ["month.csv"])

            loaded = app.read_csv_content(source, "month.csv")
            self.assertEqual(loaded.splitlines(), csv_content.splitlines())

    def test_dropbox_failure_falls_back_to_local_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            (data_dir / "month.csv").write_text(
                CSV_HEADER + "01.01.2026;Ferieopsparing;2.000,00;2.000,00\n", encoding="utf-8"
            )
            os.environ["SAVEVIEW_DATA_DIR"] = str(data_dir)
            os.environ["SAVEVIEW_DROPBOX_REMOTE"] = "dropbox:/Opsparing"

            with patch("app.subprocess.run", side_effect=FileNotFoundError("rclone")):
                files, source = app.list_input_files()

            self.assertEqual(source, "local")
            self.assertEqual(files, ["month.csv"])

    def test_dropbox_failure_raises_error_without_local_fallback(self):
        os.environ["SAVEVIEW_DATA_DIR"] = "/tmp/does-not-exist-saveview"
        os.environ["SAVEVIEW_DROPBOX_REMOTE"] = "dropbox:/Opsparing"

        with patch("app.subprocess.run", side_effect=subprocess.CalledProcessError(1, ["rclone", "lsf"])):
            with self.assertRaises(RuntimeError) as ctx:
                app.list_input_files()

        self.assertIn("Kunne ikke hente filer fra Dropbox via rclone", str(ctx.exception))


class SaveViewAggregationTests(unittest.TestCase):
    def setUp(self):
        self._old_data_dir = os.environ.get("SAVEVIEW_DATA_DIR")

    def tearDown(self):
        if self._old_data_dir is None:
            os.environ.pop("SAVEVIEW_DATA_DIR", None)
        else:
            os.environ["SAVEVIEW_DATA_DIR"] = self._old_data_dir

    def test_total_balance_matches_sum_of_categories(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            (data_dir / "month.csv").write_text(
                CSV_HEADER
                + "01.01.2026;Bilopsparing;1.000,00;15.000,00\n"
                + "05.01.2026;Ferieopsparing;500,00;15.500,00\n",
                encoding="utf-8",
            )
            os.environ["SAVEVIEW_DATA_DIR"] = str(data_dir)

            result = app.load_transactions()

            category_sum = round(sum(item[AMOUNT_KEY] for item in result["opsparingPrKategori"]), 2)
            self.assertEqual(result["totalSaldo"], category_sum)

    def test_balance_series_uses_running_total_not_csv_balance(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            (data_dir / "month.csv").write_text(
                CSV_HEADER
                + "01.01.2026;Bilopsparing;1.000,00;not-a-balance\n"
                + "05.01.2026;Ferieopsparing;500,00;50.000,00\n"
                + "10.01.2026;Bilopsparing;-200,00;75.000,00\n",
                encoding="utf-8",
            )
            os.environ["SAVEVIEW_DATA_DIR"] = str(data_dir)

            result = app.load_transactions()

            self.assertEqual(
                result["saldoUdvikling"],
                [
                    {"dato": "2026-01-01", "saldo": 1000.0},
                    {"dato": "2026-01-05", "saldo": 1500.0},
                    {"dato": "2026-01-10", "saldo": 1300.0},
                ],
            )

    def test_default_categories_include_outdoor(self):
        os.environ.pop("SAVEVIEW_CATEGORIES", None)
        self.assertEqual(app.get_categories(), ["Bilopsparing", "Ferieopsparing", "Outdoor"])


if __name__ == "__main__":
    unittest.main()
