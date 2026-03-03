import os
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path

import app
from http.server import ThreadingHTTPServer


class SaveViewDataDirTests(unittest.TestCase):
    def setUp(self):
        self._old_data_dir = os.environ.get("SAVEVIEW_DATA_DIR")

    def tearDown(self):
        if self._old_data_dir is None:
            os.environ.pop("SAVEVIEW_DATA_DIR", None)
        else:
            os.environ["SAVEVIEW_DATA_DIR"] = self._old_data_dir

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


class ApiRouteCompatibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), app.SaveViewHandler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)

    def test_dashboard_and_data_routes_both_work(self):
        for route in ("/api/dashboard", "/api/data"):
            with urllib.request.urlopen(f"http://127.0.0.1:{self.port}{route}") as response:
                self.assertEqual(response.status, 200)
                body = response.read().decode("utf-8")
                self.assertIn('"opsparingPrKategori"', body)


if __name__ == "__main__":
    unittest.main()
