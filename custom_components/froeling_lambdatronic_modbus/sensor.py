from homeassistant.components.sensor import SensorEntity
from pymodbus.client.sync import ModbusTcpClient
import logging
from datetime import timedelta
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.translation import async_get_translations
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    data = config_entry.data

    translations = await async_get_translations(hass, hass.config.language, "entity")
    def create_text_sensors():
        text_sensors = []
        text_sensors.extend([
            FroelingTextSensor(hass, translations, data, "Anlagenzustand", 34001, ANLAGENZUSTAND_MAPPING),
            FroelingTextSensor(hass, translations, data, "Kesselzustand", 34002, KESSELZUSTAND_MAPPING)
        ])
        return text_sensors
    
    def create_sensors():
        sensors = []
        sensors.extend([
            FroelingSensor(hass, translations, data, "Aussentemperatur", 31001, "°C", 2, 0, device_class="temperature"),
        ])
        if data.get('kessel', False):
            sensors.extend([
                FroelingSensor(hass, translations, data, "Kesseltemperatur", 30001, "°C", 2, 0, device_class="temperature"),
                FroelingSensor(hass, translations, data, "Abgastemperatur", 30002, "°C", 1, 0, device_class="temperature"),
                FroelingSensor(hass, translations, data, "Verbleibende_Heizstunden_bis_zur_Asche_entleeren_Warnung", 30087, "h", 1, 0, device_class="none"),
                FroelingSensor(hass, translations, data, "Saugzug_Ansteuerung", 30013, "%", 1, 0, device_class="none"),
                FroelingSensor(hass, translations, data, "Saugzugdrehzahl", 30007, "Upm", 1, 0, device_class="none"),
                FroelingSensor(hass, translations, data, "Sauerstoffregler", 30017, "%", 1, 0, device_class="none"),
                FroelingSensor(hass, translations, data, "Restsauerstoffgehalt", 30004, "%", 10, 1, device_class="none"),
                FroelingSensor(hass, translations, data, "Ruecklauffuehler", 30010, "°C", 2, 0, device_class="temperature"),
                FroelingSensor(hass, translations, data, "Primaerluft", 30012, "%", 1, 0, device_class="none"),
                FroelingSensor(hass, translations, data, "Sekundaerluft", 30014, "%", 1, 0, device_class="none"),
                FroelingSensor(hass, translations, data, "Betriebsstunden", 30021, "h", 1, 0, device_class="none"),
                FroelingSensor(hass, translations, data, "Stunden_seit_letzter_Wartung", 30056, "h", 1, 0, device_class="none"),
                FroelingSensor(hass, translations, data, "Betriebsstunden_in_der_Feuererhaltung", 30025, "h", 1, 0, device_class="none")
            ])
        if data.get('hk01', False):
            sensors.extend([
                FroelingSensor(hass, translations, data, "HK01_Vorlauf_Isttemperatur", 31031, "°C", 2, 0, device_class="temperature"),
                FroelingSensor(hass, translations, data, "HK01_Vorlauf_Solltemperatur", 31032, "°C", 2, 0, device_class="temperature")
            ])
        if data.get('hk02', False):
            sensors.extend([
                FroelingSensor(hass, translations, data, "HK02_Vorlauf_Isttemperatur", 31061, "°C", 2, 0, device_class="temperature"),
                FroelingSensor(hass, translations, data, "HK02_Vorlauf_Solltemperatur", 31062, "°C", 2, 0, device_class="temperature"),
            ])
        if data.get('puffer01', False):
            sensors.extend([
                FroelingSensor(hass, translations, data, "Puffer_1_Temperatur_oben", 32001, "°C", 2, 0, device_class="temperature"),
                FroelingSensor(hass, translations, data, "Puffer_1_Temperatur_mitte", 32002, "°C", 2, 0, device_class="temperature"),
                FroelingSensor(hass, translations, data, "Puffer_1_Temperatur_unten", 32003, "°C", 2, 0, device_class="temperature"),
                FroelingSensor(hass, translations, data, "Puffer_1_Pufferpumpen_Ansteuerung", 32004, "%", 1, 0, device_class="none"),
                FroelingSensor(hass, translations, data, "Puffer_1_Ladezustand", 32007, "%", 1, 0, device_class="none")
            ])
        if data.get('boiler01', False):
            sensors.extend([
                FroelingSensor(hass, translations, data, "Boiler_1_Temperatur_oben", 31631, "°C", 2, 0, device_class="temperature"),
                FroelingSensor(hass, translations, data, "Boiler_1_Pumpe_Ansteuerung", 31633, "%", 1, 0, device_class="none")
            ])
        if data.get('austragung', False):
            sensors.extend([
                FroelingSensor(hass, translations, data, "Fuellstand_im_Pelletsbehaelter", 30022, "%", 207, 1, device_class="none"),
                FroelingSensor(hass, translations, data, "Resetierbarer_kg_Zaehler", 30082, "kg", 1, 0, device_class="weight"),
                FroelingSensor(hass, translations, data, "Resetierbarer_t_Zaehler", 30083, "t", 1, 0, device_class="weight"),
                FroelingSensor(hass, translations, data, "Pelletverbrauch_Gesamt", 30084, "t", 10, 0, device_class="weight"),
            ])
        if data.get('zirkulationspumpe', False):
            sensors.extend([
                FroelingSensor(hass, translations, data, "Ruecklauftemperatur_an_der_Zirkulations_Leitung", 30712, "°C", 2, 0, device_class="temperature"),
                FroelingSensor(hass, translations, data, "Stoemungsschalter_an_der_Brauchwasser_Leitung", 30601, "", 2, 0, device_class="none"),
                FroelingSensor(hass, translations, data, "Drehzahl_der_Zirkulations_Pumpe", 30711, "%", 1, 0, device_class="none"),
            ])
        return sensors

    text_sensors = create_text_sensors()
    async_add_entities(text_sensors)

    sensors = create_sensors()
    async_add_entities(sensors)

    update_interval = timedelta(seconds=data.get('update_interval', 60))
    for sensor in sensors:
        async_track_time_interval(hass, sensor.async_update, update_interval)
    for sensor in text_sensors:
        async_track_time_interval(hass, sensor.async_update_text_sensor, update_interval)

