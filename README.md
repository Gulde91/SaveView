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
export SAVEVIEW_DROPBOX_REMOTE='dropbox:/Alexander & Camilla/Opsparing'
python3 app.py
```

## Kørsel
```bash
python3 app.py
```

Appen kører på port `8080` som standard (kan ændres med `PORT`).

## Miljøvariabler
- `PORT` (default `8080`)
- `SAVEVIEW_DATA_DIR` (default `sample_data`)
- `SAVEVIEW_DROPBOX_REMOTE` (valgfri, aktiverer Dropbox-læsning via rclone)
- `SAVEVIEW_CATEGORIES` (default `bilopsparing,Ferieopsparing`)
