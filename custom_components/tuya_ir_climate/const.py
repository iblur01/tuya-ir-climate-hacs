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
CONF_TEMP_SENSOR = "temp_sensor"
CONF_DELTA = "delta"
CONF_MIN_CYCLE = "min_cycle_duration"

DEFAULT_DELTA = 0.5
MIN_DELTA = 0.1
MAX_DELTA = 5.0
DEFAULT_MIN_CYCLE = 300
MIN_MIN_CYCLE = 0
MAX_MIN_CYCLE = 3600

DEFAULT_NAME = "Tuya IR Climate"
DEFAULT_REGION = "eu"
DEFAULT_INFRARED_ID = ""
REGION_OPTIONS = ["cn", "us", "us-e", "eu", "eu-w", "in", "sg"]

DEFAULT_SCAN_INTERVAL = timedelta(seconds=10)
MIN_SCAN_INTERVAL = 5
MAX_SCAN_INTERVAL = 300

TUYA_MODE_COOL = 0
TUYA_MODE_DRY = 4

TUYA_FAN_AUTO = 0
TUYA_FAN_LOW = 1
TUYA_FAN_HIGH = 3
