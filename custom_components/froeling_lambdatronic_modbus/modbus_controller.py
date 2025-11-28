from __future__ import annotations

import logging
import threading
import time
from typing import Any

from pymodbus.client import ModbusTcpClient

_LOGGER = logging.getLogger(__name__)


class ModbusController:
    def __init__(self, hass, host: str, port: int, device_id: int = 2, timeout: int = 10, retries: int = 2, cool_off: int = 30):
        self.hass = hass
        self.host = host
        self.port = port
        self.device_id = device_id
        self.timeout = timeout
        self.retries = retries
        self.cool_off = cool_off

        self._lock = threading.Lock()
        self._client: ModbusTcpClient | None = None
        self._last_failure = 0.0
        self._last_attempt = 0.0

    def _ensure_client_connected(self) -> bool:
        now = time.time()
        rate_limit_seconds = 5
        if self._last_failure and (now - self._last_failure) < self.cool_off:
            if (now - self._last_attempt) < rate_limit_seconds:
                return False
            self._last_attempt = now
        if self._client is None:
            self._client = ModbusTcpClient(self.host, port=self.port, retries=self.retries, timeout=self.timeout)

        try:
            if not self._client.connect():
                _LOGGER.debug("Modbus connect failed to %s:%s", self.host, self.port)
                try:
                    self._client.close()
                except Exception:
                    pass
                self._client = None
                self._last_failure = time.time()
                return False
        except Exception as exc:  # pragma: no cover - defensive
            _LOGGER.debug("Exception on Modbus connect: %s", exc)
            try:
                if self._client:
                    self._client.close()
            except Exception:
                pass
            self._client = None
            self._last_failure = time.time()
            return False

        self._last_failure = 0.0
        return True

    def read_input_registers(self, address: int, count: int = 1, device_id: int | None = None) -> Any:
        with self._lock:
            if device_id is None:
                device_id = self.device_id
            if not self._ensure_client_connected():
                return None
            try:
                return self._client.read_input_registers(address, count=count, device_id=device_id)
            except Exception as exc:
                _LOGGER.debug("Exception reading input registers: %s", exc)
                try:
                    if self._client:
                        self._client.close()
                except Exception:
                    pass
                self._client = None
                self._last_failure = time.time()
                return None

    def read_holding_registers(self, address: int, count: int = 1, device_id: int | None = None) -> Any:
        with self._lock:
            if device_id is None:
                device_id = self.device_id
            if not self._ensure_client_connected():
                return None
            try:
                return self._client.read_holding_registers(address, count=count, device_id=device_id)
            except Exception as exc:
                _LOGGER.debug("Exception reading holding registers: %s", exc)
                try:
                    if self._client:
                        self._client.close()
                except Exception:
                    pass
                self._client = None
                self._last_failure = time.time()
                return None

    def read_coils(self, address: int, count: int = 1, device_id: int | None = None) -> Any:
        with self._lock:
            if device_id is None:
                device_id = self.device_id
            if not self._ensure_client_connected():
                return None
            try:
                return self._client.read_coils(address, count=count, device_id=device_id)
            except Exception as exc:
                _LOGGER.debug("Exception reading coils: %s", exc)
                try:
                    if self._client:
                        self._client.close()
                except Exception:
                    pass
                self._client = None
                self._last_failure = time.time()
                return None

    def write_register(self, address: int, value: int, device_id: int | None = None) -> bool:
        with self._lock:
            if device_id is None:
                device_id = self.device_id
            if not self._ensure_client_connected():
                return False
            try:
                self._client.write_register(address, value, device_id=device_id)
                return True
            except Exception as exc:
                _LOGGER.debug("Exception writing register: %s", exc)
                try:
                    if self._client:
                        self._client.close()
                except Exception:
                    pass
                self._client = None
                self._last_failure = time.time()
                return False

    def close(self) -> None:
        with self._lock:
            if self._client:
                try:
                    self._client.close()
                except Exception:
                    pass
                self._client = None

    # --- Async wrappers ---
    async def async_read_input_registers(self, address: int, count: int = 1, device_id: int | None = None) -> Any:
        return await self.hass.async_add_executor_job(self.read_input_registers, address, count, device_id)

    async def async_read_holding_registers(self, address: int, count: int = 1, device_id: int | None = None) -> Any:
        return await self.hass.async_add_executor_job(self.read_holding_registers, address, count, device_id)

    async def async_read_coils(self, address: int, count: int = 1, device_id: int | None = None) -> Any:
        return await self.hass.async_add_executor_job(self.read_coils, address, count, device_id)

    async def async_write_register(self, address: int, value: int, device_id: int | None = None) -> bool:
        return await self.hass.async_add_executor_job(self.write_register, address, value, device_id)

    async def async_close(self) -> None:
        return await self.hass.async_add_executor_job(self.close)
