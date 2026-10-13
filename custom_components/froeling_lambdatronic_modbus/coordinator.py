"""DataUpdateCoordinator for the Fröling Lambdatronic Modbus integration."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Literal

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.translation import async_get_translations
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from modbus_connection import ModbusError, ModbusExceptionError
from modbus_connection.model import (
    CoilField,
    DiscreteInputField,
    ManualComponent,
    RegisterField,
    coil,
    discrete_input,
    raw_register,
)

from .const import DOMAIN
from .entity_definitions import ENTITY_DEFINITIONS
from .modbus_controller import ModbusController

_LOGGER = logging.getLogger(__name__)


class FroelingDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching data from the Fröling Modbus interface."""

    def __init__(
        self,
        hass: HomeAssistant,
        controller: ModbusController,
        config: dict,
        config_entry: ConfigEntry,
    ):
        """Initialize the data update coordinator."""
        self.controller = controller
        self._enabled_entities = config.get("entities", {})
        self._entity_definitions = self._get_active_entity_definitions()
        self.translations = None

        self._modbus_component = ManualComponent(
            controller.unit, max_gap=5, max_span=122
        )
        self._modbus_fields: dict[
            str,
            tuple[
                RegisterField[int] | CoilField | DiscreteInputField,
                Literal["input", "holding", "coil", "discrete"],
                int,
            ],
        ] = {}
        for entity_id, definition in self._entity_definitions.items():
            self._add_modbus_field(entity_id, definition)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=config.get("update_interval", 60)),
            config_entry=config_entry,
        )
        self.data = {}

    def _get_active_entity_definitions(self) -> dict[str, Any]:
        """Get definitions for only the enabled entities."""
        active_definitions = {
            entity_id: ENTITY_DEFINITIONS[category][entity_id]
            for category, entities in self._enabled_entities.items()
            if category in ENTITY_DEFINITIONS
            for entity_id in entities
            if entity_id in ENTITY_DEFINITIONS[category]
        }
        all_definitions = {
            entity_id: definition
            for entities in ENTITY_DEFINITIONS.values()
            for entity_id, definition in entities.items()
        }
        pending_dependencies = [
            dependency_id
            for definition in active_definitions.values()
            for dependency_id in definition.get("derived_from", {})
        ]

        while pending_dependencies:
            dependency_id = pending_dependencies.pop()
            if dependency_id in active_definitions:
                continue
            dependency = all_definitions.get(dependency_id)
            if dependency is not None:
                active_definitions[dependency_id] = dependency
                pending_dependencies.extend(dependency.get("derived_from", {}))

        return active_definitions

    def _add_modbus_field(self, entity_id: str, definition: dict[str, Any]) -> None:
        """Add a raw field to the pooled Modbus component."""
        if "coil" in definition:
            address = definition["coil"]
            field = coil(address)
            space: Literal["input", "holding", "coil", "discrete"] = "coil"
        elif "discrete_input" in definition:
            address = definition["discrete_input"] - 10001
            field = discrete_input(address)
            space = "discrete"
        elif (register := definition.get("register")) is not None:
            is_holding = (
                definition.get("type") in ("number", "select")
                or 40001 <= register < 50000
                or definition.get("register_type") == "holding"
            )
            offset = 40001 if is_holding else 30001
            address = register - offset
            space = "holding" if is_holding else "input"
            field = raw_register(address)
        else:
            return

        self._modbus_fields[entity_id] = (field, space, address)
        if space in ("input", "holding"):
            self._modbus_component.add(entity_id, field, space=space)
        else:
            self._modbus_component.add(entity_id, field)

    async def _async_read_one_field(self, entity_id: str) -> int | bool | None:
        """Read one field independently after its pooled block has failed."""
        field, space, _ = self._modbus_fields[entity_id]
        component = ManualComponent(self.controller.unit, max_gap=5, max_span=122)
        if space in ("input", "holding"):
            component.add(entity_id, field, space=space)
        else:
            component.add(entity_id, field)

        try:
            values = await component.async_update()
        except ModbusError as exc:
            _LOGGER.debug("Failed to read %s individually: %s", entity_id, exc)
            return None
        return values.get(entity_id)

    async def _async_read_modbus_fields(self) -> dict[str, int | bool | None]:
        """Read pooled fields and isolate values in any failed read block."""
        values: dict[str, int | bool | None] = {}
        removed_fields: set[str] = set()
        _LOGGER.debug(
            "Starting pooled read for %s Modbus fields", len(self._modbus_fields)
        )

        try:
            while True:
                try:
                    await self._modbus_component.async_update()
                except ModbusExceptionError as exc:
                    block = exc.block
                    failed_fields = (
                        [
                            entity_id
                            for entity_id, (
                                _,
                                space,
                                address,
                            ) in self._modbus_fields.items()
                            if entity_id not in removed_fields
                            and space == block.space
                            and block.address <= address < block.address + block.count
                        ]
                        if block is not None
                        else []
                    )

                    if not failed_fields:
                        _LOGGER.debug(
                            "Pooled Modbus read failed without an "
                            "identifiable block: %s",
                            exc,
                        )
                        raise

                    _LOGGER.debug(
                        "Isolating failed %s block at address %s (count %s)",
                        block.space,
                        block.address,
                        block.count,
                    )
                    for entity_id in failed_fields:
                        self._modbus_component.remove(entity_id)
                        removed_fields.add(entity_id)
                        values[entity_id] = await self._async_read_one_field(entity_id)
                except ModbusError as exc:
                    _LOGGER.debug("Pooled Modbus read failed: %s", exc)
                    raise
                else:
                    values.update(self._modbus_component.values)
                    successful_fields = sum(
                        value is not None for value in values.values()
                    )
                    _LOGGER.debug(
                        "Pooled read completed: %s/%s fields returned values",
                        successful_fields,
                        len(self._modbus_fields),
                    )
                    return values
        finally:
            for entity_id in removed_fields:
                field, space, _ = self._modbus_fields[entity_id]
                if space in ("input", "holding"):
                    self._modbus_component.add(entity_id, field, space=space)
                else:
                    self._modbus_component.add(entity_id, field)

    async def async_refresh_entity(self, entity_id: str) -> None:
        """Fetch data for a single entity and update state."""
        definition = self._entity_definitions.get(entity_id)
        if not definition:
            return

        address = definition.get("register")
        coil_address = definition.get("coil")
        discrete_input_address = definition.get("discrete_input")

        value = None
        read_success = False

        try:
            if coil_address is not None:
                result = await self.controller.async_read_coils(coil_address, 1)
                if result:
                    value = result[0]
                    read_success = True
            elif discrete_input_address is not None:
                result = await self.controller.async_read_discrete_inputs(
                    discrete_input_address - 10001, 1
                )
                if result:
                    value = result[0]
                    read_success = True
            elif address is not None:
                entity_type = definition.get("type")
                reg_type = definition.get("register_type")

                is_holding = (
                    entity_type in ("number", "select")
                    or (40001 <= address < 50000)
                    or reg_type == "holding"
                )

                if is_holding:
                    result = await self.controller.async_read_holding_registers(
                        address - 40001, 1
                    )
                else:
                    result = await self.controller.async_read_input_registers(
                        address - 30001, 1
                    )

                if result:
                    value = self._process_raw_value(result[0], definition)
                    read_success = True
        except ModbusError as exc:
            _LOGGER.debug("Failed to refresh entity %s: %s", entity_id, exc)

        if read_success:
            if self.data is None:
                self.data = {}
            self.data[entity_id] = value
            self.async_update_listeners()
        else:
            _LOGGER.debug("Failed to refresh entity %s", entity_id)

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the device and process it."""
        if self.translations is None:
            self.translations = await async_get_translations(
                self.hass, self.hass.config.language, "entity"
            )

        try:
            raw_values = await self._async_read_modbus_fields()
        except ModbusError as exc:
            raise UpdateFailed(f"Error communicating with device: {exc}") from exc
        data = {}
        successful_fields = 0

        for entity_id, (_, space, _) in self._modbus_fields.items():
            raw_value = raw_values.get(entity_id)
            if raw_value is None:
                data[entity_id] = None
                continue

            successful_fields += 1
            definition = self._entity_definitions[entity_id]
            if space in ("coil", "discrete"):
                data[entity_id] = raw_value
            else:
                data[entity_id] = self._process_raw_value(raw_value, definition)

        if self._modbus_fields and not successful_fields:
            _LOGGER.debug("No Modbus fields could be read successfully")
            raise UpdateFailed("Could not read any data from the Modbus device")

        for entity_id, definition in self._entity_definitions.items():
            if definition.get("type") == "binary_sensor_from_register":
                source_register = definition["register"]
                source_value = None
                for other_id, other_def in self._entity_definitions.items():
                    if (
                        other_def.get("register") == source_register
                        and other_id in data
                    ):
                        source_value = data[other_id]
                        break
                if source_value is not None:
                    data[entity_id] = source_value > 0
                else:
                    data[entity_id] = None

        for entity_id, definition in self._entity_definitions.items():
            derived_from = definition.get("derived_from")
            if derived_from is None:
                continue

            if all(data.get(source_id) is not None for source_id in derived_from):
                data[entity_id] = sum(
                    data[source_id] * multiplier
                    for source_id, multiplier in derived_from.items()
                )
            else:
                data[entity_id] = None

        return data

    def _process_raw_value(self, raw_value: int, definition: dict[str, Any]) -> Any:
        """Process a raw register value into a scaled and typed sensor value."""
        entity_type = definition.get("type")

        if entity_type == "select":
            return raw_value

        if entity_type == "text":
            translation_key = definition.get("translation_key")
            if translation_key:
                lookup_key = f"component.{DOMAIN}.entity.sensor.{translation_key}.state.{raw_value}"
                translated = self.translations.get(lookup_key)
                if translated:
                    return translated
            return f"Unknown ({raw_value})"

        reg_type = definition.get("register_type", "input")
        is_signed = definition.get("signed", reg_type in ("input", "holding"))
        if is_signed and raw_value > 32767:
            raw_value -= 65536

        scaling_factor = definition.get("scaling", 1)
        if scaling_factor == 0:
            return None

        scaled_value = raw_value / scaling_factor

        decimal_places = definition.get("decimals", 0)
        if decimal_places == 0:
            return round(scaled_value)

        return round(scaled_value, decimal_places)
