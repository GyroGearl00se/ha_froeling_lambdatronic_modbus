from homeassistant.components.select import SelectEntity
from pymodbus.client import ModbusTcpClient
import logging
from datetime import timedelta
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.translation import async_get_translations
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    data = config_entry.data
    translations = await async_get_translations(hass, hass.config.language, "entity")

    def create_selects():
        selects: list[FroelingSelect] = []

        if data.get('hk01', False):
            selects.extend([
                FroelingSelect(hass,translations,data,"HK01_Betriebsart",48047,OPERATINGMODES,min_value=0,max_value=5)
            ])
        if data.get('hk02', False):
            selects.extend([
                FroelingSelect(hass,translations,data,"HK02_Betriebsart",48048,OPERATINGMODES,min_value=0,max_value=5)
            ])
        return selects

    selects = create_selects()
    async_add_entities(selects)
    update_interval = timedelta(seconds=data.get('update_interval', 60))
    for select in selects:
        async_track_time_interval(hass, select.async_update, update_interval)

OPERATINGMODES = [
    "Aus",
    "Automatik",
    "Extraheizen",
    "Absenken",
    "Dauerabsenken",
    "Partybetrieb",
]

class FroelingSelect(SelectEntity):
    def __init__(self, hass, translations, data, entity_id: str, register: int, options: list[str], min_value: int = 0, max_value: int | None = None):
        self._hass = hass
        self._translations = translations
        self._host = data['host']
        self._port = data['port']
        self._device_name = data['name']
        self._entity_id = entity_id
        self._register = register
        self._options = options
        self._min_value = min_value
        self._max_value = max_value if max_value is not None else len(options) - 1
        self._current_index: int | None = None

    @property
    def unique_id(self):
        return f"{self._device_name}_{self._entity_id}"

    @property
    def name(self):
        translated_name = self._translations.get(
            f"component.froeling_lambdatronic_modbus.entity.select.{self._entity_id}.name",
            self._entity_id,
        )
        return f"{self._device_name} {translated_name}"

    @property
    def options(self) -> list[str]:
        return self._options

    @property
    def current_option(self) -> str | None:
        if self._current_index is None:
            return None
        if 0 <= self._current_index < len(self._options):
            return self._options[self._current_index]
        return None

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._device_name)},
            "name": self._device_name,
            "manufacturer": "Froeling",
            "model": "Lambdatronic Modbus",
            "sw_version": "1.0",
        }

    async def async_select_option(self, option: str) -> None:
        if option not in self._options:
            _LOGGER.error("Invalid option selected: %s", option)
            return
        value = self._options.index(option)
        if value < self._min_value or value > self._max_value:
            _LOGGER.error("Selected option index %s is out of allowed range [%s, %s]", value, self._min_value, self._max_value)
            return

        client = ModbusTcpClient(self._host, port=self._port)
        if client.connect():
            try:
                client.write_register(self._register - 40001, value, device_id=2)
                self._current_index = value
            except Exception as e:
                _LOGGER.error("Exception during Modbus communication (write select): %s", e)
            finally:
                client.close()

    async def async_update(self, _=None):
        client = ModbusTcpClient(self._host, port=self._port)
        if client.connect():
            try:
                result = client.read_holding_registers(self._register - 40001, count=1, device_id=2)
                if result.isError():
                    _LOGGER.error("Error reading Modbus holding register %s", self._register - 40001)
                    self._current_index = None
                else:
                    raw_value = result.registers[0]
                    if raw_value < self._min_value or raw_value > self._max_value:
                        _LOGGER.warning(
                            "Read out-of-range value %s from register %s (allowed [%s,%s])",
                            raw_value,
                            self._register - 40001,
                            self._min_value,
                            self._max_value,
                        )
                        return
                    self._current_index = raw_value
                    _LOGGER.debug(
                        "processed Modbus holding register %s: raw_value=%s, current_option=%s",
                        self._register - 40001,
                        raw_value,
                        self.current_option,
                    )
            except Exception as e:
                _LOGGER.error("Exception during Modbus communication (read select): %s", e)
            finally:
                client.close()
