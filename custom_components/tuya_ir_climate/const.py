"""Constants for Tuya IR Climate."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.const import Platform

DOMAIN = "tuya_ir_climate"
PLATFORMS = [Platform.CLIMATE]

CONF_API_KEY = "api_key"
CONF_API_SECRET = "api_secret"
CONF_REGION = "region"
CONF_INFRARED_ID = "infrared_id"
CONF_REMOTE_ID = "remote_id"
CONF_DEVICE_NAME = "device_name"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_MODE_COOL = "mode_cool"
CONF_MODE_DRY = "mode_dry"
CONF_FAN_AUTO = "fan_auto"
CONF_FAN_LOW = "fan_low"
CONF_FAN_HIGH = "fan_high"

DEFAULT_NAME = "Tuya IR Climate"
DEFAULT_REGION = "eu"
DEFAULT_INFRARED_ID = "bf2b843da25ca8b275uy7a"
REGION_OPTIONS = ["cn", "us", "us-e", "eu", "eu-w", "in", "sg"]

DEFAULT_SCAN_INTERVAL = timedelta(seconds=10)
MIN_SCAN_INTERVAL = 5
MAX_SCAN_INTERVAL = 300

TUYA_MODE_COOL = 0
TUYA_MODE_DRY = 4

TUYA_FAN_AUTO = 0
TUYA_FAN_LOW = 1
TUYA_FAN_HIGH = 3
