"""Fröling Lambdatronic Modbus Config Flow."""

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.translation import async_get_translations

from .const import DOMAIN
from .entity_definitions import ENTITY_DEFINITIONS
from .modbus_controller import ModbusController

_LOGGER = logging.getLogger(__name__)

async def _read_value_helper(
    controller: ModbusController,
    definition: dict[str, Any],
    entity_id: str,
    platform: str,
    translations: dict,
) -> Any:
    """Read a value from the controller for preview purposes."""
    try:
        if "coil" in definition:
            result = await controller.async_read_coils(definition["coil"], count=1)
            if result and not result.isError():
                return result.bits[0]
        elif "discrete_input" in definition:
            result = await controller.async_read_discrete_inputs(definition["discrete_input"] - 10001, count=1)
            if result and not result.isError():
                return int(result.bits[0])
        elif "register" in definition:
            offset = (
                40001
                if definition.get("register_type") == "holding"
                or definition.get("type") in ["number", "select"]
                else 30001
            )
            read_method = (
                controller.async_read_holding_registers
                if offset == 40001
                else controller.async_read_input_registers
            )

            result = await read_method(definition["register"] - offset, count=1)

            if result and not result.isError():
                raw_value = result.registers[0]

                if definition.get("type") == "text":
                    if entity_id.startswith("kessel_fehlerpuffer_"):
                        state_translation_key = f"component.froeling_lambdatronic_modbus.entity.sensor.kessel_fehler.state.{raw_value}"
                    else:
                        state_translation_key = f"component.froeling_lambdatronic_modbus.entity.{platform}.{entity_id}.state.{raw_value}"
                    return translations.get(
                        state_translation_key, f"Unknown ({raw_value})"
                    )

                if (
                    raw_value > 32767
                    and definition.get("register_type") != "holding"
                    and definition.get("type") not in ["number", "select"]
                ):
                    raw_value -= 65536

                scaling = definition.get("scaling", 1)
                decimals = definition.get("decimals", 0)
                scaled_value = raw_value / scaling

                if decimals == 0:
                    return int(scaled_value)
                return round(scaled_value, decimals)
    except Exception as e:
        _LOGGER.error("Error reading value for preview: %s", e)
        return "Error reading value"
    return "N/A"


class FroelingModbusConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Fröling Lambdatronic Modbus."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self.config: dict[str, Any] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            controller = ModbusController(
                self.hass,
                user_input["host"],
                user_input["port"],
                device_id=user_input.get("device_id", 2),
            )

            if await controller.async_check_connection():
                read_result = await controller.async_read_input_registers(0, count=1)
                await controller.async_close()

                if read_result is None:
                    errors["base"] = "invalid_device_id"
                else:
                    self.config.update(user_input)
                    return await self.async_step_entities()
            else:
                await controller.async_close()
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("name", default="Froeling"): str,
                    vol.Required("host"): str,
                    vol.Required("port", default=502): int,
                    vol.Required("device_id", default=2): int,
                    vol.Required("update_interval", default=60): int,
                    vol.Required(
                        "categories", default=list(ENTITY_DEFINITIONS.keys())
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=list(ENTITY_DEFINITIONS.keys()),
                            multiple=True,
                            mode=selector.SelectSelectorMode.LIST,
                            translation_key="categories",
                        ),
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_entities(self, user_input: dict[str, Any] | None = None):
        """Handle the entities step."""
        if user_input is not None:
            self.config["entities"] = user_input
            return self.async_create_entry(title=self.config["name"], data=self.config)

        schema = {}
        controller = ModbusController(
            self.hass,
            self.config["host"],
            self.config["port"],
            device_id=self.config.get("device_id", 2),
        )

        if not await controller.async_check_connection():
            await controller.async_close()
            return self.async_abort(reason="cannot_connect")

        translations = await async_get_translations(
            self.hass, self.hass.config.language, "entity", integrations=[DOMAIN]
        )

        for category in self.config.get("categories", []):
            if category in ENTITY_DEFINITIONS:
                options = []
                for entity_id, definition in ENTITY_DEFINITIONS[category].items():
                    platform = definition.get("type", "sensor")
                    if platform == "binary_sensor_from_register":
                        platform = "binary_sensor"
                    if platform == "text":
                        platform = "sensor"
                    translation_key = f"component.froeling_lambdatronic_modbus.entity.{platform}.{entity_id}.name"
                    translated_name = translations.get(translation_key, entity_id)

                    value = await _read_value_helper(
                        controller, definition, entity_id, platform, translations
                    )

                    options.append(
                        {"label": f"{translated_name}: {value}", "value": entity_id}
                    )

                default_values = [opt["value"] for opt in options]

                schema[vol.Required(category, default=default_values)] = (
                    selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=options,
                            multiple=True,
                            mode=selector.SelectSelectorMode.LIST,
                        ),
                    )
                )

        await controller.async_close()

        return self.async_show_form(
            step_id="entities",
            data_schema=vol.Schema(schema),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        """Get the options flow for this handler."""
        return FroelingOptionsFlowHandler()


class FroelingOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Fröling Lambdatronic Modbus."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Handle the initial options step."""
        if user_input is not None:
            new_options = dict(self.config_entry.options)
            new_options["entities"] = user_input
            return self.async_create_entry(title="", data=new_options)

        config = {**self.config_entry.data, **self.config_entry.options}

        translations = await async_get_translations(
            self.hass, self.hass.config.language, "entity", integrations=[DOMAIN]
        )

        schema = {}
        controller = ModbusController(
            self.hass,
            config["host"],
            config["port"],
            device_id=config.get("device_id", 2),
        )

        if not await controller.async_check_connection():
            await controller.async_close()
            return self.async_abort(reason="cannot_connect")

        current_entities = config.get("entities", {})

        for category in config.get("categories", []):
            if category in ENTITY_DEFINITIONS:
                options = []
                default_values = []

                for entity_id, definition in ENTITY_DEFINITIONS[category].items():
                    platform = definition.get("type", "sensor")
                    if platform == "binary_sensor_from_register":
                        platform = "binary_sensor"
                    if platform == "text":
                        platform = "sensor"
                    translation_key = f"component.froeling_lambdatronic_modbus.entity.{platform}.{entity_id}.name"
                    translated_name = translations.get(translation_key, entity_id)

                    value = await _read_value_helper(
                        controller, definition, entity_id, platform, translations
                    )

                    options.append(
                        {"label": f"{translated_name}: {value}", "value": entity_id}
                    )

                    if (
                        category in current_entities
                        and entity_id in current_entities.get(category, [])
                    ):
                        default_values.append(entity_id)

                schema[vol.Required(category, default=default_values)] = (
                    selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=options,
                            multiple=True,
                            mode=selector.SelectSelectorMode.LIST,
                        )
                    )
                )

        await controller.async_close()

        return self.async_show_form(step_id="init", data_schema=vol.Schema(schema))
