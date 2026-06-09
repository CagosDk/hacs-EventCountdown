import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import DOMAIN, ENTRY_TYPE_EVENT, ENTRY_TYPE_GLOBAL

_TYPE_OPTIONS = [
    {"value": "fødselsdag", "label": "Birthday 🎂"},
    {"value": "bryllup", "label": "Anniversary 💍"},
    {"value": "begivenhed", "label": "Event 📅"},
]


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
            vol.Required("day", default=int(ev.get("day", 1))): selector.NumberSelector(
                selector.NumberSelectorConfig(min=1, max=31, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Required("month", default=int(ev.get("month", 1))): selector.NumberSelector(
                selector.NumberSelectorConfig(min=1, max=12, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(
                "year",
                description={"suggested_value": ev.get("year")},
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1900, max=2100, mode=selector.NumberSelectorMode.BOX
                )
            ),
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
    event: dict = {
        "name": user_input["name"],
        "day": int(user_input["day"]),
        "month": int(user_input["month"]),
        "type": user_input["type"],
        "soon": int(user_input["soon"]),
        "recurring": user_input["recurring"],
    }
    if user_input.get("year") is not None:
        event["year"] = int(user_input["year"])
    if user_input.get("picture"):
        event["picture"] = user_input["picture"]
    if user_input.get("disabled"):
        event["disabled"] = True
    return event


# ── Config flow (initial install + adding events) ─────────────────────────────

class EventCountdownConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 3

    async def async_step_user(self, user_input=None):
        # Check whether the global config entry already exists
        existing = self.hass.config_entries.async_entries(DOMAIN)
        has_global = any(e.data.get("entry_type") == ENTRY_TYPE_GLOBAL for e in existing)

        if not has_global:
            # First install: silently create the global entry
            return self.async_create_entry(
                title="Global Configuration",
                data={"entry_type": ENTRY_TYPE_GLOBAL},
            )

        # Subsequent "Add": go straight to the event form
        return await self.async_step_event()

    async def async_step_event(self, user_input=None):
        if user_input is not None:
            event = _form_to_event(user_input)
            return self.async_create_entry(
                title=event["name"],
                data={"entry_type": ENTRY_TYPE_EVENT, "event": event},
            )
        return self.async_show_form(step_id="event", data_schema=_event_schema())

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        if config_entry.data.get("entry_type") == ENTRY_TYPE_GLOBAL:
            return GlobalOptionsFlow(config_entry)
        return EventOptionsFlow(config_entry)


# ── Global options flow ───────────────────────────────────────────────────────

class GlobalOptionsFlow(config_entries.OptionsFlow):
    """Global settings — placeholder for future global options."""

    def __init__(self, config_entry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(step_id="init", data_schema=vol.Schema({}))


# ── Per-event options flow ────────────────────────────────────────────────────

class EventOptionsFlow(config_entries.OptionsFlow):
    """Edit a single event's settings."""

    def __init__(self, config_entry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        # Merge saved options on top of original data
        saved = {
            **self._config_entry.data.get("event", {}),
            **self._config_entry.options,
        }
        if user_input is not None:
            event = _form_to_event(user_input)
            # Update the entry title to reflect possible name change
            self.hass.config_entries.async_update_entry(
                self._config_entry, title=event["name"]
            )
            return self.async_create_entry(title="", data=event)
        return self.async_show_form(
            step_id="init",
            data_schema=_event_schema(saved),
        )
