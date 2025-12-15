"""Binary Sensor for Fröling Lambdatronic Modbus."""

import logging
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.translation import async_get_translations

from .const import DOMAIN
from .coordinator import FroelingDataUpdateCoordinator
from .entity_definitions import ENTITY_DEFINITIONS

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """Set up the binary sensor platform."""
    entry = hass.data[DOMAIN][config_entry.entry_id]
    coordinator: FroelingDataUpdateCoordinator = entry["coordinator"]
    config = entry["config"]

    enabled_entities = config.get("entities", {})
    translations = await async_get_translations(hass, hass.config.language, "entity")

    binary_sensors = []
    for category, entities in enabled_entities.items():
        if category in ENTITY_DEFINITIONS:
            for entity_id in entities:
                if entity_id in ENTITY_DEFINITIONS[category]:
                    definition = ENTITY_DEFINITIONS[category][entity_id]
                    if definition.get("type") in [
                        "binary_sensor",
                        "binary_sensor_from_register",
                    ]:
                        binary_sensors.append(
                            FroelingBinarySensor(
                                coordinator, config, entity_id, translations
                            )
                        )

    async_add_entities(binary_sensors)


class FroelingBinarySensor(
    CoordinatorEntity[FroelingDataUpdateCoordinator], BinarySensorEntity
):
    """A binary sensor that fetches data from the coordinator."""

    def __init__(
        self,
        coordinator: FroelingDataUpdateCoordinator,
        config: dict[str, Any],
        entity_id: str,
        translations: dict[str, Any],
    ):
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._entity_id = entity_id
        self._device_name = config["name"]

        self._attr_unique_id = f"{self._device_name}_{self._entity_id}"
        
        translated_name = translations.get(
            f"component.froeling_lambdatronic_modbus.entity.binary_sensor.{self._entity_id}.name",
            self._entity_id.replace("_", " ").title(),
        )
        self._attr_name = f"{self._device_name} {translated_name}"

    @property
    def is_on(self) -> bool | None:
        """Return the state of the binary sensor."""
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
