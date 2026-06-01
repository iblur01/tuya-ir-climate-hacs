"""Climate platform for Tuya IR Climate.

The split's own thermostat reacts to its badly-placed internal sensor, so it
keeps the compressor running (and noisy) even when the room is already cold.
This entity owns the user intent on the Home Assistant side and regulates the
IR unit against an external room sensor: it powers the unit on/off with a
hysteresis band and an anti-short-cycle guard instead of blindly mapping the
target temperature onto the IR remote.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_TEMPERATURE,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfTemperature,
)
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN
from .coordinator import TuyaIRClimateCoordinator
from .entity import TuyaIRClimateEntity

_LOGGER = logging.getLogger(__name__)

FAN_AUTO = "auto"
FAN_LOW = "low"
FAN_HIGH = "high"

DEFAULT_TARGET_TEMP = 24

# What we last pushed to the IR unit. "cool_idle" means the cooling intent is
# active but the room is cold enough that we cut power (the user-facing mode
# stays COOL). Both "off" and "cool_idle" leave the unit unpowered.
PROFILE_OFF = "off"
PROFILE_COOL = "cool"
PROFILE_COOL_IDLE = "cool_idle"
PROFILE_DRY = "dry"

_PROFILE_POWERED = {
    PROFILE_OFF: False,
    PROFILE_COOL_IDLE: False,
    PROFILE_COOL: True,
    PROFILE_DRY: True,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Tuya IR climate entity."""
    coordinator: TuyaIRClimateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([TuyaIRClimate(coordinator)])


