import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import DOMAIN, ENTRY_TYPE, ENTRY_TYPE_GLOBAL, SIGNAL_EVENTS_CHANGED

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor"]


def _is_global(entry: ConfigEntry) -> bool:
    return entry.data.get(ENTRY_TYPE) == ENTRY_TYPE_GLOBAL


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})

    if _is_global(entry):
        # The global entry owns the slot sensors
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    else:
        # Event entries hold data only — notify slot sensors to recompute
        async_dispatcher_send(hass, SIGNAL_EVENTS_CHANGED)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if _is_global(entry):
        return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    # Event entry removed/unloaded — recompute slots
    async_dispatcher_send(hass, SIGNAL_EVENTS_CHANGED)
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    if _is_global(entry):
        # Number of sensors changed — reload to recreate slot sensors
        await hass.config_entries.async_reload(entry.entry_id)
    else:
        # Event edited — just recompute
        async_dispatcher_send(hass, SIGNAL_EVENTS_CHANGED)
