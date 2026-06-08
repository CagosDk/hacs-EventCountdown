# Event Countdown

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)

A Home Assistant integration that creates sensors for upcoming events – birthdays, anniversaries, and one-time events.

## Installation via HACS

1. Add this repository as a **Custom Repository** in HACS (category: Integration)
2. Find "Event Countdown" in HACS and install
3. Restart Home Assistant
4. Go to **Settings → Devices & Services → Add Integration** and search for "Event Countdown"

## Configuration

During setup (and later via **Configure**) you specify:

- **Number of sensors** – how many sensors to create (default: 4)
- **Events (JSON)** – a JSON list of your events

The integration updates automatically every hour.

## JSON format

```json
[
  {
    "name": "Frederik's birthday",
    "day": 24,
    "month": 3,
    "year": 2015,
    "type": "fødselsdag",
    "soon": 30,
    "picture": "/local/pic/frederik.jpg"
  },
  {
    "name": "Wedding anniversary",
    "day": 24,
    "month": 9,
    "year": 2016,
    "type": "bryllup",
    "soon": 30
  },
  {
    "name": "Summer holiday",
    "day": 5,
    "month": 7,
    "year": 2026,
    "type": "begivenhed",
    "soon": 60
  }
]
```

### Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Name of the event |
| `day` | Yes | Day (1-31) |
| `month` | Yes | Month (1-12) |
| `year` | No | Birth year / founding year – used to calculate age |
| `type` | No | `fødselsdag` (default), `bryllup`, or `begivenhed` |
| `soon` | No | Days before the event is marked as "soon" (default: 60) |
| `picture` | No | Path to image, e.g. `/local/pic/name.jpg` |
| `disabled` | No | Set to `true` to skip the event |

### Event types

- **`fødselsdag`** (birthday) – repeats every year, calculates age automatically
- **`bryllup`** (anniversary) – repeats every year, calculates years automatically
- **`begivenhed`** (event) – one-time event, skipped once the date has passed

## Sensors

The integration creates N sensors (e.g. `sensor.event_countdown_event_1`):

- **State** – number of days until the event
- **Attributes:**
  - `full_name` – human-readable text, e.g. *"Frederik 11th birthday in 5 days"*
  - `name` – event name
  - `type` – event type
  - `age` – calculated age / anniversary number
  - `days_remaining` – days remaining
  - `soon` – `true` if within the threshold
  - `soon_threshold` – threshold in days
  - `event_date` – original event date (YYYY-MM-DD)
  - `entity_picture` – path to image

Sensors are sorted: "soon" events first, then ascending by days remaining.
