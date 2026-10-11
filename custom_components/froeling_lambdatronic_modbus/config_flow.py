"""Fröling Lambdatronic Modbus Config Flow."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from modbus_connection import (
    ModbusError,
    ModbusExceptionError,
    ModbusTcpParams,
    ModbusTimeoutError,
)

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.modbus import async_get_temporary_unit
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import selector
from homeassistant.helpers.translation import async_get_translations

from .const import DOMAIN
from .entity_definitions import ENTITY_DEFINITIONS
from .modbus_controller import ModbusController

_LOGGER = logging.getLogger(__name__)


@asynccontextmanager
async def _async_temporary_controller(
    hass: HomeAssistant, config: dict[str, Any]
) -> AsyncIterator[ModbusController]:
    """Hold a temporary shared Modbus unit while a config flow uses it."""
    async with async_get_temporary_unit(
        hass,
        ModbusTcpParams(host=config["host"], port=config["port"]),
        config.get("device_id", 2),
    ) as unit:
        unit.require_timeout(config.get("timeout", 10))
        yield ModbusController(unit)


async def _async_probe_device(hass: HomeAssistant, config: dict[str, Any]) -> str | None:
    """Check that the configured endpoint responds to the selected device ID."""
    try:
        async with _async_temporary_controller(hass, config) as controller:
            try:
                await controller.async_read_input_registers(0, count=1)
            except ModbusExceptionError:
                # A Modbus exception is still a response from the device.
                pass
    except ModbusTimeoutError:
        return "invalid_device_id"
    except (ModbusError, HomeAssistantError) as exc:
        _LOGGER.debug("Could not probe Modbus device: %s", exc)
        return "cannot_connect"
    return None


async def _read_value_helper(
    controller: ModbusController,
    definition: dict[str, Any],
    entity_id: str,
    platform: str,
    translations: dict,
) -> Any:
    """Read a value from the controller for preview purposes."""
    try:
        if "derived_from" in definition:
            total = 0
            for source_id, multiplier in definition["derived_from"].items():
                source_definition = next(
                    (
                        entities[source_id]
                        for entities in ENTITY_DEFINITIONS.values()
                        if source_id in entities
                    ),
                    None,
                )
                if source_definition is None:
                    return "N/A"

                source_value = await _read_value_helper(
                    controller,
                    source_definition,
                    source_id,
                    "sensor",
                    translations,
                )
                if not isinstance(source_value, (int, float)):
                    return source_value
                total += source_value * multiplier
            return total

        if "coil" in definition:
            result = await controller.async_read_coils(definition["coil"], count=1)
            if result:
                return result[0]
        elif "discrete_input" in definition:
            result = await controller.async_read_discrete_inputs(definition["discrete_input"] - 10001, count=1)
            if result:
                return int(result[0])
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

            if result:
                raw_value = result[0]

                if definition.get("type") == "text":
                    if entity_id.startswith("kessel_fehlerpuffer_"):
                        state_translation_key = f"component.froeling_lambdatronic_modbus.entity.sensor.kessel_fehler.state.{raw_value}"
                    else:
                        state_translation_key = f"component.froeling_lambdatronic_modbus.entity.{platform}.{entity_id}.state.{raw_value}"
                    return translations.get(
                        state_translation_key, f"Unknown ({raw_value})"
                    )

                reg_type = definition.get("register_type", "input")
                is_signed = definition.get(
                    "signed",
                    reg_type in ("input", "holding")
                    and definition.get("type") != "select",
                )
                if is_signed and raw_value > 32767:
                    raw_value -= 65536

                scaling = definition.get("scaling", 1)
                decimals = definition.get("decimals", 0)
                scaled_value = raw_value / scaling

                if decimals == 0:
                    return int(scaled_value)
                return round(scaled_value, decimals)
    except ModbusError as e:
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
            error = await _async_probe_device(self.hass, user_input)
            if error is None:
                self.config.update(user_input)
                return await self.async_step_entities()
            errors["base"] = error

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
            entry_data = {k: v for k, v in self.config.items() if k != "entities"}
            entry_options = {"entities": user_input}
            return self.async_create_entry(
                title=self.config["name"],
                data=entry_data,
                options=entry_options,
            )

        schema = {}
        try:
            async with _async_temporary_controller(self.hass, self.config) as controller:
                translations = await async_get_translations(
                    self.hass,
                    self.hass.config.language,
                    "entity",
                    integrations=[DOMAIN],
                )

                for category in self.config.get("categories", []):
                    if category in ENTITY_DEFINITIONS:
                        options = []
                        for entity_id, definition in ENTITY_DEFINITIONS[
                            category
                        ].items():
                            platform = definition.get("type", "sensor")
                            if platform == "binary_sensor_from_register":
                                platform = "binary_sensor"
                            if platform == "text":
                                platform = "sensor"
                            translation_key = f"component.froeling_lambdatronic_modbus.entity.{platform}.{entity_id}.name"
                            translated_name = translations.get(
                                translation_key, entity_id
                            )

                            value = await _read_value_helper(
                                controller,
                                definition,
                                entity_id,
                                platform,
                                translations,
                            )

                            options.append(
                                {
                                    "label": f"{translated_name}: {value}",
                                    "value": entity_id,
                                }
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
        except HomeAssistantError as exc:
            _LOGGER.debug("Could not acquire temporary Modbus unit: %s", exc)
            return self.async_abort(reason="cannot_connect")

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

    def __init__(self) -> None:
        """Initialize the options flow."""
        self.config: dict[str, Any] = {}

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Handle the initial options step."""
        config = {**self.config_entry.data, **self.config_entry.options}

        if user_input is not None:
            self.config = config
            self.config.update(user_input)

            error = await _async_probe_device(self.hass, self.config)
            if error is not None:
                return self.async_show_form(
                    step_id="init",
                    data_schema=self._build_init_schema(config),
                    errors={"base": "cannot_connect"},
                )

            return await self.async_step_entities()

        return self.async_show_form(
            step_id="init",
            data_schema=self._build_init_schema(config),
        )

    async def async_step_entities(self, user_input: dict[str, Any] | None = None):
        """Handle the entity selection options step."""
        if not self.config:
            self.config = {**self.config_entry.data, **self.config_entry.options}

        if user_input is not None:
            new_options = dict(self.config_entry.options)
            new_options["entities"] = user_input

            new_data = {k: v for k, v in self.config.items() if k != "entities"}
            self.hass.config_entries.async_update_entry(
                self.config_entry, data=new_data
            )
            return self.async_create_entry(title="", data=new_options)

        schema = {}
        current_entities = self.config.get("entities", {})

        try:
            async with _async_temporary_controller(self.hass, self.config) as controller:
                translations = await async_get_translations(
                    self.hass,
                    self.hass.config.language,
                    "entity",
                    integrations=[DOMAIN],
                )
                for category in self.config.get("categories", []):
                    if category in ENTITY_DEFINITIONS:
                        options = []
                        default_values = []

                        for entity_id, definition in ENTITY_DEFINITIONS[
                            category
                        ].items():
                            platform = definition.get("type", "sensor")
                            if platform == "binary_sensor_from_register":
                                platform = "binary_sensor"
                            if platform == "text":
                                platform = "sensor"
                            translation_key = f"component.froeling_lambdatronic_modbus.entity.{platform}.{entity_id}.name"
                            translated_name = translations.get(
                                translation_key, entity_id
                            )

                            value = await _read_value_helper(
                                controller,
                                definition,
                                entity_id,
                                platform,
                                translations,
                            )

                            options.append(
                                {
                                    "label": f"{translated_name}: {value}",
                                    "value": entity_id,
                                }
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
        except HomeAssistantError as exc:
            _LOGGER.debug("Could not acquire temporary Modbus unit: %s", exc)
            return self.async_abort(reason="cannot_connect")

        return self.async_show_form(step_id="entities", data_schema=vol.Schema(schema))

    def _build_init_schema(self, config: dict[str, Any]) -> vol.Schema:
        """Build the initial options schema."""
        return vol.Schema(
            {
                vol.Required("name", default=config.get("name", "Froeling")): str,
                vol.Required("host", default=config.get("host", "")): str,
                vol.Required("port", default=config.get("port", 502)): int,
                vol.Required("device_id", default=config.get("device_id", 2)): int,
                vol.Required("update_interval", default=config.get("update_interval", 60)): int,
                vol.Required(
                    "categories",
                    default=config.get("categories", list(ENTITY_DEFINITIONS.keys())),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=list(ENTITY_DEFINITIONS.keys()),
                        multiple=True,
                        mode=selector.SelectSelectorMode.LIST,
                        translation_key="categories",
                    ),
                ),
            }
        )
