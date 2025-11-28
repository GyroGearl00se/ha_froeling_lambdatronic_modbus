from homeassistant.components.binary_sensor import BinarySensorEntity
import logging
from datetime import timedelta
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.translation import async_get_translations
from .const import DOMAIN
from .modbus_controller import ModbusController

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    ent = hass.data[DOMAIN][config_entry.entry_id]
    data = ent["config"]
    controller: ModbusController = ent["controller"]
    translations = await async_get_translations(hass, hass.config.language, "entity")

    def create_binary_sensors():
        binary_sensors = []
        if data.get('hk01', False):
            binary_sensors.extend([
                FroelingBinarySensor(hass, translations, data, controller, "hk1_Pumpe_an_aus", 1030)
            ])
        if data.get('hk02', False):
            binary_sensors.extend([
                FroelingBinarySensor(hass, translations, data, controller, "hk2_pumpe_an_aus", 1060)
            ])
        if data.get('puffer01', False):
            binary_sensors.extend([
                FroelingSensor(hass, translations, data, controller, "puffer_1_pufferpumpe_an_aus", 32004),
            ])
        if data.get('zirkulationspumpe', False):
            binary_sensors.extend([
                FroelingSensor(hass, translations, data, controller, "zirkulationspumpe_an_aus", 30711),
            ])
        if data.get('boiler01', False):
            binary_sensors.extend([
                FroelingSensor(hass, translations, data, controller, "boiler_1_pumpe_an_aus", 31633)
            ])
        return binary_sensors

    binary_sensors = create_binary_sensors()
    async_add_entities(binary_sensors)
    update_interval = timedelta(seconds=data.get('update_interval', 60))
    for sensor in binary_sensors:
        async_track_time_interval(hass, sensor.async_update, update_interval)


class FroelingBinarySensor(BinarySensorEntity):
    def __init__(self, hass, translations, data, controller: ModbusController, entity_id, coil_address):
        self._hass = hass
        self._translations = translations
        self._controller = controller
        self._device_name = data['name']
        self._device_id = entity_id
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
        result = await self._controller.async_read_coils(self._coil_address, count=1)
        if result is None:
            _LOGGER.debug("Modbus coil read returned None (connect failure) for coil %s", self._coil_address)
            self._state = None
            return
        try:
            if result.isError():
                _LOGGER.error("Error reading Modbus coil %s", self._coil_address)
                self._state = None
                return
            self._state = result.bits[0]
            _LOGGER.debug("Reading Modbus coil: %s, state: %s", self._coil_address, self._state)
        except Exception as e:
            _LOGGER.debug("Exception processing Modbus coil result: %s", e)


class FroelingSensor(BinarySensorEntity):
    def __init__(self, hass, translations, data, controller: ModbusController, entity_id, register):
        self._hass = hass
        self._translations = translations
        self._controller = controller
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
        result = await self._controller.async_read_input_registers(self._register - 30001, count=1)
        if result is None:
            _LOGGER.debug("Modbus read returned None (connect failure) for register %s", self._register - 30001)
            self._state = None
            return
        try:
            if result.isError():
                _LOGGER.error("Error reading Modbus input register %s", self._register - 30001)
                self._state = None
                return
            raw_value = result.registers[0]
            self._state = raw_value > 0
            _LOGGER.debug("Reading Modbus input register: %s, state: %s", self._register - 30001, self._state)
        except Exception as e:
            _LOGGER.debug("Exception processing Modbus input result: %s", e)
