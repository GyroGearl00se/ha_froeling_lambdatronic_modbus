"""Time entity for Fröling Lambdatronic Modbus."""

from __future__ import annotations

import datetime
import logging
from typing import Any

from homeassistant.components.time import TimeEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from modbus_connection import ModbusError

from .const import DOMAIN
from .coordinator import FroelingDataUpdateCoordinator
from .entity_definitions import ENTITY_DEFINITIONS

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """Set up the time platform."""
    entry = hass.data[DOMAIN][config_entry.entry_id]
    coordinator: FroelingDataUpdateCoordinator = entry["coordinator"]
    config = entry["config"]

    enabled_entities = config.get("entities", {})

    times = []
    for category, entities in enabled_entities.items():
        if category in ENTITY_DEFINITIONS:
            for entity_id in entities:
                if entity_id in ENTITY_DEFINITIONS[category]:
                    definition = ENTITY_DEFINITIONS[category][entity_id]
                    if definition.get("type") == "time":
                        times.append(FroelingTime(coordinator, config, entity_id))

    async_add_entities(times)


class FroelingTime(CoordinatorEntity[FroelingDataUpdateCoordinator], TimeEntity):
    """A Fröling time entity that fetches data from the coordinator."""

    def __init__(
        self,
        coordinator: FroelingDataUpdateCoordinator,
        config: dict[str, Any],
        entity_id: str,
    ):
        """Initialize the time entity."""
        super().__init__(coordinator)
        self._entity_id = entity_id
        self._device_name = config["name"]
        self.entity_definition = coordinator._entity_definitions[entity_id]

        self._attr_unique_id = f"{self._device_name}_{self._entity_id}"
        self._attr_has_entity_name = True
        self._attr_translation_key = self._entity_id

    @property
    def native_value(self) -> datetime.time | None:
        """Return the value reported by the time entity."""
        raw_minutes = self.coordinator.data.get(self._entity_id)
        if raw_minutes is None:
            return None

        try:
            total_minutes = int(raw_minutes)
        except (ValueError, TypeError):
            return None

        # 1440 minutes corresponds to 24:00 (end of day). datetime.time max is 23:59:59.
        if total_minutes >= 1440:
            return datetime.time(23, 59, 59)
        if total_minutes < 0:
            return datetime.time(0, 0)

        hours = total_minutes // 60
        minutes = total_minutes % 60
        return datetime.time(hours, minutes)

    async def async_set_value(self, value: datetime.time) -> None:
        """Update the time value in the boiler register."""
        register = self.entity_definition.get("register")
        if register is None:
            _LOGGER.error("Invalid entity definition for %s: missing register", self.entity_id)
            return

        total_minutes = value.hour * 60 + value.minute

        try:
            _LOGGER.debug(
                "Writing time entity %s (%s -> %s min) to register %s",
                self._entity_id,
                value,
                total_minutes,
                register,
            )
            await self.coordinator.unit.write_register(register - 40001, total_minutes)
        except ModbusError as exc:
            raise HomeAssistantError(
                f"Could not write value for {self._entity_id}"
            ) from exc
        await self.coordinator.async_refresh_entity(self._entity_id)

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_name)},
            name=self._device_name,
            manufacturer="Froeling",
            model="Lambdatronic Modbus",
        )
