"""Fröling Lambdatronic Modbus Sensor."""

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.translation import async_get_translations
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import FroelingDataUpdateCoordinator
from .entity_definitions import ENTITY_DEFINITIONS

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """Set up the sensor platform."""
    entry = hass.data[DOMAIN][config_entry.entry_id]
    coordinator: FroelingDataUpdateCoordinator = entry["coordinator"]
    config = entry["config"]

    enabled_entities = config.get("entities", {})
    translations = await async_get_translations(hass, hass.config.language, "entity")

    sensors = []
    for category, entities in enabled_entities.items():
        if category in ENTITY_DEFINITIONS:
            for entity_id in entities:
                if entity_id in ENTITY_DEFINITIONS[category]:
                    definition = ENTITY_DEFINITIONS[category][entity_id]
                    if definition.get("type") in ["sensor", "text"]:
                        sensors.append(
                            FroelingSensor(coordinator, config, entity_id, translations)
                        )

    async_add_entities(sensors)


class FroelingSensor(CoordinatorEntity[FroelingDataUpdateCoordinator], SensorEntity):
    """A Fröling sensor that fetches data from the coordinator."""

    def __init__(
        self,
        coordinator: FroelingDataUpdateCoordinator,
        config: dict[str, Any],
        entity_id: str,
        translations: dict[str, Any],
    ):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entity_id = entity_id
        self._device_name = config["name"]
        self.entity_definition = coordinator._entity_definitions[entity_id]

        self._attr_unique_id = f"{self._device_name}_{self._entity_id}"

        translated_name = translations.get(
            f"component.froeling_lambdatronic_modbus.entity.sensor.{self._entity_id}.name",
            self._entity_id.replace("_", " ").title(),
        )
        self._attr_name = f"{self._device_name} {translated_name}"

        self._attr_native_unit_of_measurement = self.entity_definition.get("unit")
        self._attr_device_class = self.entity_definition.get("device_class")

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        return self.coordinator.data.get(self._entity_id)

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
