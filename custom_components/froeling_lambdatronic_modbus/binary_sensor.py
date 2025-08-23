from homeassistant.components.binary_sensor import BinarySensorEntity
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

    def create_binary_sensors():
        binary_sensors = []
        if data.get('hk01', False):
            binary_sensors.extend([
                FroelingBinarySensor(hass, translations, data, "hk1_Pumpe_an_aus", 1030)
            ])
        if data.get('hk02', False):
            binary_sensors.extend([
                FroelingBinarySensor(hass, translations, data, "hk2_pumpe_an_aus", 1060)
            ])
        if data.get('puffer01', False):
            binary_sensors.extend([
                FroelingSensor(hass, translations, data, "puffer_1_pufferpumpe_an_aus", 32004),
            ])
        if data.get('zirkulationspumpe', False):
            binary_sensors.extend([
                FroelingSensor(hass, translations, data, "zirkulationspumpe_an_aus", 30711),
            ])
        if data.get('boiler01', False):
            binary_sensors.extend([
                FroelingSensor(hass, translations, data, "boiler_1_pumpe_an_aus", 31633)
            ])
        return binary_sensors

    # Add initial binary sensors
    binary_sensors = create_binary_sensors()
    async_add_entities(binary_sensors)
    update_interval = timedelta(seconds=data.get('update_interval', 60))
    for sensor in binary_sensors:
        async_track_time_interval(hass, sensor.async_update, update_interval)

class FroelingBinarySensor(BinarySensorEntity):
    def __init__(self, hass, translations, data, entity_id, coil_address):
        self._hass = hass
        self._translations = translations
        self._host = data['host']
        self._port = data['port']
        self._device_name = data['name']
        self._entity_id = entity_id
        self._coil_address = coil_address
        self._state = None

    @property
    def unique_id(self):
        return f"{self._device_name}_{self._entity_id}"

    @property
    def name(self):
        translated_name = self._translations.get(f"component.froeling_lambdatronic_modbus.entity.binary_sensor.{self._entity_id}.name", self._entity_id)
        return f"{self._device_name} {translated_name}"

    @property
    def is_on(self):
        return self._state

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._device_name)},
            "name": self._device_name,
            "manufacturer": "Froeling",
            "model": "Lambdatronic Modbus",
            "sw_version": "1.0",
        }

    async def async_update(self, _=None):
        client = ModbusTcpClient(self._host, port=self._port)
        if client.connect():
            try:
                result = client.read_coils(self._coil_address, count=1, slave=2)
                if result.isError():
                    _LOGGER.error("Error reading Modbus coil %s", self._coil_address)
                    self._state = None
                else:
                    self._state = result.bits[0]
                    _LOGGER.debug("Reading Modbus coil: %s, state: %s", self._coil_address, self._state)
            except Exception as e:
                _LOGGER.error("Exception during Modbus communication: %s", e)
            finally:
                client.close()

class FroelingSensor(BinarySensorEntity):
    def __init__(self, hass, translations, data, entity_id, register):
        self._hass = hass
        self._translations = translations
        self._host = data['host']
        self._port = data['port']
        self._device_name = data['name']
        self._entity_id = entity_id
        self._register = register
        self._state = None

    @property
    def unique_id(self):
        return f"{self._device_name}_{self._entity_id}"

    @property
    def name(self):
        translated_name = self._translations.get(f"component.froeling_lambdatronic_modbus.entity.binary_sensor.{self._entity_id}.name", self._entity_id)
        return f"{self._device_name} {translated_name}"

    @property
    def is_on(self):
        return self._state
    
    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._device_name)},
            "name": self._device_name,
            "manufacturer": "Froeling",
            "model": "Lambdatronic Modbus",
            "sw_version": "1.0",
        }

    async def async_update(self, _=None):
        client = ModbusTcpClient(self._host, port=self._port, retries=2, timeout=15)
        if client.connect():
            try:
                result = client.read_input_registers(self._register - 30001, count=1, slave=2)
                if result.isError():
                    _LOGGER.error("Error reading Modbus input register %s", self._register - 30001)
                    self._state = None
                else:
                    raw_value = result.registers[0]
                    self._state = raw_value > 0
                    _LOGGER.debug("Reading Modbus input register: %s, state: %s", self._register - 30001, self._state)
            except Exception as e:
                _LOGGER.error("Exception during Modbus communication: %s", e)
            finally:
                client.close()