import json
from pathlib import Path


INTEGRATION = Path(__file__).parents[1] / "custom_components" / "lu_alert"


def test_strings_and_english_translation_are_valid_json_and_have_matching_selectors():
    strings = json.loads((INTEGRATION / "strings.json").read_text(encoding="utf-8"))
    english = json.loads((INTEGRATION / "translations" / "en.json").read_text(encoding="utf-8"))

    for document in (strings, english):
        assert set(document["selector"]["severity"]["options"]) == {
            "unknown", "information", "minor", "moderate", "severe", "extreme"
        }
        assert set(document["selector"]["location_mode"]["options"]) == {"off", "flag", "only"}


def test_german_severity_selector_keys_use_configured_values():
    german = json.loads((INTEGRATION / "translations" / "de.json").read_text(encoding="utf-8"))

    assert set(german["selector"]["severity"]["options"]) == {
        "unknown", "information", "minor", "moderate", "severe", "extreme"
    }
