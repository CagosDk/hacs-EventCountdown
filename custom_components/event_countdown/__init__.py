import json
import logging
from pathlib import Path

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.components.frontend import async_register_built_in_panel
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_EVENTS, CONF_MAX_SENSORS, DEFAULT_MAX_SENSORS, DOMAIN

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor"]
_PANEL_KEY = "panel_registered"


async def _register_static_path(hass: HomeAssistant, url_path: str, path: str) -> None:
    try:
        from homeassistant.components.http import StaticPathConfig  # HA 2024.4+
        await hass.http.async_register_static_paths(
            [StaticPathConfig(url_path, path, cache_headers=False)]
        )
    except (ImportError, AttributeError):
        hass.http.register_static_path(url_path, path, False)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})

    if not hass.data[DOMAIN].get(_PANEL_KEY):
        www_path = Path(__file__).parent / "www"
        try:
            await _register_static_path(hass, "/event_countdown_panel", str(www_path))
            async_register_built_in_panel(
                hass,
                "custom",
                sidebar_title=None,   # hidden from sidebar
                sidebar_icon=None,
                frontend_url_path="event-countdown",
                config={
                    "_panel_custom": {
                        "name": "event-countdown-panel",
                        "module_url": "/event_countdown_panel/event-countdown-panel.js",
                    }
                },
                require_admin=False,
            )
            _LOGGER.debug("Event Countdown panel registered")
        except Exception:
            _LOGGER.exception("Event Countdown: could not register sidebar panel")

        websocket_api.async_register_command(hass, websocket_get_config)
        websocket_api.async_register_command(hass, websocket_save_config)
        hass.data[DOMAIN][_PANEL_KEY] = True

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


@websocket_api.websocket_command({vol.Required("type"): "event_countdown/get_config"})
@websocket_api.async_response
async def websocket_get_config(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict,
) -> None:
    entries = hass.config_entries.async_entries(DOMAIN)
    if not entries:
        connection.send_error(msg["id"], "not_found", "No Event Countdown integration found")
        return
    entry = entries[0]
    events_raw = entry.options.get(CONF_EVENTS, entry.data.get(CONF_EVENTS, "[]"))
    try:
        events = json.loads(events_raw)
    except (json.JSONDecodeError, ValueError):
        events = []
    max_sensors = entry.options.get(
        CONF_MAX_SENSORS, entry.data.get(CONF_MAX_SENSORS, DEFAULT_MAX_SENSORS)
    )
    connection.send_result(
        msg["id"],
        {"entry_id": entry.entry_id, "events": events, "max_sensors": max_sensors},
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "event_countdown/save_config",
        vol.Required("entry_id"): str,
        vol.Required("events"): list,
        vol.Required("max_sensors"): int,
    }
)
@websocket_api.async_response
async def websocket_save_config(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict,
) -> None:
    entry = hass.config_entries.async_get_entry(msg["entry_id"])
    if not entry:
        connection.send_error(msg["id"], "not_found", "Config entry not found")
        return
    hass.config_entries.async_update_entry(
        entry,
        options={
            CONF_EVENTS: json.dumps(msg["events"], ensure_ascii=False),
            CONF_MAX_SENSORS: msg["max_sensors"],
        },
    )
    await hass.config_entries.async_reload(entry.entry_id)
    connection.send_result(msg["id"], {"success": True})
