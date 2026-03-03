from __future__ import annotations

import csv
import io
import json
import os
import re
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

FILENAME_PATTERN = re.compile(r"^\d+_\d{4}\.\d{2}\.\d{2}-\d{4}\.\d{2}\.\d{2}(?:\.[A-Za-z0-9]+)?$")
DATE_FORMAT = "%d.%m.%Y"
BASE_DIR = Path(__file__).parent


def parse_danish_decimal(value: str) -> float:
    clean = value.strip().replace(".", "").replace(",", ".")
    return float(clean)


def decode_csv_bytes(raw: bytes, filename: str) -> str:
    for encoding in ("utf-8", "cp1252", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise RuntimeError(f"Filen {filename} kunne ikke dekodes som tekst")


def normalize_category(raw_text: str, configured_categories: list[str]) -> str:
    value = raw_text.strip().lower()
    for category in configured_categories:
        if value == category.lower():
            return category
    return "Øvrig opsparing"


@dataclass
class Transaction:
    date: datetime
    text: str
    amount: float
    balance: float


def get_categories() -> list[str]:
    configured = os.getenv("SAVEVIEW_CATEGORIES", "bilopsparing,Ferieopsparing")
    return [entry.strip() for entry in configured.split(",") if entry.strip()]


def resolve_local_data_dir() -> Path:
    configured = os.getenv("SAVEVIEW_DATA_DIR", "sample_data")
    expanded = Path(os.path.expandvars(configured)).expanduser()
    if expanded.is_absolute():
        return expanded
    return (BASE_DIR / expanded).resolve()


def list_input_files() -> tuple[list[str], str]:
    dropbox_remote = os.getenv("SAVEVIEW_DROPBOX_REMOTE")

    if dropbox_remote:
        try:
            result = subprocess.run(["rclone", "lsf", dropbox_remote], check=True, capture_output=True, text=True)
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            raise RuntimeError(f"Kunne ikke hente filer fra Dropbox via rclone: {exc}") from exc
        files = [line.strip() for line in result.stdout.splitlines() if line.strip() and not line.endswith("/")]
        return files, "dropbox"

    data_path = resolve_local_data_dir()
    if not data_path.exists():
        configured = os.getenv("SAVEVIEW_DATA_DIR", "sample_data")
        raise RuntimeError(
            f"Datamappen findes ikke: {data_path} (SAVEVIEW_DATA_DIR={configured!r}, BASE_DIR={BASE_DIR})"
        )
    if data_path.is_file():
        return [data_path.name], "local"
    files = sorted([entry.name for entry in data_path.iterdir() if entry.is_file()])
    return files, "local"


def read_csv_content(source: str, filename: str) -> str:
    if source == "dropbox":
        remote = os.getenv("SAVEVIEW_DROPBOX_REMOTE")
        if not remote:
            raise RuntimeError("Dropbox remote er ikke konfigureret")
        path = f"{remote.rstrip('/')}/{filename}"
        try:
            result = subprocess.run(["rclone", "cat", path], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            raise RuntimeError(f"Kunne ikke læse filen {filename}: {exc}") from exc
        return decode_csv_bytes(result.stdout, filename)

    local_dir = resolve_local_data_dir()
    return decode_csv_bytes((local_dir / filename).read_bytes(), filename)


def load_transactions() -> dict:
    categories = get_categories()
    files, source = list_input_files()
    invalid_filenames = []
    transactions: list[Transaction] = []

    for filename in files:
        if not FILENAME_PATTERN.match(filename):
            invalid_filenames.append(filename)

        content = read_csv_content(source, filename)
        reader = csv.DictReader(io.StringIO(content), delimiter=";")
        for row in reader:
            if not row.get("Dato") or not row.get("Tekst"):
                continue
            try:
                tx_date = datetime.strptime(row["Dato"], DATE_FORMAT)
                amount = parse_danish_decimal(row["Beløb"])
                balance = parse_danish_decimal(row["Saldo"])
            except (ValueError, KeyError):
                continue
            mapped = normalize_category(row["Tekst"], categories)
            transactions.append(Transaction(date=tx_date, text=mapped, amount=amount, balance=balance))

    transactions.sort(key=lambda item: item.date)

    totals_per_category = defaultdict(float)
    for tx in transactions:
        totals_per_category[tx.text] += tx.amount

    balance_series = [{"dato": tx.date.strftime("%Y-%m-%d"), "saldo": round(tx.balance, 2)} for tx in transactions]

    tracked_categories = sorted(set(categories + ["Øvrig opsparing"]))
    per_category_progress = defaultdict(float)
    category_series_map: dict[str, list[dict]] = defaultdict(list)
    for tx in transactions:
        per_category_progress[tx.text] += tx.amount
        for category in tracked_categories:
            category_series_map[category].append(
                {"dato": tx.date.strftime("%Y-%m-%d"), "værdi": round(per_category_progress.get(category, 0.0), 2)}
            )

    return {
        "antalTransaktioner": len(transactions),
        "kategorier": tracked_categories,
        "opsparingPrKategori": [
            {"kategori": name, "beløb": round(totals_per_category.get(name, 0.0), 2)} for name in tracked_categories
        ],
        "saldoUdvikling": balance_series,
        "kategoriUdvikling": category_series_map,
        "ugyldigeFiler": invalid_filenames,
        "datakilde": source,
    }


class SaveViewHandler(BaseHTTPRequestHandler):
    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path, content_type: str) -> None:
        if not path.exists():
            self.send_error(404)
            return
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        route = urlparse(self.path).path
        if route == "/":
            self._send_file(BASE_DIR / "templates" / "index.html", "text/html; charset=utf-8")
            return
        if route == "/api/dashboard":
            try:
                self._send_json(load_transactions())
            except RuntimeError as exc:
                self._send_json({"fejl": str(exc)}, status=500)
            return
        if route == "/static/styles.css":
            self._send_file(BASE_DIR / "static" / "styles.css", "text/css; charset=utf-8")
            return
        if route == "/static/app.js":
            self._send_file(BASE_DIR / "static" / "app.js", "application/javascript; charset=utf-8")
            return

        self.send_error(404)


def main() -> None:
    port = int(os.getenv("PORT", "8080"))
    server = ThreadingHTTPServer(("0.0.0.0", port), SaveViewHandler)
    print(f"SaveView kører på port {port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
