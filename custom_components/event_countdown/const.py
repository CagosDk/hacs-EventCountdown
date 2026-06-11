DOMAIN = "event_countdown"

ENTRY_TYPE = "entry_type"
ENTRY_TYPE_GLOBAL = "global"
ENTRY_TYPE_EVENT = "event"

CONF_NUM_SENSORS = "num_sensors"
DEFAULT_NUM_SENSORS = 4

CONF_LANGUAGE = "language"
DEFAULT_LANGUAGE = "auto"
LANGUAGE_OPTIONS = ["auto", "en", "da"]

CONF_DELETE_AFTER_OCCURRENCE = "delete_after_occurrence"

EVENT_TYPE_BIRTHDAY = "birthday"
EVENT_TYPE_ANNIVERSARY = "anniversary"
EVENT_TYPE_EVENT = "event"

# Maps legacy (Danish) type values to the current English ones.
LEGACY_TYPE_MAP = {
    "fødselsdag": EVENT_TYPE_BIRTHDAY,
    "bryllup": EVENT_TYPE_ANNIVERSARY,
    "begivenhed": EVENT_TYPE_EVENT,
}

SIGNAL_EVENTS_CHANGED = "event_countdown_events_changed"
