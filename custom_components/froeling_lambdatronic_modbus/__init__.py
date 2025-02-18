

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform

DOMAIN = "froeling_modbus"

async def async_setup(hass, config):
    return True

PLATFORMS = [Platform.SENSOR, Platform.NUMBER, Platform.BINARY_SENSOR]

async def async_setup_entry(hass, entry):
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass, entry):
    for platform in PLATFORMS:
        await hass.config_entries.async_forward_entry_unload(entry, platform)
    hass.data[DOMAIN].pop(entry.entry_id)
    return True