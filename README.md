# SaveView

Mobilvenligt dashboard til overblik over opsparing fra CSV-filer.

## Funktioner
- Viser opsparing pr. kategori (baseret på kolonnen `Tekst`).
- Viser udvikling i total saldo over tid.
- Viser udvikling i opsparing pr. kategori over tid.
- Behandler kategorier case-insensitivt.
- Mapper ukendte kategorier til `Øvrig opsparing`.
- Viser tydelig advarsel i appen, hvis et filnavn ikke matcher forventet mønster.

## Kategorier
Standardkategorier:
- `bilopsparing`
- `Ferieopsparing`

Kan tilpasses via miljøvariablen `SAVEVIEW_CATEGORIES` (kommasepareret).

## Datakilder
Appen kan læse data fra:
1. Lokal mappe (default): `sample_data`
2. Dropbox via `rclone` ved at sætte `SAVEVIEW_DROPBOX_REMOTE`

Eksempel for Dropbox:
```bash
export SAVEVIEW_DROPBOX_REMOTE='dropbox:/TEAM_FOLDER/Opsparing'
python3 app.py
```

## Kørsel lokalt
```bash
python3 app.py
```

Appen kører på port `8080` som standard (kan ændres med `PORT`).

## Miljøvariabler
- `PORT` (default `8080`)
- `SAVEVIEW_DATA_DIR` (default `sample_data`) — **lokal mappe eller lokal filsti**
- `SAVEVIEW_DROPBOX_REMOTE` (valgfri, aktiverer Dropbox-læsning via rclone)
- `SAVEVIEW_CATEGORIES` (default `bilopsparing,Ferieopsparing`)

> Vigtigt: `SAVEVIEW_DATA_DIR` er kun til lokale stier. Dropbox-stier (`dropbox:/...`) skal sættes i `SAVEVIEW_DROPBOX_REMOTE`.

## Drift med systemd (Raspberry Pi)
Hvis appen kører som service, anbefales følgende unit-fil:

```ini
# /etc/systemd/system/saveview.service
[Unit]
Description=SaveView
After=network.target

[Service]
Type=simple
User=alex
Group=alex
WorkingDirectory=/home/alex/SaveView
EnvironmentFile=/etc/saveview.env
ExecStart=/home/alex/SaveView/.venv/bin/python /home/alex/SaveView/app.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### Eksempel på `/etc/saveview.env`
```env
PORT=8080
SAVEVIEW_DROPBOX_REMOTE="dropbox:/TEAM_FOLDER/Opsparing"
# SAVEVIEW_DATA_DIR=sample_data
SAVEVIEW_CATEGORIES=bilopsparing,Ferieopsparing
```

Efter ændringer i service-konfiguration:
```bash
sudo systemctl daemon-reload
sudo systemctl restart saveview
sudo systemctl status saveview --no-pager -l
```

## Fejlsøgning

### 1) HTTP 500 fra `/api/dashboard`
Hent den fulde fejl direkte fra API'et:
```bash
curl -i http://127.0.0.1:8080/api/dashboard
```

Typisk årsag: forkert miljøvariabel (fx `SAVEVIEW_DATA_DIR='dropbox:/...'`).

### 2) `Datamappen findes ikke ...`
- Kontrollér værdien af `SAVEVIEW_DATA_DIR`.
- Brug kun lokal sti i `SAVEVIEW_DATA_DIR`.
- Brug `SAVEVIEW_DROPBOX_REMOTE` til Dropbox.

Hvis appen kører som service:
```bash
sudo systemctl show saveview --property=Environment
sudo systemctl show saveview --property=EnvironmentFiles
sudo cat /etc/saveview.env
```

### 3) `OSError: [Errno 98] Address already in use`
Porten er allerede i brug.

Find processen:
```bash
sudo lsof -i :8080
```

Eller start SaveView på en anden port:
```bash
PORT=8081 python3 app.py
```

### 4) Verificér Dropbox/rclone
```bash
which rclone
rclone lsf "$SAVEVIEW_DROPBOX_REMOTE"
```

Hvis `rclone lsf` fejler, er problemet i rclone-opsætning/credentials eller remote-navn.
