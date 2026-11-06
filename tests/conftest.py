"""Test set-up: the integration is loaded from this repository, in a real Home Assistant test instance."""
import os
import time

import aiohttp
import aiohttp.connector

# Home Assistant's test dependencies install aiodns. aiohttp then selects its
# pycares-based AsyncResolver by default, which starts a background shutdown
# thread. Use aiohttp's standard threaded resolver for every test-created
# connector/session, including those created inside Home Assistant fixtures.
aiohttp.connector.DefaultResolver = aiohttp.ThreadedResolver

# Alert end times are shown in the time zone of the machine: tests run in UTC.
os.environ["TZ"] = "UTC"
if hasattr(time, "tzset"):
    time.tzset()

# This import must come before the Home Assistant test plugin puts its own custom_components folder on sys.path.
import custom_components  # noqa: E402,F401

import pytest  # noqa: E402

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Let the tests load custom_components/lu_alert."""
    yield