class FroelingSensor(SensorEntity):
    def __init__(self, hass, translations, data, entity_id, register, unit, scaling_factor, decimal_places=0, device_class=None):
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
        self._device_class = device_class
        self._state = None

    @property
    def unique_id(self):
        return f"{self._device_name}_{self._entity_id}"

    @property
    def name(self):
        translated_name = self._translations.get(f"component.froeling_lambdatronic_modbus.entity.sensor.{self._entity_id}.name", self._entity_id)
        return f"{self._device_name} {translated_name}"

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return self._unit

    @property
    def device_class(self):
        return self._device_class

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
                result = client.read_input_registers(self._register - 30001, 1, unit=2)
                if result.isError():
                    _LOGGER.error("Error reading Modbus input register %s", self._register - 30001)
                    self._state = None
                else:
                    raw_value = result.registers[0]
                    if raw_value > 32767:
                        raw_value -= 65536
                    scaled_value = raw_value / self._scaling_factor
                    if self._decimal_places == 0:
                        self._state = int(scaled_value)  # Convert to integer if decimal_places is 0
                    else:
                        self._state = round(scaled_value, self._decimal_places)
                    _LOGGER.debug("Reading Modbus input register: %s, state: %s", self._register - 30001, self._state)
            except Exception as e:
                _LOGGER.error("Exception during Modbus communication: %s", e)
            finally:
                client.close()

ANLAGENZUSTAND_MAPPING = {
    0: "Dauerlast",
    1: "Brauchwasser",
    2: "Automatik",
    3: "Scheitholzbetr",
    4: "Reinigen",
    5: "Ausgeschaltet",
    6: "Extraheizen",
    7: "Kaminkehrer",
    8: "Reinigen"
}

