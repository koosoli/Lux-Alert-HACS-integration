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
