"""Climate platform for Tuya IR Climate."""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature, HVACMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
)
from .coordinator import TuyaIRClimateCoordinator
from .entity import TuyaIRClimateEntity

FAN_AUTO = "auto"
FAN_LOW = "low"
FAN_HIGH = "high"

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Tuya IR climate entity."""
    coordinator: TuyaIRClimateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([TuyaIRClimate(coordinator)])


class TuyaIRClimate(TuyaIRClimateEntity, ClimateEntity):
    """Tuya IR air conditioner climate entity."""

    _attr_name = None
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.FAN_MODE
    )
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_min_temp = 16
    _attr_max_temp = 30
    _attr_target_temperature_step = 1
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.COOL, HVACMode.DRY]
    _attr_fan_modes = [FAN_AUTO, FAN_LOW, FAN_HIGH]

    def __init__(self, coordinator: TuyaIRClimateCoordinator) -> None:
        super().__init__(coordinator, "climate")

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return super().available and bool(self.coordinator.data)

    @property
    def hvac_mode(self) -> HVACMode:
        """Return current HVAC mode from Tuya cloud shadow."""
        if self._value("power") == 0:
            return HVACMode.OFF
        if self._value("mode") == self.coordinator.device.mode_dry:
            return HVACMode.DRY
        return HVACMode.COOL

    @property
    def target_temperature(self) -> int | None:
        """Return target temperature."""
        return self._value("temp")

    @property
    def fan_mode(self) -> str | None:
        """Return current fan mode."""
        fan = self._value("wind")
        if fan is None:
            return None
        return {
            self.coordinator.device.fan_auto: FAN_AUTO,
            self.coordinator.device.fan_low: FAN_LOW,
            self.coordinator.device.fan_high: FAN_HIGH,
        }.get(fan, FAN_AUTO)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set HVAC mode."""
        if hvac_mode == HVACMode.OFF:
            await self.coordinator.async_send_command("power", 0)
            return

        if hvac_mode == HVACMode.DRY:
            await self.coordinator.async_send_command(
                "mode", self.coordinator.device.mode_dry
            )
            await self.coordinator.async_send_command(
                "wind", self.coordinator.device.fan_auto
            )
            await self.coordinator.async_send_command("power", 1)
            return

        if hvac_mode == HVACMode.COOL:
            await self.coordinator.async_send_command(
                "mode", self.coordinator.device.mode_cool
            )
            await self.coordinator.async_send_command("power", 1)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set target temperature."""
        if ATTR_TEMPERATURE not in kwargs:
            return
        value = int(kwargs[ATTR_TEMPERATURE])
        value = max(self.min_temp, min(self.max_temp, value))
        await self.coordinator.async_send_command("temp", value)

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set fan mode."""
        value = {
            FAN_AUTO: self.coordinator.device.fan_auto,
            FAN_LOW: self.coordinator.device.fan_low,
            FAN_HIGH: self.coordinator.device.fan_high,
        }.get(fan_mode)
        if value is None:
            return
        await self.coordinator.async_send_command("wind", value)

    def _value(self, key: str) -> int | None:
        """Return an integer value from coordinator data."""
        data = self.coordinator.data or {}
        value = data.get(key)
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
