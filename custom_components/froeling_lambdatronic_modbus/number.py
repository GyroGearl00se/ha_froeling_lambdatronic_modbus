from homeassistant.components.number import NumberEntity, NumberMode
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

    def create_numbers():
        numbers = []

        if data.get('kessel', False):
            numbers.extend([
                FroelingNumber(hass, translations, data, "Kessel_Solltemperatur", 40001, "°C", 2, 0, 70, 90),
                FroelingNumber(hass, translations, data, "Bei_welcher_RL_Temperatur_an_der_Zirkulationsleitung_soll_die_Pumpe_ausschalten", 40601, "°C", 2, 0, 20, 120)
            ])
        if data.get('hk01', False):
            numbers.extend([
                FroelingNumber(hass, translations, data, "HK1_Vorlauf_Temperatur_10C_Aussentemperatur", 41032, "°C", 2, 0, 10, 110),
                FroelingNumber(hass, translations, data, "HK1_Vorlauf_Temperatur_minus_10C_Aussentemperatur", 41033, "°C", 2, 0, 10, 110),
                FroelingNumber(hass, translations, data, "HK1_Heizkreispumpe_ausschalten_wenn_Vorlauf_Soll_kleiner_ist_als", 41040, "°C", 2, 0, 10, 30),
                FroelingNumber(hass, translations, data, "HK1_Absenkung_der_Vorlauftemperatur_im_Absenkbetrieb", 41034, "°C", 2, 0, 0, 70),
                FroelingNumber(hass, translations, data, "HK1_Aussentemperatur_unter_der_die_Heizkreispumpe_im_Heizbetrieb_einschaltet", 41037, "°C", 2, 0, -20, 50),
                FroelingNumber(hass, translations, data, "HK1_Aussentemperatur_unter_der_die_Heizkreispumpe_im_Absenkbetrieb_einschaltet", 41038, "°C", 2, 0, -20, 50),
                FroelingNumber(hass, translations, data, "HK1_Frostschutztemperatur", 41039, "°C", 2, 0, 10, 20),
                FroelingNumber(hass, translations, data, "HK1_Temp_am_Puffer_oben_ab_der_der_Ueberhitzungsschutz_aktiv_wird", 41048, "°C", 1, 0, 60, 120)
            ])
        if data.get('hk02', False):
            numbers.extend([
                FroelingNumber(hass, translations, data, "HK2_Vorlauf_Temperatur_10C_Aussentemperatur", 41062, "°C", 2, 0, 10, 110),
                FroelingNumber(hass, translations, data, "HK2_Vorlauf_Temperatur_minus_10C_Aussentemperatur", 41063, "°C", 2, 0, 10, 110),
                FroelingNumber(hass, translations, data, "HK2_Heizkreispumpe_ausschalten_wenn_Vorlauf_Soll_kleiner_ist_als", 41070, "°C", 2, 0, 10, 30),
                FroelingNumber(hass, translations, data, "HK2_Absenkung_der_Vorlauftemperatur_im_Absenkbetrieb", 41064, "°C", 2, 0, 0, 70),
                FroelingNumber(hass, translations, data, "HK2_Aussentemperatur_unter_der_die_Heizkreispumpe_im_Heizbetrieb_einschaltet", 41067, "°C", 2, 0, -20, 50),
                FroelingNumber(hass, translations, data, "HK2_Aussentemperatur_unter_der_die_Heizkreispumpe_im_Absenkbetrieb_einschaltet", 41068, "°C", 2, 0, -20, 50),
                FroelingNumber(hass, translations, data, "HK2_Frostschutztemperatur", 41069, "°C", 2, 0, -10, 20),
                FroelingNumber(hass, translations, data, "HK2_Temp_am_Puffer_oben_ab_der_der_Ueberhitzungsschutz_aktiv_wird", 41079, "°C", 1, 0, 60, 120)
            ])
        if data.get('boiler01', False):
            numbers.extend([
                FroelingNumber(hass, translations, data, "Boiler_1_Gewuenschte_Boilertemperatur", 41632, "°C", 2, 0, 10, 100),
                FroelingNumber(hass, translations, data, "Boiler_1_Nachladen_wenn_Boilertemperatur_unter", 41633, "°C", 2, 0, 1, 90)
            ])
        if data.get('austragung', False):
            numbers.extend([
                FroelingNumber(hass, translations, data, "Pelletlager_Restbestand", 40320, "t", 10, 1, 0, 100)
            ])
        if data.get('zweitkessel', False):
            numbers.extend([
                FroelingNumber(hass, translations, data, "Minimaltemperatur_Zweitkessel", 40507, "°C", 2, 0, 20, 95),
                FroelingNumber(hass, translations, data, "Temperaturdifferenz_Zweitkessel_Puffer", 40508, "°C", 2, 0, 0, 50),
                FroelingNumber(hass, translations, data, "Minimale_Laufzeit_Zweitkessel", 40505, "min", 60, 0, 0, 500),
                FroelingNumber(hass, translations, data, "Einschaltverzoegerung_Zweitkessel", 40502, "min", 60, 0, 0, 500),
            ])

        return numbers

    numbers = create_numbers()
    async_add_entities(numbers)
    update_interval = timedelta(seconds=data.get('update_interval', 60))
    for number in numbers:
        async_track_time_interval(hass, number.async_update, update_interval)

