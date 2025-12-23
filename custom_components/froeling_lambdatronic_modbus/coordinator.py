"""DataUpdateCoordinator for the Fröling Lambdatronic Modbus integration."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN
from .entity_definitions import (
    ANLAGENZUSTAND_MAPPING,
    ENTITY_DEFINITIONS,
    KESSEL_FEHLER_MAPPING,
    KESSELZUSTAND_MAPPING,
)
from .modbus_controller import ModbusController

_LOGGER = logging.getLogger(__name__)

MAPPINGS = {
    "ANLAGENZUSTAND_MAPPING": ANLAGENZUSTAND_MAPPING,
    "KESSELZUSTAND_MAPPING": KESSELZUSTAND_MAPPING,
    "KESSEL_FEHLER_MAPPING": KESSEL_FEHLER_MAPPING,
}


class FroelingDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """FroelingDataUpdateCoordinator."""

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

        self._read_blocks = self._group_registers()

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=config.get("update_interval", 60)),
            config_entry=config_entry,
        )

    def _get_active_entity_definitions(self) -> dict[str, Any]:
        """Get definitions for only the enabled entities."""
        active_definitions = {}
        for category, entities in self._enabled_entities.items():
            if category in ENTITY_DEFINITIONS:
                for entity_id in entities:
                    if entity_id in ENTITY_DEFINITIONS[category]:
                        definition = ENTITY_DEFINITIONS[category][entity_id]
                        active_definitions[entity_id] = definition
        return active_definitions

    def _group_registers(
        self, max_gap: int = 5, block_size_limit: int = 122
    ) -> list[tuple[str, int, int, list[str]]]:
        """Group registers into blocks for efficient reading."""
        registers_by_type: dict[str, list[tuple[int, str]]] = {
            "input": [],
            "holding": [],
            "coil": [],
        }

        for entity_id, definition in self._entity_definitions.items():
            address = definition.get("register")
            reg_type = None

            if "coil" in definition:
                reg_type = "coil"
                address = definition["coil"]
            elif address is not None:
                entity_type = definition.get("type")

                if (
                    entity_type in ("number", "select")
                    or (address >= 40001 and address < 50000)
                    or definition.get("register_type") == "holding"
                ):
                    reg_type = "holding"
                else:
                    reg_type = "input"

            if reg_type and address is not None:
                registers_by_type[reg_type].append((address, entity_id))

        blocks = []
        for reg_type, registers in registers_by_type.items():
            if not registers:
                continue

            registers.sort(key=lambda x: x[0])

            current_block_start = -1
            current_block_entities: list[str] = []
            last_addr_in_block = -1

            for i, (addr, entity_id) in enumerate(registers):

                if current_block_start == -1:
                    current_block_start = addr
                    last_addr_in_block = addr
                    current_block_entities = [entity_id]
                else:
                    is_gap_too_big = (addr - last_addr_in_block) > max_gap
                    is_block_too_big = (
                        addr - current_block_start + 1
                    ) >= block_size_limit

                    if is_gap_too_big or is_block_too_big:
                        count = (last_addr_in_block - current_block_start) + 1
                        blocks.append(
                            (
                                reg_type,
                                current_block_start,
                                count,
                                current_block_entities,
                            )
                        )

                        current_block_start = addr
                        current_block_entities = [entity_id]
                    else:

                        current_block_entities.append(entity_id)

                    last_addr_in_block = addr

                if i == len(registers) - 1:
                    count = (last_addr_in_block - current_block_start) + 1
                    blocks.append(
                        (reg_type, current_block_start, count, current_block_entities)
                    )
        return blocks

    async def async_refresh_entity(self, entity_id: str) -> None:
        """Fetch data for a single entity and update state."""
        definition = self._entity_definitions.get(entity_id)
        if not definition:
            return

        address = definition.get("register")
        coil_address = definition.get("coil")

        value = None
        read_success = False

        if coil_address is not None:
            result = await self.controller.async_read_coils(coil_address, 1)
            if result and not result.isError():
                value = result.bits[0]
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

            if result and not result.isError():
                raw_value = result.registers[0]
                value = self._process_raw_value(raw_value, definition)
                read_success = True

        if read_success:
            if self.data is None:
                self.data = {}
            self.data[entity_id] = value
            self.async_update_listeners()
        else:
            _LOGGER.debug("Failed to refresh entity %s", entity_id)

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the device and process it."""
        if not await self.controller.async_check_connection():
            raise UpdateFailed("Could not connect to Modbus device")

        data = {}

        try:
            for block_type, start_addr, count, entities_in_block in self._read_blocks:
                # result = None
                read_success = False

                if block_type == "input":
                    result = await self.controller.async_read_input_registers(
                        start_addr - 30001, count
                    )
                elif block_type == "holding":
                    result = await self.controller.async_read_holding_registers(
                        start_addr - 40001, count
                    )
                elif block_type == "coil":
                    result = await self.controller.async_read_coils(start_addr, count)

                if result and not result.isError():
                    read_success = True

                if not read_success:
                    _LOGGER.debug(
                        "Failed to read %s block at address %s", block_type, start_addr
                    )
                    for entity_id in entities_in_block:
                        data[entity_id] = None
                    continue

                for entity_id in entities_in_block:
                    definition = self._entity_definitions[entity_id]
                    reg_addr = definition.get("register", definition.get("coil"))

                    offset = reg_addr - start_addr

                    if block_type == "coil":
                        if offset < len(result.bits):
                            data[entity_id] = result.bits[offset]
                        else:
                            data[entity_id] = None
                        continue

                    if offset < len(result.registers):
                        raw_value = result.registers[offset]
                        processed_value = self._process_raw_value(raw_value, definition)
                        data[entity_id] = processed_value
                    else:
                        data[entity_id] = None

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

        except Exception as e:
            raise UpdateFailed(f"Error communicating with device: {e}") from e

        return data

    def _process_raw_value(self, raw_value: int, definition: dict[str, Any]) -> Any:
        """Process a raw register value into a scaled and typed sensor value."""
        entity_type = definition.get("type")

        if entity_type == "select":
            return raw_value

        if entity_type == "text":
            mapping_name = definition.get("mapping")
            if mapping_name and mapping_name in MAPPINGS:
                return MAPPINGS[mapping_name].get(raw_value, f"Unknown ({raw_value})")
            return f"Unknown ({raw_value})"

        reg_type = definition.get("register_type", "input")
        if reg_type in ("input", "holding") and raw_value > 32767:
            raw_value -= 65536

        scaling_factor = definition.get("scaling", 1)
        if scaling_factor == 0:
            return None

        scaled_value = raw_value / scaling_factor

        decimal_places = definition.get("decimals", 0)
        if decimal_places == 0:
            return int(round(scaled_value))

        return round(scaled_value, decimal_places)
