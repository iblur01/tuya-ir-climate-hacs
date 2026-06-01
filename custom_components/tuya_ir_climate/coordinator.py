"""Coordinator for Tuya IR Climate."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import TuyaIRClimateAPI, TuyaIRClimateError
from .const import (
    CONF_API_KEY,
    CONF_API_SECRET,
    CONF_DELTA,
    CONF_DEVICE_NAME,
    CONF_FAN_AUTO,
    CONF_FAN_HIGH,
    CONF_FAN_LOW,
    CONF_INFRARED_ID,
    CONF_MIN_CYCLE,
    CONF_MODE_COOL,
    CONF_MODE_DRY,
    CONF_REGION,
    CONF_REMOTE_ID,
    CONF_SCAN_INTERVAL,
    CONF_TEMP_SENSOR,
    DEFAULT_DELTA,
    DEFAULT_MIN_CYCLE,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    TUYA_FAN_AUTO,
    TUYA_FAN_HIGH,
    TUYA_FAN_LOW,
    TUYA_MODE_COOL,
    TUYA_MODE_DRY,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class TuyaIRClimateDevice:
    """Static metadata for the IR climate device."""

    infrared_id: str
    remote_id: str
    name: str
    mode_cool: int
    mode_dry: int
    fan_auto: int
    fan_low: int
    fan_high: int
    temp_sensor: str
    delta: float
    min_cycle: int


class TuyaIRClimateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Central polling and command coordinator."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: TuyaIRClimateAPI,
        device: TuyaIRClimateDevice,
        scan_interval: timedelta,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}-{device.remote_id}",
            update_interval=scan_interval,
        )
        self.api = api
        self.device = device

    @classmethod
    def from_entry_data(
        cls,
        hass: HomeAssistant,
        data: dict[str, Any],
        options: dict[str, Any],
    ) -> "TuyaIRClimateCoordinator":
        """Build a coordinator from config entry data."""
        api = TuyaIRClimateAPI(
            data[CONF_API_KEY],
            data[CONF_API_SECRET],
            data[CONF_REGION],
            data[CONF_INFRARED_ID],
            data[CONF_REMOTE_ID],
        )
        device = TuyaIRClimateDevice(
            infrared_id=data[CONF_INFRARED_ID],
            remote_id=data[CONF_REMOTE_ID],
            name=data.get(CONF_DEVICE_NAME, DEFAULT_NAME),
            mode_cool=int(data.get(CONF_MODE_COOL, TUYA_MODE_COOL)),
            mode_dry=int(data.get(CONF_MODE_DRY, TUYA_MODE_DRY)),
            fan_auto=int(data.get(CONF_FAN_AUTO, TUYA_FAN_AUTO)),
            fan_low=int(data.get(CONF_FAN_LOW, TUYA_FAN_LOW)),
            fan_high=int(data.get(CONF_FAN_HIGH, TUYA_FAN_HIGH)),
            temp_sensor=data[CONF_TEMP_SENSOR],
            delta=float(options.get(CONF_DELTA, DEFAULT_DELTA)),
            min_cycle=int(options.get(CONF_MIN_CYCLE, DEFAULT_MIN_CYCLE)),
        )
        interval = timedelta(
            seconds=int(options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL.seconds))
        )
        return cls(hass, api, device, interval)

    async def _async_setup(self) -> None:
        """Validate the cloud connection before the first refresh."""
        await self.hass.async_add_executor_job(self.api.test_connection)

    async def _async_update_data(self) -> dict[str, Any]:
        """Poll Tuya cloud shadow state."""
        try:
            return await self.hass.async_add_executor_job(self.api.get_status)
        except TuyaIRClimateError as ex:
            raise UpdateFailed(str(ex)) from ex

    async def async_send_command(self, code: str, value: int) -> None:
        """Send a command and refresh the cloud shadow."""
        try:
            await self.hass.async_add_executor_job(self.api.send_command, code, value)
        except TuyaIRClimateError as ex:
            raise HomeAssistantError(str(ex)) from ex

        optimistic = {**(self.data or {}), code: value}
        self.async_set_updated_data(optimistic)
        await self.async_request_refresh()
