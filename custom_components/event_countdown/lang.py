"""Per-language text used to build the human-readable sensor output."""

LANGUAGES: dict[str, dict[str, str]] = {
    "en": {
        "today": "today",
        "tomorrow": "tomorrow",
        "in_days": "in {days} days",
        "no_event": "No event",
        "unit_days": "days",
        "slot_name": "Event {slot}",
        "strip_word": "birthday",
        "birthday_with_age": "{base} turns {age} {day_text}",
        "birthday_no_age": "{base}'s birthday {day_text}",
        "anniversary_with_age": "{age} year {name} {day_text}",
        "anniversary_no_age": "{name} {day_text}",
        "event": "{name} {day_text}",
    },
    "da": {
        "today": "i dag",
        "tomorrow": "i morgen",
        "in_days": "om {days} dage",
        "no_event": "Ingen begivenhed",
        "unit_days": "dage",
        "slot_name": "Begivenhed {slot}",
        "strip_word": "fødselsdag",
        "birthday_with_age": "{base} {age} års fødselsdag {day_text}",
        "birthday_no_age": "{base} fødselsdag {day_text}",
        "anniversary_with_age": "{age} års {name} {day_text}",
        "anniversary_no_age": "{name} {day_text}",
        "event": "{name} {day_text}",
    },
}

DEFAULT_LANGUAGE = "en"


def get_language(language_code: str) -> dict[str, str]:
    """Return the translation table for a language, falling back to English."""
    return LANGUAGES.get(language_code, LANGUAGES[DEFAULT_LANGUAGE])
