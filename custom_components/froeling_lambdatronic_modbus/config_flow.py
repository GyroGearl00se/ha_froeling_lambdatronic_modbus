import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN

@config_entries.HANDLERS.register(DOMAIN)
class FroelingModbusConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title=user_input["name"], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("name", default="Froeling"): str,
                vol.Required("host"): str,
                vol.Required("port", default=502): int,
                vol.Required("update_interval", default=60): int,
                vol.Optional("kessel", default=True): bool,
                vol.Optional("fehlerpuffer", default=True): bool,
                vol.Optional("boiler01", default=True): bool,
                vol.Optional("hk01", default=True): bool,
                vol.Optional("hk02", default=True): bool,
                vol.Optional("austragung", default=True): bool,
                vol.Optional("puffer01", default=True): bool,
                vol.Optional("zirkulationspumpe", default=True): bool
            })
        )