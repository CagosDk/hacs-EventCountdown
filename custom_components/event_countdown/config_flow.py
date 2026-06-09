import json
from datetime import date

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import CONF_EVENTS, CONF_MAX_SENSORS, DEFAULT_MAX_SENSORS, DOMAIN

_TYPE_OPTIONS = [
    {"value": "fødselsdag", "label": "Birthday 🎂"},
    {"value": "bryllup", "label": "Anniversary 💍"},
    {"value": "begivenhed", "label": "Event 📅"},
]


def _ev_date_str(ev: dict) -> str:
    """Return YYYY-MM-DD string from event dict, falling back to today."""
    year = ev.get("year") or date.today().year
    month = ev.get("month") or 1
    day = ev.get("day") or 1
    try:
        return date(int(year), int(month), int(day)).isoformat()
    except ValueError:
        return date.today().isoformat()


def _event_schema(event: dict | None = None) -> vol.Schema:
    ev = event or {}
    recurring = ev.get("recurring")
    if recurring is None:
        recurring = ev.get("type", "fødselsdag") != "begivenhed"

    return vol.Schema(
        {
            vol.Required("name", default=ev.get("name", "")): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
            ),
            vol.Required("event_date", default=_ev_date_str(ev)): selector.DateSelector(),
            vol.Required("type", default=ev.get("type", "fødselsdag")): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=_TYPE_OPTIONS,
                    mode=selector.SelectSelectorMode.LIST,
                )
            ),
            vol.Required("soon", default=int(ev.get("soon", 30))): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1, max=180, step=1, mode=selector.NumberSelectorMode.SLIDER
                )
            ),
            vol.Optional(
                "picture",
                description={"suggested_value": ev.get("picture", "")},
            ): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
            ),
            vol.Required("recurring", default=bool(recurring)): selector.BooleanSelector(),
            vol.Required(
                "disabled", default=bool(ev.get("disabled", False))
            ): selector.BooleanSelector(),
        }
    )


def _form_to_event(user_input: dict) -> dict:
    year, month, day = (int(x) for x in user_input["event_date"].split("-"))
    event: dict = {
        "name": user_input["name"],
        "day": day,
        "month": month,
        "year": year,
        "type": user_input["type"],
        "soon": int(user_input["soon"]),
        "recurring": user_input["recurring"],
    }
    if user_input.get("picture"):
        event["picture"] = user_input["picture"]
    if user_input.get("disabled"):
        event["disabled"] = True
    return event


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
        self._events: list[dict] = []
        self._max_sensors: int = DEFAULT_MAX_SENSORS
        self._initialized = False
        self._edit_index: int | None = None

    async def async_step_init(self, user_input=None):
        if not self._initialized:
            raw = self._config_entry.options.get(
                CONF_EVENTS, self._config_entry.data.get(CONF_EVENTS, "[]")
            )
            try:
                self._events = json.loads(raw)
            except (json.JSONDecodeError, ValueError):
                self._events = []
            self._max_sensors = self._config_entry.options.get(
                CONF_MAX_SENSORS,
                self._config_entry.data.get(CONF_MAX_SENSORS, DEFAULT_MAX_SENSORS),
            )
            self._initialized = True

        menu_options = ["add_event"]
        if self._events:
            menu_options += ["edit_event", "delete_event"]
        menu_options += ["settings", "save"]

        return self.async_show_menu(step_id="init", menu_options=menu_options)

    async def async_step_add_event(self, user_input=None):
        if user_input is not None:
            self._events.append(_form_to_event(user_input))
            return await self.async_step_init()
        return self.async_show_form(step_id="add_event", data_schema=_event_schema())

    async def async_step_edit_event(self, user_input=None):
        if user_input is not None:
            if self._edit_index is not None:
                self._events[self._edit_index] = _form_to_event(user_input)
                self._edit_index = None
                return await self.async_step_init()
            self._edit_index = int(user_input["event_index"])
            return self.async_show_form(
                step_id="edit_event",
                data_schema=_event_schema(self._events[self._edit_index]),
            )

        if self._edit_index is None:
            return self.async_show_form(
                step_id="edit_event",
                data_schema=vol.Schema(
                    {
                        vol.Required("event_index"): selector.SelectSelector(
                            selector.SelectSelectorConfig(
                                options=[
                                    {"value": str(i), "label": e["name"]}
                                    for i, e in enumerate(self._events)
                                ],
                                mode=selector.SelectSelectorMode.LIST,
                            )
                        )
                    }
                ),
            )
        return self.async_show_form(
            step_id="edit_event",
            data_schema=_event_schema(self._events[self._edit_index]),
        )

    async def async_step_delete_event(self, user_input=None):
        if user_input is not None:
            self._events.pop(int(user_input["event_index"]))
            return await self.async_step_init()
        return self.async_show_form(
            step_id="delete_event",
            data_schema=vol.Schema(
                {
                    vol.Required("event_index"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                {"value": str(i), "label": e["name"]}
                                for i, e in enumerate(self._events)
                            ],
                            mode=selector.SelectSelectorMode.LIST,
                        )
                    )
                }
            ),
        )

    async def async_step_settings(self, user_input=None):
        if user_input is not None:
            self._max_sensors = int(user_input[CONF_MAX_SENSORS])
            return await self.async_step_init()
        return self.async_show_form(
            step_id="settings",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_MAX_SENSORS, default=self._max_sensors
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=1, max=20, step=1, mode=selector.NumberSelectorMode.SLIDER
                        )
                    ),
                }
            ),
        )

    async def async_step_save(self, user_input=None):
        return self.async_create_entry(
            title="",
            data={
                CONF_EVENTS: json.dumps(self._events, ensure_ascii=False),
                CONF_MAX_SENSORS: self._max_sensors,
            },
        )
