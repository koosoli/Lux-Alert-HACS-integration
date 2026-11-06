"""Constants for the LU-Alert (Luxembourg) integration."""
from __future__ import annotations

DOMAIN = "lu_alert"

# The dataset "Alertes du système LU-Alert" on data.public.lu: one CAP XML file per message.
DATASET_URL = "https://data.public.lu/api/1/datasets/67aca67bcaea3ae62308114f/"
PROJECT_URL = "https://github.com/janreimen/Lux-Alert-HACS-integration"

DEFAULT_NAME = "LU-Alert"
ATTRIBUTION = "Data provided by data.public.lu"

# -- timings and limits -------------------------------------------------------------------------------------
DEFAULT_SCAN_INTERVAL = 300             # seconds between polls
MAX_BACKOFF = 1800                      # longest wait between polls after failures
HTTP_TIMEOUT = 10                       # seconds per HTTP request
FETCH_WORKERS = 5                       # alert files downloaded in parallel
MAX_DATASET_BYTES = 16 * 1024 * 1024    # the dataset description lists every file ever published
MAX_XML_BYTES = 2 * 1024 * 1024         # one CAP message; areas with large polygons are a few hundred kB
DEFAULT_MAX_RESOURCES = 100             # the newest files that are looked at
DEFAULT_STALE_DAYS = 10                 # a message without an end that is older than this is not shown
MAX_ALERTS = 3                          # number of "LU-Alert n" sensors

# -- configuration keys (the latitude and longitude keys are Home Assistant's own) -----------------------------
CONF_MIN_SEVERITY = "min_severity"
CONF_LANGUAGE = "language"
CONF_LOCATION_MODE = "location_mode"
CONF_WATCHLIST_KEYWORDS = "watchlist_keywords"
CONF_ALLERGENS = "allergens"
CONF_SHOW_TEST = "show_test_alerts"

LOCATION_MODE_OFF = "off"
LOCATION_MODE_FLAG = "flag"
LOCATION_MODE_ONLY = "only"
LOCATION_MODES = (LOCATION_MODE_OFF, LOCATION_MODE_FLAG, LOCATION_MODE_ONLY)

LANGUAGES = ("en", "de", "fr", "lb")

DEFAULT_MIN_SEVERITY = "Unknown"
DEFAULT_LANGUAGE = "en"
DEFAULT_LOCATION_MODE = LOCATION_MODE_OFF
DEFAULT_WATCHLIST_KEYWORDS = ""
DEFAULT_ALLERGENS: list[str] = []
DEFAULT_SHOW_TEST = False

# Suggestions for the allergen option (any other word can be typed in as well)
ALLERGEN_LIST = [
    "Barley",
    "Celery",
    "Crustaceans",
    "Eggs",
    "Fish",
    "Gluten",
    "Lupin",
    "Milk",
    "Molluscs",
    "Mustard",
    "Nuts",
    "Peanuts",
    "Sesame",
    "Soy",
    "Sulphites",
]

# -- severity -----------------------------------------------------------------------------------------------
EXTREME, SEVERE, MODERATE, MINOR, INFORMATION, UNKNOWN, TEST = (
    "Extreme", "Severe", "Moderate", "Minor", "Information", "Unknown", "Test")
SEVERITIES = (EXTREME, SEVERE, MODERATE, MINOR, INFORMATION, UNKNOWN, TEST)
# Higher is more severe. Test is below everything: it is shown only when a test is asked for.
SEVERITY_RANK = {EXTREME: 4, SEVERE: 3, MODERATE: 2, MINOR: 1, INFORMATION: 0, UNKNOWN: -1, TEST: -2}
# The choices of the option "Minimum severity"
MIN_SEVERITY_CHOICES = (UNKNOWN, INFORMATION, MINOR, MODERATE, SEVERE, EXTREME)
# The severities that make a "critical" alert
CRITICAL_SEVERITIES = (EXTREME, SEVERE)

# The LU-Alert level of a message, as the feed writes it (compared in lower case). The live feed uses ALERT_LVL_1 ...
# ALERT_LVL_4 and TEST (seen by the Domoticz-LUAlert plugin on 2026-11-04, 100 messages); the other spellings come from
# the levels named on https://lu-alert.lu (D, N1-N3, A, I, T) and the CAP-LU profile (LU-Alert Level 1-4, Amber, Test,
# Exercise) and have not been seen in the feed.
LEVEL_TO_SEVERITY = {
    "d": EXTREME,                       # only when D is not a test level (see DEFAULT_TEST_LEVELS)
    "n1": EXTREME,                      # awareness level red
    "l1": EXTREME, "lu-alert level 1": EXTREME, "alert_lvl_1": EXTREME,
    "n2": SEVERE,                       # awareness level orange
    "l2": SEVERE, "lu-alert level 2": SEVERE, "alert_lvl_2": SEVERE,
    "a": MODERATE,                      # missing person / kidnapping (amber)
    "lu-alert amber": MODERATE,
    "n3": MINOR,                        # awareness level yellow
    "l3": MINOR, "lu-alert level 3": MINOR, "alert_lvl_3": MINOR,
    "i": INFORMATION,
    "lu-alert level 4": INFORMATION, "alert_lvl_4": INFORMATION,
    "t": TEST, "test": TEST, "lu-alert test": TEST, "lu-alert exercise": TEST,
}
# The names of the parameter that carries the level. The feed writes them with the profile prefix
# ("urn:oasis:...:profile:cap-lu:1.0:cb-eu-level"): the part after the last ':' counts.
LEVEL_PARAMETERS = ("cb-eu-level", "cb-lu-level")
# Levels that are treated as test messages (and so left out) unless tests are asked for. "D" is in the list because the
# original integration filtered it as a test level; it is also an Extreme level there. D has NOT been seen in the live
# feed. TEST is what the live feed writes for its test messages (with the CAP status Actual).
DEFAULT_TEST_LEVELS = ("T", "TEST", "D", "LU-Alert Test", "LU-Alert Exercise")
# CAP status values that are not a real alert: Test, Exercise, System and Draft are shown only when tests are shown
REAL_STATUS = "actual"

# Channel blocks of CAP-LU: one <info> per language and channel. The text of the app and the website is the fullest,
# a siren block has no text for people.
CHANNEL_PARAMETER = "canal"
CHANNEL_ORDER = ("mobile-app", "website channel", "cell-broadcast", "sms", "email", "facebook")
CHANNEL_LAST = ("siren", "led-signs", "twitter")

MSG_NO_ALERT = ("ack", "error")         # CAP replies, not alerts

# Location filter modes as the filter code knows them
LOCATION_OFF, LOCATION_FLAG, LOCATION_ONLY = 0, 1, 2
LOCATION_MODE_VALUES = {LOCATION_MODE_OFF: LOCATION_OFF, LOCATION_MODE_FLAG: LOCATION_FLAG,
                        LOCATION_MODE_ONLY: LOCATION_ONLY}

# State text limit of Home Assistant
MAX_STATE_LENGTH = 255

# The card: the www folder is served at STATIC_URL
STATIC_URL = "/lu_alert_static"
CARD_FILE = "lu-alert-card.js"
