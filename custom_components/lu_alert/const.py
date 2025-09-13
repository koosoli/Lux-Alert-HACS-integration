"""Constants for the LU-Alert (Luxembourg) integration."""

# The domain of the integration. This must be unique and match the directory name.
DOMAIN = "lu_alert"

# The base URL for the data.public.lu API to get the dataset information.
DATASET_API_URL = "https://data.public.lu/api/1/datasets/67aca67bcaea3ae62308114f/"

# Default name for the integration's device.
DEFAULT_NAME = "LU-Alert"

# Default update interval for the coordinator.
# 5 minutes is a reasonable default to avoid spamming the API.
DEFAULT_SCAN_INTERVAL = 300  # seconds

# Configuration keys
CONF_MIN_SEVERITY = "min_severity"
CONF_ENABLE_LOCATION_FILTER = "enable_location_filter"
CONF_LATITUDE = "latitude"
CONF_LONGITUDE = "longitude"
CONF_WATCHLIST_KEYWORDS = "watchlist_keywords"
CONF_ALLERGENS = "allergens"


# Default values
DEFAULT_MIN_SEVERITY = "Unknown"
DEFAULT_ENABLE_LOCATION_FILTER = False
DEFAULT_WATCHLIST_KEYWORDS = ""
DEFAULT_ALLERGENS = []

# List of common allergens for the config flow
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


# Number of alert sensor sets to create
MAX_ALERTS = 3
