"""
Prueft bei samedi (Praxis fuer Psychotherapie Viola Berg), ob ein Termin fuer
"ADHS-Diagnostik fuer gesetzlich Versicherte" bei Susann Bergmann oder
Melanie Scholz frei geworden ist, und schickt bei einem Treffer eine
Push-Benachrichtigung ueber ntfy.sh.

Braucht keine externen Pakete (nur Python-Standardbibliothek).
"""

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta

# Feste Werte des Buchungs-Widgets (aus dem Netzwerk-Traffic der Buchungsseite)
CLIENT_ID = "8f0hsw1v0x676r5pqbf4fecv3fo7s5l"
API_KEY = "TESTING"
SOURCE = "bw_v3"

# ntfy.sh-Thema kommt aus einem GitHub Secret (siehe README.md)
NTFY_TOPIC = os.environ.get("NTFY_TOPIC")

DOCTORS = [
    {
        "name": "Susann Bergmann",
        "event_category_id": "139923",
        "event_type_id": "399110",
        "booking_url": (
            "https://termin.samedi.de/b/viola-berg/1/bergmann-susann/"
            "adhs-diagnostik-fur-gesetzlich-versicherte--3?insuranceId=public"
        ),
    },
    {
        "name": "Melanie Scholz",
        "event_category_id": "139924",
        "event_type_id": "399114",
        "booking_url": (
            "https://termin.samedi.de/b/viola-berg/1/scholz-melanie/"
            "adhs-diagnostik-fur-gesetzlich-versicherte--4?insuranceId=public"
        ),
    },
]

# Wie weit und in welchen Schritten in die Zukunft geprueft wird.
# 84 Tage pro Anfrage entspricht dem, was die Webseite selbst benutzt.
WINDOW_DAYS = 84
TOTAL_DAYS_AHEAD = 270  # ca. 9 Monate voraus


def fetch_times(event_category_id: str, event_type_id: str, start: date, end: date):
    params = {
        "client_id": CLIENT_ID,
        "api_key": API_KEY,
        "source": SOURCE,
        "event_category_id": event_category_id,
        "event_type_id": event_type_id,
        "from": start.isoformat(),
        "to": end.isoformat(),
        "insurance_id": "public",
    }
    url = "https://patient.samedi.de/api/booking/v3/times?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
        return payload.get("data", [])


def check_doctor(doc: dict):
    today = date.today()
    start = today + timedelta(days=1)
    horizon = today + timedelta(days=TOTAL_DAYS_AHEAD)
    all_slots = []
    while start < horizon:
        end = min(start + timedelta(days=WINDOW_DAYS), horizon)
        try:
            slots = fetch_times(doc["event_category_id"], doc["event_type_id"], start, end)
            all_slots.extend(slots)
        except urllib.error.HTTPError as exc:
            print(f"HTTP-Fehler bei {doc['name']} ({start} bis {end}): {exc}")
        except Exception as exc:  # noqa: BLE001
            print(f"Fehler bei {doc['name']} ({start} bis {end}): {exc}")
        start = end
    return all_slots


def notify(message: str):
    if not NTFY_TOPIC:
        print("WARNUNG: NTFY_TOPIC ist nicht gesetzt, keine Benachrichtigung moeglich.")
        print(message)
        return
    req = urllib.request.Request(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=message.encode("utf-8"),
        method="POST",
        headers={
            "Title": "ADHS-Termin frei!",
            "Priority": "urgent",
            "Tags": "rotating_light",
        },
    )
    urllib.request.urlopen(req, timeout=15)


def main():
    any_found = False
    for doc in DOCTORS:
        slots = check_doctor(doc)
        if slots:
            any_found = True
            zeiten = ", ".join(s.get("time", "?") for s in slots[:5])
            print(f"TREFFER bei {doc['name']}: {len(slots)} Termin(e) -> {zeiten}")
            notify(f"{doc['name']}: {zeiten}\n\nJetzt buchen: {doc['booking_url']}")
        else:
            print(f"{doc['name']}: keine freien Termine.")
    if not any_found:
        print("Ergebnis: aktuell nirgends ein freier Termin.")


if __name__ == "__main__":
    main()
