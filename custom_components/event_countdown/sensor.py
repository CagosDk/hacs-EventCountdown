"""Slot sensors showing the next N upcoming events, sorted like the original Node-RED flow."""
from __future__ import annotations

import logging
import re
from datetime import date, timedelta

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval

from .const import (
    CONF_NUM_SENSORS,
    DEFAULT_NUM_SENSORS,
    DOMAIN,
    ENTRY_TYPE,
    ENTRY_TYPE_EVENT,
    SIGNAL_EVENTS_CHANGED,
)

_LOGGER = logging.getLogger(__name__)
_UPDATE_INTERVAL = timedelta(hours=1)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    num_sensors = entry.options.get(
        CONF_NUM_SENSORS, entry.data.get(CONF_NUM_SENSORS, DEFAULT_NUM_SENSORS)
    )
    sensors = [EventSlotSensor(entry, slot) for slot in range(num_sensors)]
    async_add_entities(sensors, update_before_add=True)

    @callback
    def _refresh(now=None) -> None:
        for sensor in sensors:
            sensor.async_schedule_update_ha_state(force_refresh=True)

    entry.async_on_unload(
        async_dispatcher_connect(hass, SIGNAL_EVENTS_CHANGED, _refresh)
    )
    entry.async_on_unload(
        async_track_time_interval(hass, _refresh, _UPDATE_INTERVAL)
    )


def _collect_events(hass: HomeAssistant) -> list[dict]:
    """Gather all event entries (data merged with options)."""
    return [
        {**e.data.get("event", {}), **e.options}
        for e in hass.config_entries.async_entries(DOMAIN)
        if e.data.get(ENTRY_TYPE) == ENTRY_TYPE_EVENT
    ]


def _compute_all(events: list[dict]) -> list[dict]:
    """Port of the Node-RED function node: compute, filter and sort events."""
    today = date.today()
    results: list[dict] = []

    for event in events:
        try:
            if event.get("disabled"):
                continue

            name = event.get("name")
            day = event.get("day")
            month = event.get("month")
            year = event.get("year")
            if not name or not day or not month:
                continue

            event_type = (event.get("type") or "fødselsdag").lower()
            recurring = event.get("recurring")
            if recurring is None:
                recurring = event_type != "begivenhed"

            try:
                target = date(today.year, month, day)
            except ValueError:
                _LOGGER.warning("Event Countdown: invalid date for '%s'", name)
                continue

            if target < today:
                if not recurring:
                    continue
                target = date(today.year + 1, month, day)

            days_remaining = (target - today).days
            age = (target.year - year) if isinstance(year, int) else None
            soon_threshold = event.get("soon") if isinstance(event.get("soon"), int) else 30
            is_soon = days_remaining <= soon_threshold

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

            file_name = re.sub(r"[^a-zA-Z0-9æøåÆØÅ ]", "", name).replace(" ", "_")
            picture = event.get("picture") or f"/local/pic/{file_name}.jpg"
            event_date = (
                f"{year}-{month:02d}-{day:02d}"
                if isinstance(year, int)
                else f"{today.year}-{month:02d}-{day:02d}"
            )

            results.append(
                {
                    "name": name,
                    "full_name": full_name,
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
            _LOGGER.exception("Event Countdown: error processing event %s", event)

    # Sort: soon-events first, then by days remaining
    results.sort(key=lambda x: (not x["soon"], x["days_remaining"]))
    return results


class EventSlotSensor(SensorEntity):
    """One slot in the sorted list of upcoming events (begivenhed0..N-1)."""

    _attr_icon = "mdi:calendar-clock"
    _attr_native_unit_of_measurement = "dage"
    _attr_should_poll = False

    def __init__(self, entry: ConfigEntry, slot: int) -> None:
        self._entry = entry
        self._slot = slot
        self._attr_unique_id = f"{entry.entry_id}_begivenhed{slot}"
        self._attr_name = f"Begivenhed {slot}"
        self._data: dict | None = None

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name="Event Countdown",
            manufacturer="CagosDk",
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
            # Mirror the Node-RED fallback message
            return {"full_name": "Ingen begivenhed", "soon": False}
        return {
            "name": self._data["name"],
            "full_name": self._data["full_name"],
            "type": self._data["type"],
            "age": self._data["age"],
            "days_remaining": self._data["days_remaining"],
            "soon": self._data["soon"],
            "soon_threshold": self._data["soon_threshold"],
            "entity_picture": self._data["picture"],
            "event_date": self._data["event_date"],
        }

    def update(self) -> None:
        computed = _compute_all(_collect_events(self.hass))
        self._data = computed[self._slot] if self._slot < len(computed) else None
