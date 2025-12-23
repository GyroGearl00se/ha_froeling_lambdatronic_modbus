"""Number entity for Fröling Lambdatronic Modbus."""

import logging
from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import FroelingDataUpdateCoordinator
from .entity_definitions import ENTITY_DEFINITIONS

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """Set up the number platform."""
    entry = hass.data[DOMAIN][config_entry.entry_id]
    coordinator: FroelingDataUpdateCoordinator = entry["coordinator"]
    config = entry["config"]

    enabled_entities = config.get("entities", {})

    numbers = []
    for category, entities in enabled_entities.items():
        if category in ENTITY_DEFINITIONS:
            for entity_id in entities:
                if entity_id in ENTITY_DEFINITIONS[category]:
                    definition = ENTITY_DEFINITIONS[category][entity_id]
                    if definition.get("type") == "number":
                        numbers.append(
                            FroelingNumber(coordinator, config, entity_id)
                        )

    async_add_entities(numbers)


class FroelingNumber(CoordinatorEntity[FroelingDataUpdateCoordinator], NumberEntity):
    """A Fröling number entity that fetches data from the coordinator."""

    def __init__(
        self,
        coordinator: FroelingDataUpdateCoordinator,
        config: dict[str, Any],
        entity_id: str,
    ):
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._entity_id = entity_id
        self._device_name = config["name"]
        self.entity_definition = coordinator._entity_definitions[entity_id]

        self._attr_unique_id = f"{self._device_name}_{self._entity_id}"
        self._attr_has_entity_name = True
        self._attr_translation_key = self._entity_id

        self._attr_native_unit_of_measurement = self.entity_definition.get("unit")
        self._attr_native_min_value = self.entity_definition.get("min", 0)
        self._attr_native_max_value = self.entity_definition.get("max", 100)
        self._attr_mode = self.entity_definition.get("mode", NumberMode.BOX)

        scaling = self.entity_definition.get("scaling", 1)
        if scaling != 0:
            self._attr_native_step = 1.0 / scaling
        else:
            self._attr_native_step = 1.0

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        value = self.coordinator.data.get(self._entity_id)
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        scaling_factor = self.entity_definition.get("scaling", 1)
        register = self.entity_definition.get("register")

        if scaling_factor == 0 or register is None:
            _LOGGER.error("Invalid entity definition for %s", self.entity_id)
            return

        scaled_value = int(round(value * scaling_factor))
        
        await self.coordinator.controller.async_write_register(
            register - 40001, scaled_value
        )
        await self.coordinator.async_refresh_entity(self._entity_id)

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_name)},
            name=self._device_name,
            manufacturer="Froeling",
            model="Lambdatronic Modbus",
            sw_version="1.0",
        )

