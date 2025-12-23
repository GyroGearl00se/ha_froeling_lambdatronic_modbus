"""Select entity for Fröling Lambdatronic Modbus."""

import logging
from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.translation import async_get_translations

from .const import DOMAIN
from .coordinator import FroelingDataUpdateCoordinator
from .entity_definitions import ENTITY_DEFINITIONS

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """Set up the select platform."""
    entry = hass.data[DOMAIN][config_entry.entry_id]
    coordinator: FroelingDataUpdateCoordinator = entry["coordinator"]
    config = entry["config"]

    enabled_entities = config.get("entities", {})
    translations = await async_get_translations(hass, hass.config.language, "entity")

    selects = []
    for category, entities in enabled_entities.items():
        if category in ENTITY_DEFINITIONS:
            for entity_id in entities:
                if entity_id in ENTITY_DEFINITIONS[category]:
                    definition = ENTITY_DEFINITIONS[category][entity_id]
                    if definition.get("type") == "select":
                        selects.append(
                            FroelingSelect(coordinator, config, entity_id, translations)
                        )

    async_add_entities(selects)


class FroelingSelect(CoordinatorEntity[FroelingDataUpdateCoordinator], SelectEntity):
    """A Fröling select entity that fetches data from the coordinator."""

    def __init__(
        self,
        coordinator: FroelingDataUpdateCoordinator,
        config: dict[str, Any],
        entity_id: str,
        translations: dict[str, Any],
    ):
        """Initialize the select entity."""
        super().__init__(coordinator)
        self._entity_id = entity_id
        self._device_name = config["name"]
        self.entity_definition = coordinator._entity_definitions[entity_id]

        self._attr_unique_id = f"{self._device_name}_{self._entity_id}"
        
        translated_name = translations.get(
            f"component.froeling_lambdatronic_modbus.entity.select.{self._entity_id}.name",
            self._entity_id.replace("_", " ").title(),
        )
        self._attr_name = f"{self._device_name} {translated_name}"
        self._attr_options = self.entity_definition.get("options", [])

    @property
    def current_option(self) -> str | None:
        """Return the currently selected option."""
        index = self.coordinator.data.get(self._entity_id)
        if index is not None and 0 <= index < len(self.options):
            return self.options[index]
        return None

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        if option not in self.options:
            _LOGGER.warning("Selected option '%s' is not valid", option)
            return

        index = self.options.index(option)
        register = self.entity_definition.get("register")

        if register is None:
            _LOGGER.error("No register defined for %s", self.entity_id)
            return

        await self.coordinator.controller.async_write_register(register - 40001, index)
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
