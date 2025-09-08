import asyncio
from unittest.mock import MagicMock

from custom_components.lu_alert.coordinator import LuAlertDataUpdateCoordinator
from custom_components.lu_alert.sensor import LuAlertDescriptionSensor, _strip_html

async def main():
    """Test the coordinator."""
    hass = MagicMock()
    entry = MagicMock()

    # Set up the config entry mock
    entry.options = {}

    # Set up the hass mock for async_add_executor_job
    async def dummy_async_add_executor_job(func, *args):
        return func(*args)

    hass.async_add_executor_job = dummy_async_add_executor_job


    coordinator = LuAlertDataUpdateCoordinator(hass, entry)
    await coordinator.async_refresh()

    print("--- Coordinator Data ---")
    print(coordinator.data)

    print("\n--- Fetched Data ---")
    data = coordinator.data
    if data:
        print(f"Headline: {data.get('headline')}")
        print(f"Count: {data.get('count')}")
        for i, alert_data in enumerate(data.get('alerts', [])):
            print("--- Alert ---")
            print(f"  Headline: {alert_data.get('headline')}")
            print(f"  Severity: {alert_data.get('severity')}")
            print(f"  Event: {alert_data.get('event')}")

            # Test the description sensor
            desc_sensor = LuAlertDescriptionSensor(coordinator, entry, i)
            print(f"  Description (State): {desc_sensor.native_value}")
            full_desc = desc_sensor.extra_state_attributes.get('full_description') if desc_sensor.extra_state_attributes else "Not Available"
            print(f"  Description (Attribute): {full_desc}")

            print(f"  Sent: {alert_data.get('sent')}")

if __name__ == "__main__":
    asyncio.run(main())
