import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .const import CONF_EVENTS, CONF_MAX_SENSORS, DEFAULT_MAX_SENSORS, DOMAIN


class EventCountdownConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(
                title="Event Countdown",
                data={CONF_MAX_SENSORS: DEFAULT_MAX_SENSORS, CONF_EVENTS: "[]"},
            )
        return self.async_show_form(step_id="user")

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return EventCountdownOptionsFlow(config_entry)


class EventCountdownOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data={})
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({}),
        )
