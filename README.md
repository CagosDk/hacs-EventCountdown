# Event Countdown

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)

A Home Assistant integration that creates sensors for upcoming events – birthdays, anniversaries, and one-time events.

## Installation via HACS

1. Add this repository as a **Custom Repository** in HACS (category: Integration)
2. Find "Event Countdown" in HACS and install
3. Restart Home Assistant
4. Go to **Settings → Devices & Services → Add Integration** and search for "Event Countdown"

## Configuration

The integration is configured entirely through the UI, with two kinds of entries:

### Global Configuration

Created automatically the first time the integration is added. Use its **Configure** button to set:

- **Number of sensors** – how many slot sensors to create (default: 4). They always show the next N upcoming events, sorted with the soonest first.

### Events

Add one entry per event via **Add Integration → Event Countdown**. Each event has its own **Configure** / **Delete** actions and the following fields:

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Name of the event |
| `day` | Yes | Day (1-31) |
| `month` | Yes | Month (1-12) |
| `year` | No | Birth year / wedding year — used to calculate age |
| `type` | Yes | `birthday` (default), `anniversary`, or `event` |
| `soon` | Yes | Days before the event is marked as "soon" (default: 30) |
| `picture` | No | Path to image, e.g. `/local/pic/name.jpg` |
| `recurring` | Yes | On = repeats every year. Off = skipped once the date has passed (default depends on `type`) |
| `delete_after_occurrence` | Yes | On = the event (and its configuration entry) is removed automatically the day after it occurs |
| `disabled` | Yes | On = the event is ignored until re-enabled |

### Event types

- **`birthday`** – repeats every year by default, calculates age automatically
- **`anniversary`** – repeats every year by default, calculates the number of years automatically
- **`event`** – one-time by default, skipped once the date has passed (unless `recurring` is enabled)

The integration recomputes the upcoming events every hour, and whenever an event is added, edited, or removed.

## Sensors

The Global Configuration entry creates N slot sensors (`sensor.event_countdown_event_0` … `event_(N-1)`), each showing the next upcoming events sorted with the soonest (and "soon") events first:

- **State** – number of days until the event
- **Attributes:**
  - `full_name` – human-readable text, e.g. *"Frederik turns 11 in 5 days"*
  - `name` – event name
  - `type` – event type
  - `age` – calculated age / anniversary number
  - `days_remaining` – days remaining
  - `soon` – `true` if within the threshold
  - `soon_threshold` – threshold in days
  - `event_date` – original event date (YYYY-MM-DD)
  - `entity_picture` – path to image

If there are fewer upcoming events than sensors, the remaining sensors show `full_name: "No event"`.
