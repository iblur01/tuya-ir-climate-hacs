"""Shared entity helpers for Tuya IR Climate."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import TuyaIRClimateCoordinator


class TuyaIRClimateEntity(CoordinatorEntity[TuyaIRClimateCoordinator]):
    """Base class for Tuya IR Climate entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: TuyaIRClimateCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.device.remote_id}_{key}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return Home Assistant device registry information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.device.remote_id)},
            manufacturer="Tuya",
            model="Infrared air conditioner",
            name=self.coordinator.device.name,
            via_device=(DOMAIN, self.coordinator.device.infrared_id),
        )
