"""Slot sensors showing the next N upcoming events, sorted like the original Node-RED flow."""
from __future__ import annotations

import logging
import re
from datetime import date, timedelta

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval

from .const import (
    CONF_DELETE_AFTER_OCCURRENCE,
    CONF_LANGUAGE,
    CONF_NUM_SENSORS,
    DEFAULT_LANGUAGE,
    DEFAULT_NUM_SENSORS,
    DOMAIN,
    ENTRY_TYPE,
    ENTRY_TYPE_EVENT,
    EVENT_TYPE_ANNIVERSARY,
    EVENT_TYPE_BIRTHDAY,
    EVENT_TYPE_EVENT,
    SIGNAL_EVENTS_CHANGED,
)
from .lang import get_language

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
    language_code = entry.options.get(
        CONF_LANGUAGE, entry.data.get(CONF_LANGUAGE, DEFAULT_LANGUAGE)
    )
    if language_code == "auto":
        language_code = hass.config.language
    lang = get_language(language_code)

    _remove_stale_slot_entities(hass, entry, num_sensors)

    sensors = [EventSlotSensor(entry, slot, lang) for slot in range(num_sensors)]
    async_add_entities(sensors, update_before_add=True)

    @callback
    def _refresh(now=None) -> None:
        hass.async_create_task(_remove_expired_events(hass))
        for sensor in sensors:
            sensor.async_schedule_update_ha_state(force_refresh=True)

    entry.async_on_unload(
        async_dispatcher_connect(hass, SIGNAL_EVENTS_CHANGED, _refresh)
    )
    entry.async_on_unload(
        async_track_time_interval(hass, _refresh, _UPDATE_INTERVAL)
    )


def _remove_stale_slot_entities(
    hass: HomeAssistant, entry: ConfigEntry, num_sensors: int
) -> None:
    """Remove slot sensors left over from a previous, larger num_sensors setting."""
    ent_reg = er.async_get(hass)
    prefix = f"{entry.entry_id}_event"
    for entity_entry in er.async_entries_for_config_entry(ent_reg, entry.entry_id):
        if not entity_entry.unique_id.startswith(prefix):
            continue
        try:
            slot = int(entity_entry.unique_id[len(prefix):])
        except ValueError:
            continue
        if slot >= num_sensors:
            ent_reg.async_remove(entity_entry.entity_id)


def _collect_events(hass: HomeAssistant) -> list[dict]:
    """Gather all event entries (data merged with options)."""
    return [
        {**e.data.get("event", {}), **e.options}
        for e in hass.config_entries.async_entries(DOMAIN)
        if e.data.get(ENTRY_TYPE) == ENTRY_TYPE_EVENT
    ]


async def _remove_expired_events(hass: HomeAssistant) -> None:
    """Remove event entries that occurred and are flagged for deletion afterwards."""
    today = date.today()

    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.data.get(ENTRY_TYPE) != ENTRY_TYPE_EVENT:
            continue

        event = {**entry.data.get("event", {}), **entry.options}
        if not event.get(CONF_DELETE_AFTER_OCCURRENCE):
            continue

        day = event.get("day")
        month = event.get("month")
        if not day or not month:
            continue

        try:
            target = date(today.year, month, day)
        except ValueError:
            continue

        if target < today:
            _LOGGER.info(
                "Event Countdown: removing '%s' (occurred on %s)",
                event.get("name"),
                target,
            )
            await hass.config_entries.async_remove(entry.entry_id)


def _compute_all(events: list[dict], lang: dict[str, str]) -> list[dict]:
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

            event_type = (event.get("type") or EVENT_TYPE_BIRTHDAY).lower()
            recurring = event.get("recurring")
            if recurring is None:
                recurring = event_type != EVENT_TYPE_EVENT

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
                day_text = lang["today"]
            elif days_remaining == 1:
                day_text = lang["tomorrow"]
            else:
                day_text = lang["in_days"].format(days=days_remaining)

            if event_type == EVENT_TYPE_BIRTHDAY:
                base = re.sub(
                    lang["strip_word"], "", name, flags=re.IGNORECASE
                ).strip()
                full_name = (
                    lang["birthday_with_age"].format(base=base, age=age, day_text=day_text)
                    if age is not None
                    else lang["birthday_no_age"].format(base=base, day_text=day_text)
                )
            elif event_type == EVENT_TYPE_ANNIVERSARY:
                full_name = (
                    lang["anniversary_with_age"].format(
                        age=age, name=name.lower(), day_text=day_text
                    )
                    if age is not None
                    else lang["anniversary_no_age"].format(name=name, day_text=day_text)
                )
            else:
                full_name = lang["event"].format(name=name, day_text=day_text)

            picture = event.get("picture")
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
    """One slot in the sorted list of upcoming events (event_0..N-1)."""

    _attr_should_poll = False

    def __init__(self, entry: ConfigEntry, slot: int, lang: dict[str, str]) -> None:
        self._entry = entry
        self._slot = slot
        self._lang = lang
        self._attr_unique_id = f"{entry.entry_id}_event{slot}"
        self._attr_name = lang["slot_name"].format(slot=slot)
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
    def native_value(self) -> str:
        """Whether this slot holds an event that should be displayed ("soon")."""
        return "true" if self._data and self._data["soon"] else "false"

    @property
    def entity_picture(self) -> str | None:
        return self._data["picture"] if self._data else None

    @property
    def extra_state_attributes(self):
        if not self._data:
            # Mirror the Node-RED fallback message
            return {"full_name": self._lang["no_event"], "soon": False}
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
        computed = _compute_all(_collect_events(self.hass), self._lang)
        self._data = computed[self._slot] if self._slot < len(computed) else None
