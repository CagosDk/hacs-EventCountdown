from __future__ import annotations

import json
import logging
import re
from datetime import date, timedelta

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval

from .const import CONF_EVENTS, DOMAIN

_LOGGER = logging.getLogger(__name__)
_UPDATE_INTERVAL = timedelta(hours=1)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    events_raw = entry.options.get(CONF_EVENTS, entry.data.get(CONF_EVENTS, "[]"))
    try:
        events = json.loads(events_raw)
    except (json.JSONDecodeError, ValueError):
        events = []

    sensors = [EventCountdownSensor(entry, ev) for ev in events if ev.get("name")]
    async_add_entities(sensors, update_before_add=True)

    async def _handle_interval(now=None):
        for sensor in sensors:
            sensor.async_schedule_update_ha_state(force_refresh=True)

    entry.async_on_unload(
        async_track_time_interval(hass, _handle_interval, _UPDATE_INTERVAL)
    )


def _compute(event: dict) -> dict | None:
    """Compute countdown data for a single event. Returns None if past and non-recurring."""
    today = date.today()
    name = event.get("name", "")
    day = event.get("day")
    month = event.get("month")
    year = event.get("year")
    event_type = (event.get("type") or "fødselsdag").lower()
    recurring = event.get("recurring")
    if recurring is None:
        recurring = event_type != "begivenhed"

    if not day or not month:
        return None

    try:
        target = date(today.year, month, day)
    except ValueError:
        return None

    if target < today:
        if not recurring:
            return None
        target = date(today.year + 1, month, day)

    days_remaining = (target - today).days
    age = (target.year - year) if isinstance(year, int) else None
    soon_threshold = event.get("soon", 30) if isinstance(event.get("soon"), int) else 30
    is_soon = days_remaining <= soon_threshold

    # Day text
    if days_remaining == 0:
        dagstekst = "i dag"
    elif days_remaining == 1:
        dagstekst = "i morgen"
    else:
        dagstekst = f"om {days_remaining} dage"

    # Full name
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
        f"{year}-{month:02d}-{day:02d}"
        if isinstance(year, int)
        else f"{today.year}-{month:02d}-{day:02d}"
    )

    file_name = re.sub(r"[^a-zA-Z0-9æøåÆØÅ ]", "", name).replace(" ", "_")
    picture = event.get("picture") or f"/local/pic/{file_name}.jpg"

    return {
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


class EventCountdownSensor(SensorEntity):
    _attr_icon = "mdi:calendar-clock"
    _attr_native_unit_of_measurement = "dage"

    def __init__(self, entry: ConfigEntry, event: dict) -> None:
        self._entry = entry
        self._event = event
        name = event["name"]
        slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
        self._attr_unique_id = f"{entry.entry_id}_{slug}"
        self._attr_name = name
        self._data: dict | None = None

    @property
    def device_info(self) -> DeviceInfo:
        name = self._event["name"]
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self._entry.entry_id}_{name}")},
            name=name,
            manufacturer="Event Countdown",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def native_value(self):
        return self._data["days_remaining"] if self._data else None

    @property
    def entity_picture(self) -> str | None:
        return self._data["picture"] if self._data else None

    @property
    def extra_state_attributes(self):
        if not self._data:
            return {}
        return {
            "full_name": self._data["full_name"],
            "type": self._data["type"],
            "age": self._data["age"],
            "days_remaining": self._data["days_remaining"],
            "soon": self._data["soon"],
            "soon_threshold": self._data["soon_threshold"],
            "entity_picture": self._data["picture"],
            "event_date": self._data["event_date"],
        }

    @property
    def available(self) -> bool:
        return self._data is not None

    def update(self) -> None:
        if self._event.get("disabled"):
            self._data = None
            return
        self._data = _compute(self._event)
