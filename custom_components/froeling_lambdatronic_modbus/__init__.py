"""Integration for Fröling Lambdatronic Modbus."""

from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .coordinator import FroelingDataUpdateCoordinator
from .modbus_controller import ModbusController

DOMAIN = "froeling_lambdatronic_modbus"
_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required("name", default="Froeling"): cv.string,
                vol.Required("host"): cv.string,
                vol.Required("port", default=502): cv.port,
                vol.Optional("device_id", default=2): cv.positive_int,
                vol.Required("update_interval", default=60): cv.positive_int,
                vol.Optional("kessel", default=True): cv.boolean,
                vol.Optional("fehlerpuffer", default=True): cv.boolean,
                vol.Optional("boiler01", default=True): cv.boolean,
                vol.Optional("boiler02", default=True): cv.boolean,
                vol.Optional("hk01", default=True): cv.boolean,
                vol.Optional("hk02", default=True): cv.boolean,
                vol.Optional("hk03", default=True): cv.boolean,
                vol.Optional("hk04", default=True): cv.boolean,
                vol.Optional("austragung", default=True): cv.boolean,
                vol.Optional("puffer01", default=True): cv.boolean,
                vol.Optional("puffer02", default=True): cv.boolean,
                vol.Optional("puffer03", default=True): cv.boolean,
                vol.Optional("puffer04", default=True): cv.boolean,
                vol.Optional("zirkulationspumpe", default=True): cv.boolean,
                vol.Optional("zweitkessel", default=True): cv.boolean,
                vol.Optional("solarthermie", default=True): cv.boolean,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Fröling component from YAML."""
    if DOMAIN not in config:
        return True

    domain_config = config[DOMAIN]
    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_IMPORT},
            data=domain_config,
        )
    )
    return True


PLATFORMS = [Platform.BINARY_SENSOR, Platform.NUMBER, Platform.SELECT, Platform.SENSOR]


async def async_cleanup_and_reload(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update, cleanup removed entities, and reload."""

    old_config = hass.data[DOMAIN][entry.entry_id]["config"]
    old_entities_by_cat = old_config.get("entities", {})
    old_entity_ids = {
        entity_id
        for cat_entities in old_entities_by_cat.values()
        for entity_id in cat_entities
    }

    new_options = entry.options
    new_entities_by_cat = new_options.get("entities", {})
    new_entity_ids = {
        entity_id
        for cat_entities in new_entities_by_cat.values()
        for entity_id in cat_entities
    }

    entity_ids_to_remove = old_entity_ids - new_entity_ids

    if entity_ids_to_remove:
        ent_reg = er.async_get(hass)
        device_name = old_config.get("name", "Froeling")

        all_entities = [
            entity
            for entity in ent_reg.entities.values()
            if entity.config_entry_id == entry.entry_id
        ]

        for entity_entry in all_entities:
            prefix = f"{device_name}_"
            if entity_entry.unique_id.startswith(prefix):
                entity_id_from_unique_id = entity_entry.unique_id[len(prefix) :]
                if entity_id_from_unique_id in entity_ids_to_remove:
                    ent_reg.async_remove(entity_entry.entity_id)
                    _LOGGER.debug("Removed entity: %s", entity_entry.entity_id)

    if not new_entity_ids and old_entity_ids:
        dev_reg = dr.async_get(hass)
        device_name = old_config.get("name", "Froeling")
        device_to_remove = dev_reg.async_get_device(identifiers={(DOMAIN, device_name)})
        if device_to_remove:
            try:
                dev_reg.async_remove_device(device_to_remove.id)
                _LOGGER.debug("Removed device: %s", device_name)
            except Exception as e:
                _LOGGER.warning("Could not remove device %s: %s", device_name, e)

    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up platform from a ConfigEntry."""
    hass.data.setdefault(DOMAIN, {})
    config = {**entry.data, **entry.options}

    controller = ModbusController(
        hass,
        config.get("host", ""),
        config.get("port", 502),
        device_id=config.get("device_id", 2),
        timeout=config.get("timeout", 10),
        retries=config.get("retries", 1),
        reconnect_delay=config.get("reconnect_delay", 30),
    )
    coordinator = FroelingDataUpdateCoordinator(
        hass, controller=controller, config=config, config_entry=entry
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        "config": config,
        "coordinator": coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_cleanup_and_reload))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        entry_data = hass.data[DOMAIN].pop(entry.entry_id)
        if "coordinator" in entry_data:
            coordinator: FroelingDataUpdateCoordinator = entry_data["coordinator"]
            await coordinator.controller.async_close()
    return unload_ok