class TuyaIRClimate(TuyaIRClimateEntity, ClimateEntity, RestoreEntity):
    """Tuya IR air conditioner regulated against an external room sensor."""

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
        self._hvac_mode: HVACMode = HVACMode.OFF
        self._fan_mode: str = FAN_AUTO
        self._attr_target_temperature: float = DEFAULT_TARGET_TEMP
        # Last command profile actually pushed to the IR unit.
        self._applied: str = PROFILE_OFF
        # Monotonic timestamp of the last power transition, for the min-cycle
        # guard. None until the first switch so the first action is immediate.
        self._last_switch: float | None = None

    async def async_added_to_hass(self) -> None:
        """Restore state and start listening to the room sensor."""
        await super().async_added_to_hass()

        if (last_state := await self.async_get_last_state()) is not None:
            if last_state.state in self._attr_hvac_modes:
                self._hvac_mode = HVACMode(last_state.state)
            target = last_state.attributes.get(ATTR_TEMPERATURE)
            if target is not None:
                self._attr_target_temperature = float(target)
            fan = last_state.attributes.get("fan_mode")
            if fan in self._attr_fan_modes:
                self._fan_mode = fan

        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                [self.coordinator.device.temp_sensor],
                self._async_sensor_changed,
            )
        )
        # Apply the restored intent against the current room temperature.
        await self._async_control(force=True)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return super().available and bool(self.coordinator.data)

    @property
    def current_temperature(self) -> float | None:
        """Return the room temperature read from the external sensor."""
        state = self.hass.states.get(self.coordinator.device.temp_sensor)
        if state is None or state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            return None
        try:
            return float(state.state)
        except (TypeError, ValueError):
            return None

    @property
    def hvac_mode(self) -> HVACMode:
        """Return the user-selected HVAC mode (intent lives on the HA side)."""
        return self._hvac_mode

    @property
    def hvac_action(self) -> HVACAction:
        """Return what the unit is actually doing right now."""
        if self._hvac_mode == HVACMode.OFF:
            return HVACAction.OFF
        if self._hvac_mode == HVACMode.DRY:
            return HVACAction.DRYING
        return (
            HVACAction.COOLING
            if self._applied == PROFILE_COOL
            else HVACAction.IDLE
        )

    @property
    def fan_mode(self) -> str | None:
        """Return the current fan mode."""
        return self._fan_mode

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set HVAC mode."""
        if hvac_mode not in self._attr_hvac_modes:
            return
        self._hvac_mode = hvac_mode
        # A direct user command bypasses the anti-short-cycle guard.
        await self._async_control(force=True)
        self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set target temperature."""
        if ATTR_TEMPERATURE not in kwargs:
            return
        value = float(kwargs[ATTR_TEMPERATURE])
        self._attr_target_temperature = max(
            self.min_temp, min(self.max_temp, value)
        )
        await self._async_control()
        self.async_write_ha_state()

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set fan mode."""
        if fan_mode not in self._attr_fan_modes:
            return
        self._fan_mode = fan_mode
        # Push the new fan speed only while the unit is actually cooling.
        if self._applied == PROFILE_COOL:
            await self.coordinator.async_send_command("wind", self._tuya_fan())
        self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Re-run regulation on each poll to retry deferred min-cycle switches."""
        super()._handle_coordinator_update()
        self.hass.async_create_task(self._async_control())

    @callback
    def _async_sensor_changed(self, event: Event[EventStateChangedData]) -> None:
        """Regulate when the room temperature changes."""
        self.hass.async_create_task(self._async_control())

    async def _async_control(self, *, force: bool = False) -> None:
        """Decide which profile the IR unit should run, and apply it."""
        if self._hvac_mode == HVACMode.OFF:
            await self._apply_profile(PROFILE_OFF, force=force)
            return

        if self._hvac_mode == HVACMode.DRY:
            # Dehumidify mode is not temperature-regulated by us.
            await self._apply_profile(PROFILE_DRY, force=force)
            return

        # COOL: hysteresis around the target using the external room sensor.
        room = self.current_temperature
        if room is None:
            # No reliable reading: fail safe by keeping the unit cooling.
            _LOGGER.debug("Room sensor unavailable, keeping unit on as fallback")
            await self._apply_profile(PROFILE_COOL, force=force)
            return

        target = self._attr_target_temperature
        delta = self.coordinator.device.delta
        if self._applied == PROFILE_COOL:
            if room <= target - delta:
                await self._apply_profile(PROFILE_COOL_IDLE, force=force)
        elif room >= target + delta:
            await self._apply_profile(PROFILE_COOL, force=force)

    async def _apply_profile(self, profile: str, *, force: bool = False) -> None:
        """Push a command profile to the IR unit, honouring the min-cycle guard."""
        if profile == self._applied:
            return

        powering = _PROFILE_POWERED[profile] != _PROFILE_POWERED[self._applied]
        now = time.monotonic()
        if (
            powering
            and not force
            and self._last_switch is not None
            and now - self._last_switch < self.coordinator.device.min_cycle
        ):
            # Too soon since the last power transition; a later tick will retry.
            _LOGGER.debug("Min-cycle guard blocked profile %s", profile)
            return

        if profile == PROFILE_COOL:
            await self.coordinator.async_send_command(
                "mode", self.coordinator.device.mode_cool
            )
            await self.coordinator.async_send_command(
                "temp", int(self._attr_target_temperature)
            )
            await self.coordinator.async_send_command("wind", self._tuya_fan())
            await self.coordinator.async_send_command("power", 1)
        elif profile == PROFILE_DRY:
            await self.coordinator.async_send_command(
                "mode", self.coordinator.device.mode_dry
            )
            await self.coordinator.async_send_command(
                "wind", self.coordinator.device.fan_auto
            )
            await self.coordinator.async_send_command("power", 1)
        else:  # PROFILE_OFF or PROFILE_COOL_IDLE
            await self.coordinator.async_send_command("power", 0)

        if powering:
            self._last_switch = now
        self._applied = profile
        self.async_write_ha_state()

    def _tuya_fan(self) -> int:
        """Map the HA fan mode to the device-specific Tuya value."""
        return {
            FAN_AUTO: self.coordinator.device.fan_auto,
            FAN_LOW: self.coordinator.device.fan_low,
            FAN_HIGH: self.coordinator.device.fan_high,
        }.get(self._fan_mode, self.coordinator.device.fan_auto)
