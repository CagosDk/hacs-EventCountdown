import json

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .const import CONF_EVENTS, CONF_MAX_SENSORS, DEFAULT_MAX_SENSORS, DOMAIN

_EXAMPLE_EVENTS = json.dumps(
    [
        {
            "name": "Eksempel fødselsdag",
            "day": 1,
            "month": 6,
            "year": 1990,
            "type": "fødselsdag",
            "soon": 30,
        },
        {
            "name": "Juleaften",
            "day": 24,
            "month": 12,
            "year": 2026,
            "type": "begivenhed",
            "soon": 31,
        },
    ],
    ensure_ascii=False,
    indent=2,
)


def _events_schema(default_events: str, default_max: int) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_MAX_SENSORS, default=default_max): vol.All(
                int, vol.Range(min=1, max=20)
            ),
            vol.Required(CONF_EVENTS, default=default_events): str,
        }
    )


class EventCountdownConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                json.loads(user_input[CONF_EVENTS])
            except (json.JSONDecodeError, ValueError):
                errors[CONF_EVENTS] = "invalid_json"
            else:
                return self.async_create_entry(
                    title="Event Countdown",
                    data={
                        CONF_MAX_SENSORS: user_input[CONF_MAX_SENSORS],
                        CONF_EVENTS: user_input[CONF_EVENTS],
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_events_schema(_EXAMPLE_EVENTS, DEFAULT_MAX_SENSORS),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return EventCountdownOptionsFlow(config_entry)


class EventCountdownOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                json.loads(user_input[CONF_EVENTS])
            except (json.JSONDecodeError, ValueError):
                errors[CONF_EVENTS] = "invalid_json"
            else:
                return self.async_create_entry(title="", data=user_input)

        current_events = self._config_entry.options.get(
            CONF_EVENTS,
            self._config_entry.data.get(CONF_EVENTS, _EXAMPLE_EVENTS),
        )
        current_max = self._config_entry.options.get(
            CONF_MAX_SENSORS,
            self._config_entry.data.get(CONF_MAX_SENSORS, DEFAULT_MAX_SENSORS),
        )

        return self.async_show_form(
            step_id="init",
            data_schema=_events_schema(current_events, current_max),
            errors=errors,
        )
