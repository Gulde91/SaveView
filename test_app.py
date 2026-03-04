import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app


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
            csv_content = "Dato;Tekst;Beløb;Saldo\n01.01.2026;bilopsparing;1.000,00;1.000,00\n"
            csv_path.write_text(csv_content, encoding="utf-8")

            os.environ["SAVEVIEW_DATA_DIR"] = str(csv_path)

            files, source = app.list_input_files()
            self.assertEqual(source, "local")
            self.assertEqual(files, ["single.csv"])

            loaded = app.read_csv_content(source, files[0])
            self.assertEqual(loaded, csv_content)

    def test_read_csv_content_when_data_dir_points_to_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            csv_path = data_dir / "month.csv"
            csv_content = "Dato;Tekst;Beløb;Saldo\n01.01.2026;Ferieopsparing;2.000,00;2.000,00\n"
            csv_path.write_text(csv_content, encoding="utf-8")

            os.environ["SAVEVIEW_DATA_DIR"] = str(data_dir)

            files, source = app.list_input_files()
            self.assertEqual(source, "local")
            self.assertEqual(files, ["month.csv"])

            loaded = app.read_csv_content(source, "month.csv")
            self.assertEqual(loaded, csv_content)

    def test_dropbox_failure_falls_back_to_local_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            (data_dir / "month.csv").write_text(
                "Dato;Tekst;Beløb;Saldo\n01.01.2026;Ferieopsparing;2.000,00;2.000,00\n", encoding="utf-8"
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


if __name__ == "__main__":
    unittest.main()
