"""Modbus Controller (async) using AsyncModbusTcpClient."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from typing import Any

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ConnectionException, ModbusIOException

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class ModbusController:
    """Async Modbus Controller using AsyncModbusTcpClient."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        port: int,
        device_id: int = 2,
        timeout: int = 10,
        retries: int = 1,
        reconnect_delay: float = 30,
    ):
        """Init."""

        self.hass = hass
        self.host = host
        self.port = port
        self.device_id = device_id
        self.timeout = timeout
        self.retries = retries
        self.reconnect_delay = reconnect_delay
        self.last_fail_time = 0

        self._lock = asyncio.Lock()
        self._client: AsyncModbusTcpClient | None = None

    async def _ensure_client_connected(self) -> bool:
        """Ensure the async client is connected."""

        if self._client is None:
            if time.monotonic() < self.last_fail_time + self.reconnect_delay:
                return False
            self._client = AsyncModbusTcpClient(
                self.host,
                port=self.port,
                retries=self.retries,
                timeout=self.timeout,
                reconnect_delay=self.reconnect_delay,
            )

        try:
            if not self._client.connected:
                connected = await self._client.connect()

                if not connected:
                    self._client.close()
                    self._client = None
                    self.last_fail_time = time.monotonic()
                    return False
        except (TimeoutError, ModbusIOException, ConnectionException, OSError) as exc:
            _LOGGER.debug(
                "Exception on Modbus async connect to %s:%s - %s",
                self.host,
                self.port,
                exc,
            )
            if self._client:
                self._client.close()
            self._client = None
            self.last_fail_time = time.monotonic()
            return False

        return self._client is not None and self._client.connected

    async def async_read_input_registers(
        self, address: int, count: int = 1, device_id: int | None = None
    ) -> Any:
        """Read input registers (async)."""

        if device_id is None:
            device_id = self.device_id

        async with self._lock:
            if not await self._ensure_client_connected():
                return None
            assert self._client is not None
            try:
                return await self._client.read_input_registers(
                    address=address, count=count, device_id=device_id
                )
            except (ModbusIOException, ConnectionException) as exc:
                _LOGGER.debug("Exception reading input registers: %s", exc)
                with contextlib.suppress(Exception):
                    if self._client:
                        self._client.close()
                self._client = None
                return None

    async def async_read_holding_registers(
        self, address: int, count: int = 1, device_id: int | None = None
    ) -> Any:
        """Read holding registers (async)."""

        if device_id is None:
            device_id = self.device_id

        async with self._lock:
            if not await self._ensure_client_connected():
                return None
            assert self._client is not None
            try:
                return await self._client.read_holding_registers(
                    address=address, count=count, device_id=device_id
                )
            except (ModbusIOException, ConnectionException) as exc:
                _LOGGER.debug("Exception reading holding registers: %s", exc)
                with contextlib.suppress(Exception):
                    if self._client:
                        self._client.close()
                self._client = None
                return None

    async def async_read_coils(
        self, address: int, count: int = 1, device_id: int | None = None
    ) -> Any:
        """Read coils (async)."""

        if device_id is None:
            device_id = self.device_id

        async with self._lock:
            if not await self._ensure_client_connected():
                return None
            assert self._client is not None
            try:
                return await self._client.read_coils(
                    address=address, count=count, device_id=device_id
                )
            except (ModbusIOException, ConnectionException) as exc:
                _LOGGER.debug("Exception reading coils: %s", exc)
                with contextlib.suppress(Exception):
                    if self._client:
                        self._client.close()
                self._client = None
                return None

    async def async_write_register(
        self, address: int, value: int, device_id: int | None = None
    ) -> bool:
        """Write single register (async)."""

        if device_id is None:
            device_id = self.device_id

        async with self._lock:
            if not await self._ensure_client_connected():
                return False
            assert self._client is not None
            try:
                await self._client.write_register(address, value, device_id=device_id)
            except (ModbusIOException, ConnectionException) as exc:
                _LOGGER.debug("Exception writing register: %s", exc)
                with contextlib.suppress(Exception):
                    if self._client:
                        self._client.close()
                self._client = None
                return False
            else:
                return True

    async def async_close(self) -> None:
        """Close async client connection."""

        async with self._lock:
            if self._client:
                with contextlib.suppress(Exception):
                    self._client.close()
                self._client = None