class FroelingNumber(NumberEntity):
    def __init__(self, hass, translations, data, entity_id, register, unit, scaling_factor, decimal_places=0, min_value=0, max_value=0, mode: NumberMode | None = None, step: float | None = None):
        self._hass = hass
        self._translations = translations
        self._host = data['host']
        self._port = data['port']
        self._device_name = data['name']
        self._entity_id = entity_id
        self._register = register
        self._unit = unit
        self._scaling_factor = scaling_factor
        self._decimal_places = decimal_places
        self._min_value = min_value
        self._max_value = max_value
        self._value = None
        self._mode = mode
        self._native_step_override = step

    @property
    def unique_id(self):
        return f"{self._device_name}_{self._entity_id}"

    @property
    def name(self):
        translated_name = self._translations.get(f"component.froeling_lambdatronic_modbus.entity.number.{self._entity_id}.name", self._entity_id)
        return f"{self._device_name} {translated_name}"

    @property
    def native_value(self):
        return self._value

    @property
    def native_unit_of_measurement(self):
        return self._unit

    @property
    def native_step(self):
        if self._native_step_override is not None:
            return self._native_step_override
        if self._decimal_places and self._decimal_places > 0:
            try:
                return 1 / float(self._scaling_factor)
            except Exception:
                return 1.0
        return 1.0

    @property
    def mode(self) -> NumberMode:
        return self._mode or NumberMode.BOX

    @property
    def suggested_display_precision(self) -> int:
        return int(self._decimal_places or 0)

    @property
    def native_min_value(self):
        return self._min_value

    @property
    def native_max_value(self):
        return self._max_value

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._device_name)},
            "name": self._device_name,
            "manufacturer": "Froeling",
            "model": "Lambdatronic Modbus",
            "sw_version": "1.0",
        }

    async def async_set_native_value(self, value):
        client = ModbusTcpClient(self._host, port=self._port, retries=2, timeout=15)
        if client.connect():
            try:
                scaled_value = int(value * self._scaling_factor)
                client.write_register(self._register - 40001, scaled_value, device_id=2)
                self._value = value
            except Exception as e:
                _LOGGER.error("Exception during Modbus communication: %s", e)
            finally:
                client.close()

    async def async_update(self, _=None):
        client = ModbusTcpClient(self._host, port=self._port, retries=2, timeout=15)
        if client.connect():
            try:
                result = client.read_holding_registers(self._register - 40001, count=1, device_id=2)
                if result.isError():
                    _LOGGER.error("Error reading Modbus holding register %s", self._register - 40001)
                    self._value = None
                else:
                    raw_value = result.registers[0]
                    self._value = round(raw_value / self._scaling_factor, self._decimal_places)
                    _LOGGER.debug("processed Modbus holding register %s: raw_value=%s, _value=%s", self._register - 40001, raw_value, self._value)
            except Exception as e:
                _LOGGER.error("Exception during Modbus communication: %s", e)
            finally:
                client.close()
