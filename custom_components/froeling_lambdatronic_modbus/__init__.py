from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform
import voluptuous as vol
import homeassistant.helpers.config_validation as cv

DOMAIN = "froeling_lambdatronic_modbus"

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required("name", default="Froeling"): cv.string,
                vol.Required("host"): cv.string,
                vol.Required("port", default=502): cv.port,
                vol.Required("update_interval", default=60): cv.positive_int,
                vol.Optional("kessel", default=True): cv.boolean,
                vol.Optional("boiler01", default=True): cv.boolean,
                vol.Optional("hk01", default=True): cv.boolean,
                vol.Optional("hk02", default=True): cv.boolean,
                vol.Optional("austragung", default=True): cv.boolean,
                vol.Optional("puffer01", default=True): cv.boolean,
                vol.Optional("zirkulationspumpe", default=True): cv.boolean,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

async def async_setup(hass: HomeAssistant, config: dict):
    return True

PLATFORMS = [Platform.SENSOR, Platform.NUMBER, Platform.BINARY_SENSOR]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    for platform in PLATFORMS:
        await hass.config_entries.async_forward_entry_unload(entry, platform)
    hass.data[DOMAIN].pop(entry.entry_id)
    return True