from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform
import voluptuous as vol
import homeassistant.helpers.config_validation as cv

from .modbus_controller import ModbusController

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
                vol.Optional("zweitkessel", default=True): cv.boolean
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

async def async_setup(hass: HomeAssistant, config: dict):
    return True

PLATFORMS = [Platform.SENSOR, Platform.NUMBER, Platform.BINARY_SENSOR, Platform.SELECT]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    hass.data.setdefault(DOMAIN, {})
    controller = ModbusController(hass, entry.data.get("host"), entry.data.get("port", 502))
    hass.data[DOMAIN][entry.entry_id] = {"config": entry.data, "controller": controller}
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    for platform in PLATFORMS:
        await hass.config_entries.async_forward_entry_unload(entry, platform)
    ent = hass.data[DOMAIN].pop(entry.entry_id, None)
    if ent and isinstance(ent, dict) and "controller" in ent:
        try:
            await ent["controller"].async_close()
        except Exception:
            pass
    return True