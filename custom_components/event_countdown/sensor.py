from __future__ import annotations

import json
import logging
import re
from datetime import date, timedelta

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval

from .const import CONF_EVENTS, CONF_MAX_SENSORS, DEFAULT_MAX_SENSORS, DOMAIN

_LOGGER = logging.getLogger(__name__)
_UPDATE_INTERVAL = timedelta(hours=1)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    max_sensors: int = entry.options.get(
        CONF_MAX_SENSORS, entry.data.get(CONF_MAX_SENSORS, DEFAULT_MAX_SENSORS)
    )
    sensors = [EventCountdownSensor(entry, slot) for slot in range(max_sensors)]
    async_add_entities(sensors, update_before_add=True)

    async def _handle_interval(now=None):
        for sensor in sensors:
            sensor.async_schedule_update_ha_state(force_refresh=True)

    entry.async_on_unload(
        async_track_time_interval(hass, _handle_interval, _UPDATE_INTERVAL)
    )


def _compute_events(events_json: str) -> list[dict]:
    """Parse events JSON and return sorted list of upcoming events."""
    try:
        raw = json.loads(events_json)
    except (json.JSONDecodeError, ValueError):
        _LOGGER.error("Event Countdown: could not parse events JSON")
        return []

    today = date.today()
    results: list[dict] = []

    for event in raw:
        try:
            if event.get("disabled"):
                continue

            name = event.get("name")
            day = event.get("day")
            month = event.get("month")
            origin_year = event.get("year")  # birth year / founding year

            if not name or not day or not month:
                _LOGGER.warning("Event Countdown: skipping event with missing fields: %s", event)
                continue

            event_type = (event.get("type") or "fødselsdag").lower()
            this_year = today.year

            try:
                target = date(this_year, month, day)
            except ValueError:
                _LOGGER.error("Event Countdown: invalid date for '%s'", name)
                continue

            if target < today:
                if event_type == "begivenhed":
                    continue  # one-time past event – skip
                target = date(this_year + 1, month, day)

            days_remaining = (target - today).days
            age = (target.year - origin_year) if isinstance(origin_year, int) else None
            soon_threshold = event.get("soon", 60) if isinstance(event.get("soon"), int) else 60
            is_soon = days_remaining <= soon_threshold

            file_name = re.sub(r"[^a-zA-Z0-9æøåÆØÅ ]", "", name).replace(" ", "_")
            picture = event.get("picture") or f"/local/pic/{file_name}.jpg"

            if days_remaining == 0:
                dagstekst = "i dag"
            elif days_remaining == 1:
                dagstekst = "i morgen"
            else:
                dagstekst = f"om {days_remaining} dage"

            if event_type == "fødselsdag":
                base = re.sub(r"fødselsdag", "", name, flags=re.IGNORECASE).strip()
                full_name = (
                    f"{base} {age} års fødselsdag {dagstekst}"
                    if age is not None
                    else f"{base} fødselsdag {dagstekst}"
                )
            elif event_type == "bryllup":
                full_name = (
                    f"{age} års {name.lower()} {dagstekst}"
                    if age is not None
                    else f"{name} {dagstekst}"
                )
            else:
                full_name = f"{name} {dagstekst}"

            event_date = (
                f"{origin_year}-{month:02d}-{day:02d}"
                if isinstance(origin_year, int)
                else f"{this_year}-{month:02d}-{day:02d}"
            )

            results.append(
                {
                    "full_name": full_name,
                    "name": name,
                    "type": event_type,
                    "age": age,
                    "days_remaining": days_remaining,
                    "soon": is_soon,
                    "soon_threshold": soon_threshold,
                    "picture": picture,
                    "event_date": event_date,
                }
            )

        except Exception:
            _LOGGER.exception("Event Countdown: unexpected error processing event '%s'", event.get("name"))

    results.sort(key=lambda x: (not x["soon"], x["days_remaining"]))
    return results


class EventCountdownSensor(SensorEntity):
    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = "dage"
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, entry: ConfigEntry, slot: int) -> None:
        self._entry = entry
        self._slot = slot
        self._attr_unique_id = f"{entry.entry_id}_slot_{slot}"
        self._attr_name = f"Event {slot + 1}"
        self._data: dict | None = None

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": "Event Countdown",
            "manufacturer": "CagosDk",
        }

    @property
    def native_value(self):
        return self._data["days_remaining"] if self._data else None

    @property
    def entity_picture(self) -> str | None:
        return self._data["picture"] if self._data else None

    @property
    def extra_state_attributes(self):
        if not self._data:
            return {"full_name": "Ingen begivenhed"}
        return {
            "name": self._data["name"],
            "full_name": self._data["full_name"],
            "type": self._data["type"],
            "age": self._data["age"],
            "days_remaining": self._data["days_remaining"],
            "soon": self._data["soon"],
            "soon_threshold": self._data["soon_threshold"],
            "unit": "dage",
            "entity_picture": self._data["picture"],
            "event_date": self._data["event_date"],
        }

    def update(self) -> None:
        events_json: str = self._entry.options.get(
            CONF_EVENTS,
            self._entry.data.get(CONF_EVENTS, "[]"),
        )
        events = _compute_events(events_json)
        self._data = events[self._slot] if self._slot < len(events) else None
