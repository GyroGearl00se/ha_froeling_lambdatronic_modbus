"""Modbus controller backed by a Home Assistant-managed unit."""

from __future__ import annotations

from modbus_connection import ModbusUnit


class ModbusController:
    """Provide the integration's Modbus operations through a shared unit."""

    def __init__(self, unit: ModbusUnit) -> None:
        """Initialize the controller."""
        self._unit = unit

    async def async_read_input_registers(
        self, address: int, count: int = 1
    ) -> list[int]:
        """Read input registers."""
        return await self._unit.read_input_registers(address, count)

    async def async_read_discrete_inputs(
        self, address: int, count: int = 1
    ) -> list[bool]:
        """Read discrete inputs."""
        return await self._unit.read_discrete_inputs(address, count)

    async def async_read_holding_registers(
        self, address: int, count: int = 1
    ) -> list[int]:
        """Read holding registers."""
        return await self._unit.read_holding_registers(address, count)

    async def async_read_coils(self, address: int, count: int = 1) -> list[bool]:
        """Read coils."""
        return await self._unit.read_coils(address, count)

    async def async_write_register(self, address: int, value: int) -> None:
        """Write a single register."""
        await self._unit.write_register(address, value)
