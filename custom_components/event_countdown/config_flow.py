from homeassistant import config_entries

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