KESSELZUSTAND_MAPPING = {
    0: "STÖRUNG",
    1: "Kessel Aus",
    2: "Anheizen",
    3: "Heizen",
    4: "Feuererhaltung",
    5: "Feuer Aus",
    6: "Tür offen",
    7: "Vorbereitung",
    8: "Vorwärmen",
    9: "Zünden",
    10: "Abstellen Warten",
    11: "Abstellen Warten1",
    12: "Abstellen Einschub1",
    13: "Abstellen Warten2",
    14: "Abstellen Einschub2",
    15: "Abreinigen",
    16: "2h warten",
    17: "Saugen / Heizen",
    18: "Fehlzündung",
    19: "Betriebsbereit",
    20: "Rost schließen",
    21: "Stoker leeren",
    22: "Vorheizen",
    23: "Saugen",
    24: "RSE schließen",
    25: "RSE öffnen",
    26: "Rost kippen",
    27: "Vorwärmen-Zünden",
    28: "Resteinschub",
    29: "Stoker auffüllen",
    30: "Lambdasonde aufheizen",
    31: "Gebläsenachlauf I",
    32: "Gebläsenachlauf II",
    33: "Abgestellt",
    34: "Nachzünden",
    35: "Zünden Warten",
    36: "FB: RSE schließen",
    37: "FB: Kessel belüften",
    38: "FB: Zünden",
    39: "FB: min. Einschub",
    40: "RSE schließen",
    41: "STÖRUNG: STB/NA",
    42: "STÖRUNG: Kipprost",
    43: "STÖRUNG: FR-Überdr.",
    44: "STÖRUNG: Türkont.",
    45: "STÖRUNG: Saugzug",
    46: "STÖRUNG: Umfeld",
    47: "FEHLER: STB/NA",
    48: "FEHLER: Kipprost",
    49: "FEHLER: FR-Überdr.",
    50: "FEHLER: Türkont.",
    51: "FEHLER: Saugzug",
    52: "FEHLER: Umfeld",
    53: "FEHLER: Stoker",
    54: "STÖRUNG: Stoker",
    55: "FB: Stoker leeren",
    56: "Vorbelüften",
    57: "STÖRUNG: Hackgut",
    58: "FEHLER: Hackgut",
    59: "NB: Tür offen",
    60: "NB: Anheizen",
    61: "NB: Heizen",
    62: "FEHLER: STB/NA",
    63: "FEHLER: Allgemein",
    64: "NB: Feuer Aus",
    65: "Selbsttest aktiv",
    66: "Fehlerbeh. 20min",
    67: "FEHLER: Fallschacht",
    68: "STÖRUNG: Fallschacht",
    69: "Reinigen möglich",
    70: "Heizen - Reinigen",
    71: "SH Anheizen",
    72: "SH Heizen",
    73: "SH Heiz/Abstell",
    74: "STÖRUNG sicher",
    75: "AGR Nachlauf",
    76: "AGR reinigen",
    77: "Zündung AUS",
    78: "Filter reinigen",
    79: "Anheizassistent",
    80: "SH Zünden",
    81: "SH Störung",
    82: "Sensorcheck"
}

class FroelingTextSensor(SensorEntity):
    def __init__(self, hass, translations, data, entity_id, register, mapping):
        self._hass = hass
        self._translations = translations
        self._host = data['host']
        self._port = data['port']
        self._device_name = data['name']
        self._entity_id = entity_id
        self._register = register
        self._mapping = mapping
        self._state = None

    @property
    def unique_id(self):
        return f"{self._device_name}_{self._entity_id}"

    @property
    def name(self):
        translated_name = self._translations.get(f"component.froeling_lambdatronic_modbus.entity.sensor.{self._entity_id}.name", self._entity_id)
        return f"{self._device_name} {translated_name}"

    @property
    def state(self):
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

    async def async_update_text_sensor(self, _=None):
        client = ModbusTcpClient(self._host, port=self._port, retries=2, timeout=15)
        if client.connect():
            try:
                result = client.read_input_registers(self._register - 30001, 1, unit=2)
                if result.isError():
                    _LOGGER.error("Error reading Modbus input register %s", self._register - 30001)
                    self._state = None
                else:
                    raw_value = result.registers[0]
                    self._state = self._mapping.get(raw_value, "Unknown")
                    _LOGGER.debug("Reading Modbus input register: %s, state: %s", self._register - 30001, self._state)
            except Exception as e:
                _LOGGER.error("Exception during Modbus communication: %s", e)
            finally:
                client.close()

