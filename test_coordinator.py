"""Legacy manual coordinator smoke script retired.

The real coordinator tests belong under tests/ and use pytest with a Home Assistant test instance.
This file intentionally contains no executable network test so pytest collection cannot accidentally
run an unmocked live-feed request.
