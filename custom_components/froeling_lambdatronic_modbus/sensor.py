from homeassistant.components.sensor import SensorEntity
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
    def create_text_sensors():
        text_sensors = []
        text_sensors.extend([
            FroelingTextSensor(hass, translations, data, "Anlagenzustand", 34001, ANLAGENZUSTAND_MAPPING),
            FroelingTextSensor(hass, translations, data, "Kesselzustand", 34002, KESSELZUSTAND_MAPPING)
        ])
        if data.get('fehlerpuffer', False):
            for i in range(20):
                reg = 33001 + i
                entity_id = f"Kessel_Fehlerpuffer_{i+1}"
                text_sensors.append(
                    FroelingTextSensor(hass, translations, data, entity_id, reg, KESSEL_FEHLER_MAPPING)
                )
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
                FroelingSensor(hass, translations, data, "Saugzug_Ansteuerung", 30014, "%", 1, 0, device_class="none"),
                FroelingSensor(hass, translations, data, "Saugzugdrehzahl", 30007, "Upm", 1, 0, device_class="none"),
                FroelingSensor(hass, translations, data, "Sauerstoffregler", 30017, "%", 1, 0, device_class="none"),
                FroelingSensor(hass, translations, data, "Restsauerstoffgehalt", 30004, "%", 10, 1, device_class="none"),
                FroelingSensor(hass, translations, data, "Ruecklauffuehler", 30010, "°C", 2, 0, device_class="temperature"),
                FroelingSensor(hass, translations, data, "Primaerluft", 30012, "%", 1, 0, device_class="none"),
                FroelingSensor(hass, translations, data, "Sekundaerluft", 30013, "%", 1, 0, device_class="none"),
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
                FroelingSensor(hass, translations, data, "Pelletverbrauch_Gesamt", 30084, "t", 10, 1, device_class="weight"),
            ])
        if data.get('zirkulationspumpe', False):
            sensors.extend([
                FroelingSensor(hass, translations, data, "Ruecklauftemperatur_an_der_Zirkulations_Leitung", 30712, "°C", 2, 0, device_class="temperature"),
                FroelingSensor(hass, translations, data, "Stoemungsschalter_an_der_Brauchwasser_Leitung", 30601, "", 2, 0, device_class="none"),
                FroelingSensor(hass, translations, data, "Drehzahl_der_Zirkulations_Pumpe", 30711, "%", 1, 0, device_class="none"),
            ])
        if data.get('zweitkessel', False):
            sensors.extend([
                FroelingSensor(hass, translations, data, "Temperatur_Zweitkessel", 30501, "°C", 2, 0, device_class="temperature"),
                FroelingSensor(hass, translations, data, "Umschaltventil_Zweitkessel", 30504, "%", 1, 0, device_class="none"),
                FroelingSensor(hass, translations, data, "Zustand_Brennerrelais", 30502, "", 1, 0, device_class="none"),
                FroelingSensor(hass, translations, data, "Betriebsstunden_Zweitkessel", 30503, "h", 1, 0, device_class="none"),
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
                result = client.read_input_registers(self._register - 30001, count=1, device_id=2)
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

KESSEL_FEHLER_MAPPING = {
    0: "STB gefallen oder NOT-AUS betätigt",
    1: "Kesseltemperaturfühler fehlerhaft",
    2: "Primärluftklappe blockiert",
    3: "Sekundärluftklappe blockiert",
    4: "Kessel zieht zu viel Falschluft",
    5: "Kontrolle von Feuerraum- Überdruckwächter durchführen",
    6: "Rückbrandschieber schließt nicht",
    7: "Rückbrandschieber öffnet nicht",
    8: "Rostantrieb defekt",
    9: "Rost Fehler",
    10: "Rostreinigung fehlerhaft",
    11: "Zündversuch ist nicht gelungen",
    12: "Sicherheitszeit abgelaufen Sauerstoffgehalt zu lange zu hoch",
    13: "Sicherheitszeit abgelaufen Abgastemperatur zu lange zu niedrig",
    14: "Kesseltür zu lange offen",
    15: "Stopfsensor für länger als 5min belegt",
    16: "Raumaustragung kontrollieren",
    17: "Lagerraum kontrollieren",
    18: "Rücklauftemperaturfühler fehlerhaft",
    19: "Rücklauftemperatur seit mehr als 30 Minuten zu niedrig",
    20: "Fernversteller Heizkreis 1 fehlerhaft",
    21: "Vorlauftemperaturfühler Heizkreis 1 fehlerhaft",
    22: "Fernversteller Heizkreis 2 fehlerhaft",
    23: "Vorlauftemperaturfühler Heizkreis 2 fehlerhaft",
    24: "Außentemperaturfühler fehlerhaft",
    25: "NOT-AUS Kontakt wurde betätigt",
    26: "Fernversteller Heizkreis 3 fehlerhaft",
    27: "Fernversteller Heizkreis 4 fehlerhaft",
    28: "Fernversteller Heizkreis 5 fehlerhaft",
    29: "Fernversteller Heizkreis 6 fehlerhaft",
    30: "Fernversteller Heizkreis 7 fehlerhaft",
    31: "Fernversteller Heizkreis 8 fehlerhaft",
    32: "Fernversteller Heizkreis 9 fehlerhaft",
    33: "Fernversteller Heizkreis 10 fehlerhaft",
    34: "Fernversteller Heizkreis 11 fehlerhaft",
    35: "Fernversteller Heizkreis 12 fehlerhaft",
    36: "Fernversteller Heizkreis 13 fehlerhaft",
    37: "Fernversteller Heizkreis 14 fehlerhaft",
    38: "Fernversteller Heizkreis 15 fehlerhaft",
    39: "Fernversteller Heizkreis 16 fehlerhaft",
    40: "Fernversteller Heizkreis 17 fehlerhaft",
    41: "Fernversteller Heizkreis 18 fehlerhaft",
    42: "Vorlauftemperaturfühler Heizkreis 3 fehlerhaft",
    43: "Vorlauftemperaturfühler Heizkreis 4 fehlerhaft",
    44: "Vorlauftemperaturfühler Heizkreis 5 fehlerhaft",
    45: "Vorlauftemperaturfühler Heizkreis 6 fehlerhaft",
    46: "Vorlauftemperaturfühler Heizkreis 7 fehlerhaft",
    47: "Vorlauftemperaturfühler Heizkreis 8 fehlerhaft",
    48: "Vorlauftemperaturfühler Heizkreis 9 fehlerhaft",
    49: "Vorlauftemperaturfühler Heizkreis 10 fehlerhaft",
    50: "Vorlauftemperaturfühler Heizkreis 11 fehlerhaft",
    51: "Vorlauftemperaturfühler Heizkreis 12 fehlerhaft",
    52: "Vorlauftemperaturfühler Heizkreis 13 fehlerhaft",
    53: "Vorlauftemperaturfühler Heizkreis 14 fehlerhaft",
    54: "Vorlauftemperaturfühler Heizkreis 15 fehlerhaft",
    55: "Vorlauftemperaturfühler Heizkreis 16 fehlerhaft",
    56: "Vorlauftemperaturfühler Heizkreis 17 fehlerhaft",
    57: "Vorlauftemperaturfühler Heizkreis 18 fehlerhaft",
    58: "Vor dem Stromausfall ist ein Busmodul ausgefallen",
    59: "Saugzug dreht sich nicht, trotz voller Ansteuerung",
    60: "Fühler im Boiler 01 fehlerhaft",
    61: "Kommunikation zum Pelletsmodul fehlerhaft",
    62: "Unbekannt",
    63: "001 EEPROM Lesefehler",
    64: "002 EEPROM Prüfsumme Null",
    65: "003 EEPROM Lesefehler",
    66: "004 EEPROM SW-Version falsch",
    67: "005 EEPROM Parameterlänge falsch",
    68: "006 EEPROM Lesefehler",
    69: "007 EEPROM Prüfsumme falsch",
    70: "008 EEPROM Schreibfehler",
    71: "009 EEPROM Schreibfehler",
    72: "010 Konfig. Listenfehler",
    73: "Fühler im Boiler 02 fehlerhaft",
    74: "Fühler im Boiler 03 fehlerhaft",
    75: "Fühler im Boiler 04 fehlerhaft",
    76: "Fühler im Boiler 05 fehlerhaft",
    77: "Fühler im Boiler 06 fehlerhaft",
    78: "Fühler im Boiler 07 fehlerhaft",
    79: "Fühler im Boiler 08 fehlerhaft",
    80: "Fühler Solarreferenz im Boiler 01 fehlerhaft",
    81: "Fühler Solarreferenz im Boiler 02 fehlerhaft",
    82: "Fühler Solarreferenz im Boiler 03 fehlerhaft",
    83: "Fühler Solarreferenz im Boiler 04 fehlerhaft",
    84: "Fühler Solarreferenz im Boiler 05 fehlerhaft",
    85: "Fühler Solarreferenz im Boiler 06 fehlerhaft",
    86: "Fühler Solarreferenz im Boiler 07 fehlerhaft",
    87: "Fühler Solarreferenz im Boiler 08 fehlerhaft",
    88: "Fühler oben im Puffer 1 fehlerhaft",
    89: "Fühler oben im Puffer 2 fehlerhaft",
    90: "Fühler oben im Puffer 3 fehlerhaft",
    91: "Fühler oben im Puffer 4 fehlerhaft",
    92: "Fühler Mitte im Puffer 1 fehlerhaft",
    93: "Fühler Mitte im Puffer 2 fehlerhaft",
    94: "Fühler Mitte im Puffer 3 fehlerhaft",
    95: "Fühler Mitte im Puffer 4 fehlerhaft",
    96: "Fühler unten im Puffer 1 fehlerhaft",
    97: "Fühler unten im Puffer 2 fehlerhaft",
    98: "Fühler unten im Puffer 3 fehlerhaft",
    99: "Fühler unten im Puffer 4 fehlerhaft",
    100: "Fühler im Zweitkessel fehlerhaft",
    101: "Kollektor-Überhitzung oder Kollektorfühler unterbrochen",
    102: "Fühler im Zusatzkessel fehlerhaft",
    103: "Der Füllstand kann nicht richtig interpretiert werden",
    104: "Die Bypassklappe konnte nicht öffnen",
    105: "Die Bypassklappe konnte nicht geschlossen werden",
    106: "Die Laufzeit zum Füllen wurde überschritten",
    107: "Die Austragsschnecke stopft an der Saugstelle",
    108: "Die Bypassklappe konnte weder öffnen noch schließen",
    109: "Zündversuch nicht gelungen von Hand Anheizen!",
    110: "Motorschutzschalter Saugzug gefallen",
    111: "Motorschutzschalter Stoker gefallen",
    112: "Motorschutzschalter Förderschnecke gefallen",
    113: "Rückbrandklappe öffnet zu schnell",
    114: "Rückbrandklappe schließt zu schnell",
    115: "Keine/Beide Endlagen der Rückbrandklappe aktiv",
    116: "Motorschutzschalter Zellradschleuse gefallen",
    117: "Lambdasonde defekt",
    118: "Abgastemperaturfühler defekt",
    119: "Feuerraumtemperaturfühler defekt",
    120: "LS im Fallschacht defekt",
    121: "Fallschachtdeckel offen",
    122: "Kesseltür zu lange offen oder Unterdruckmessdose defekt",
    123: "Rost öffnet nicht",
    124: "Sicherheitszeit wegen Füllstandsensor im Saugzyklon abgelaufen.",
    125: "Motorschutz der Austragsschnecke gefallen",
    126: "Stoker hat zu wenig Material",
    127: "Austragsschnecke Fehler",
    128: "GEFÄHRLICHER Zustand möglich",
    129: "Hackgutmodul ausgefallen -> Sofortabschaltung",
    130: "Saugmodul ausgefallen \n-> Sofortabschaltung",
    131: "Brennstoff lt. Anleitung einlegen",
    132: "RL Fühler für Netzpumpe fehlerhaft",
    133: "LS im Fallschacht der Austragsschnecke defekt (Voll)",
    134: "Fallschachtdeckel der Austragsschnecke offen",
    135: "Motorschutzschalter Austragsschnecke gefallen",
    136: "LS im Fallschacht der Zwischenschnecke 1 defekt (Voll)",
    137: "Fallschachtdeckel der Zwischenschnecke 1 offen",
    138: "Motorschutzschalter der Zwischenschnecke 1 gefallen",
    139: "Brenner reinigen und kontrollieren",
    140: "Rost schließt nicht",
    141: "Rückbrandklappe schließt nicht",
    142: "Rückbrandklappe öffnet nicht",
    143: "Zu oft Überstrom Zellradschleuse",
    144: "Zu oft Überstrom Stokerschnecke",
    145: "Zu oft Überstrom Förderschnecke",
    146: "Steuerung neu gestartet",
    147: "Rücklauffühler für Verteiler 1 fehlerhaft",
    148: "Rücklauffühler für Verteiler 2 fehlerhaft",
    149: "Rücklauffühler für Verteiler 3 fehlerhaft",
    150: "Rücklauffühler für Verteiler 4 fehlerhaft",
    151: "maximaler Einschub nach Änderung neu berechnet und begrenzt",
    152: "LS im Fallschacht der Zwischenschnecke 1 defekt (Leer)",
    153: "LS im Fallschacht der Austragsschnecke defekt (Leer)",
    154: "Absperrschieber blockiert",
    155: "Fehler Kessel und Brennstoffauswahl",
    156: "Kesselüberprüfung im Vorbereiten fehlerhaft",
    157: "Kesselundichtheit festgestellt aufgrund Einschuberkennung",
    158: "Kesselundichtheit festgestellt aufgrund O2 Überwachung",
    159: "Fühler für Zirkulationspumpe fehlerhaft",
    160: "Fühler für Solar WT sek. Vorlauf fehlerhaft",
    161: "Fühler für Solar Kollektor Rücklauf fehlerhaft",
    162: "Lambdasonde defekt",
    163: "Fehlerbehebung wurde abgebrochen",
    164: "Wärmequellen Fühler des Differenzregler defekt",
    165: "Wärmesenken Fühler des Differenzregler defekt",
    166: "Variante 3, es wurde ein Puffer und ein Verteiler mit der selben Nummer aktiviert",
    167: "Sondenumschaltung aufgrund Pelletsmangel oder Stopfsensor",
    168: "Vorratsbehälter leer, bitte Pellets Nachfüllen",
    169: "Aschebox voll, bitte entleeren",
    170: "Rostantrieb hat Überstrom, bitte 5 min warten",
    171: "Fühler 1 fehlerhaft",
    172: "Puffer Solarreferenz Fühler Fehlerhaft",
    173: "Aschebox voll, bitte entleeren",
    174: "Stokermotor nicht angesteckt oder funktioniert nicht",
    175: "Breitbandsonde nicht angesteckt oder Heizung der Sonde defekt",
    176: "Sensorelement der Breitbandsonde Fehlerhaft oder Kurzschluss",
    177: "Stokermotor nicht angesteckt oder funktioniert nicht",
    178: "Förderschnecke nicht angesteckt oder funktioniert nicht",
    179: "Aschebox zu lange offen, bzw. entfernt",
    180: "Unterdruck im VORBEREITEN zu gering",
    181: "Luftklappe blockiert",
    182: "Rücklaufanhebung und Boiler mittels HKP0 ist nicht möglich (gleicher Fühler)",
    183: "Frequenzumformer fehlerhaft",
    184: "Temperaturüberwachung des Saugzuges hat angesprochen (Klixon)",
    185: "linker Teil des Rostes schließt nicht",
    186: "rechter Teil des Rostes schließt nicht",
    187: "linker Teil des Rostes öffnet nicht",
    188: "rechter Teil des Rostes öffnet nicht",
    189: "Motorschutz des VBL hat angesprochen",
    190: "Motorschutz der Kesselladepumpe hat angesprochen",
    191: "Zu oft Überstrom Austragschnecke",
    192: "Zu oft Überstrom Zwischenschnecke",
    193: "Automatische Raumluftklappe öffnet nicht",
    194: "Luftzufuhr Fehlerhaft oder verschlossen",
    195: "Sicherheitszeit wegen Minsensor im Saugzyklon abgelaufen.",
    196: "Saugzugschalter nicht auf AUTO",
    197: "Motorschutzschalter Schubboden hat angesprochen",
    198: "Niveau für Hydrauliköl bei Schubboden zu niedrig",
    199: "Temperatur des Hydrauliköls für den Schubboden zu hoch",
    200: "Schlüsselschalter für Hydraulikraum nicht auf AUTO",
    201: "Sicherheitsendschalter für Schubboden hat angesprochen",
    202: "Wassertemperatur im Pelletsbrenner (F1) zu hoch",
    203: "WOS Antrieb ist blockiert oder nicht angeschlossen",
    204: "Luftdurchsatz zu gering oder Luftzufuhr fehlerhaft",
    205: "Kesselüberprüfung im Vorbereiten fehlerhaft",
    206: "Überfüllsicherung der ZRS hat angesprochen",
    207: "Zellradschleuse nicht angesteckt oder funktioniert nicht",
    208: "eingestellte Anzahl der Zwangszyklen am Schubboden überschritten",
    209: "Kesselstandardwerte nicht gesetzt (Menü Einstellen --> Allg. Einst.)",
    210: "Unterrostthermostat hat ausgelöst",
    211: "Unterdruck im VORBEREITEN zu hoch",
    212: "Rostantrieb meldet beide Endlagen aktiv",
    213: "Austragung kontrollieren",
    214: "Modul-Update fehlgeschlagen, bitte Pelletsmodul tauschen",
    215: "Messbereitschaft konnte nicht hergestellt werden",
    216: "Messbereitschaft konnte nicht aufrecht erhalten werden",
    217: "Eingestellter Mindestbestand im Pelletlager unterschritten",
    218: "Ungültige Parametrierung der Austragung",
    219: "Lichtschranke dauerhaft belegt oder defekt",
    220: "Temperaturüberschreitung am Wärmetauscher",
    221: "Motorschutzschalter vom Rührwerk gefallen",
    222: "FU Betriebssignal vom AGR-Gebläse abgefallen",
    223: "Sicherheitsschalter E-Filter geöffnet",
    224: "Fehler Wassersensor E-Filter",
    225: "Übertemperatur HV-Box",
    226: "Kommunikationsfehler E-Filter",
    227: "HV-Fehler E-Filter",
    228: "Betriebssignal vom Saugzug FU fehlerhaft",
    229: "Störung der DBBK Pumpe",
    230: "Motorschutzschalter Der Schnecke 1 auf LS gefallen",
    231: "Motorschutzschalter Der Schnecke 2 auf LS gefallen",
    232: "Displaymodul mit der Adresse 0 ist ausgefallen (DA 24)",
    233: "Displaymodul mit der Adresse 1 ist ausgefallen (DA 25)",
    234: "Displaymodul mit der Adresse 2 ist ausgefallen (DA 26)",
    235: "Displaymodul mit der Adresse 3 ist ausgefallen (DA 27)",
    236: "Displaymodul mit der Adresse 4 ist ausgefallen (DA 28)",
    237: "Displaymodul mit der Adresse 5 ist ausgefallen (DA 29)",
    238: "Displaymodul mit der Adresse 6 ist ausgefallen (DA 30)",
    239: "Displaymodul mit der Adresse 7 ist ausgefallen (DA 31)",
    240: "Displaymodul mit der Adresse 0 ist ausgefallen (DA 243)",
    241: "Heizkreismodul mit der Adresse 0 ist ausgefallen (DA 32)",
    242: "Heizkreismodul mit der Adresse 1 ist ausgefallen (DA 33)",
    243: "Heizkreismodul mit der Adresse 2 ist ausgefallen (DA 34)",
    244: "Heizkreismodul mit der Adresse 3 ist ausgefallen (DA 35)",
    245: "Heizkreismodul mit der Adresse 4 ist ausgefallen (DA 36)",
    246: "Heizkreismodul mit der Adresse 5 ist ausgefallen (DA 37)",
    247: "Heizkreismodul mit der Adresse 6 ist ausgefallen (DA 38)",
    248: "Heizkreismodul mit der Adresse 7 ist ausgefallen (DA 39)",
    249: "Hydraulikmodul mit der Adresse 0 ist ausgefallen (DA 40)",
    250: "Hydraulikmodul mit der Adresse 1 ist ausgefallen (DA 41)",
    251: "Hydraulikmodul mit der Adresse 2 ist ausgefallen (DA 42)",
    252: "Hydraulikmodul mit der Adresse 3 ist ausgefallen (DA 43)",
    253: "Hydraulikmodul mit der Adresse 4 ist ausgefallen (DA 44)",
    254: "Hydraulikmodul mit der Adresse 5 ist ausgefallen (DA 45)",
    255: "Hydraulikmodul mit der Adresse 6 ist ausgefallen (DA 46)",
    256: "Hydraulikmodul mit der Adresse 7 ist ausgefallen (DA 47)",
    257: "Digitalmodul mit der Adresse 0 ist ausgefallen (DA 48)",
    258: "Digitalmodul mit der Adresse 1 ist ausgefallen (DA 49)",
    259: "Digitalmodul mit der Adresse 2 ist ausgefallen (DA 50)",
    260: "Digitalmodul mit der Adresse 3 ist ausgefallen (DA 51)",
    261: "Digitalmodul mit der Adresse 4 ist ausgefallen (DA 52)",
    262: "Digitalmodul mit der Adresse 5 ist ausgefallen (DA 53)",
    263: "Digitalmodul mit der Adresse 6 ist ausgefallen (DA 54)",
    264: "Digitalmodul mit der Adresse 7 ist ausgefallen (DA 55)",
    265: "Kaskadenmodul mit der Adresse 0 ist ausgefallen (DA 56)",
    266: "Kaskadenmodul mit der Adresse 1 ist ausgefallen (DA 57)",
    267: "Kaskadenmodul mit der Adresse 2 ist ausgefallen (DA 58)",
    268: "Kaskadenmodul mit der Adresse 3 ist ausgefallen (DA 59)",
    269: "Kaskadenmodul mit der Adresse 4 ist ausgefallen (DA 60)",
    270: "Kaskadenmodul mit der Adresse 5 ist ausgefallen (DA 61)",
    271: "Kaskadenmodul mit der Adresse 6 ist ausgefallen (DA 62)",
    272: "Kaskadenmodul mit der Adresse 7 ist ausgefallen (DA 63)",
    273: "Analogmodul mit der Adresse 0 ist ausgefallen (DA 64)",
    274: "Analogmodul mit der Adresse 1 ist ausgefallen (DA 65)",
    275: "Analogmodul mit der Adresse 2 ist ausgefallen (DA 66)",
    276: "Analogmodul mit der Adresse 3 ist ausgefallen (DA 67)",
    277: "Analogmodul mit der Adresse 4 ist ausgefallen (DA 68)",
    278: "Analogmodul mit der Adresse 5 ist ausgefallen (DA 69)",
    279: "Analogmodul mit der Adresse 6 ist ausgefallen (DA 70)",
    280: "Analogmodul mit der Adresse 7 ist ausgefallen (DA 71)",
    281: "Touch Display mit der Adresse 0 ist ausgefallen (DA 72)",
    282: "Touch Display mit der Adresse 1 ist ausgefallen (DA 73)",
    283: "Touch Display mit der Adresse 2 ist ausgefallen (DA 74)",
    284: "Touch Display mit der Adresse 3 ist ausgefallen (DA 75)",
    285: "Touch Display mit der Adresse 4 ist ausgefallen (DA 76)",
    286: "Touch Display mit der Adresse 5 ist ausgefallen (DA 77)",
    287: "Touch Display mit der Adresse 6 ist ausgefallen (DA 78)",
    288: "Touch Display mit der Adresse 7 ist ausgefallen (DA 79)",
    289: "Austragungsmodul mit der Adresse 0 ist ausgefallen (DA 80)",
    290: "Austragungsmodul mit der Adresse 1 ist ausgefallen (DA 81)",
    291: "Austragungsmodul mit der Adresse 2 ist ausgefallen (DA 82)",
    292: "Austragungsmodul mit der Adresse 3 ist ausgefallen (DA 83)",
    293: "Austragungsmodul mit der Adresse 4 ist ausgefallen (DA 84)",
    294: "Austragungsmodul mit der Adresse 5 ist ausgefallen (DA 85)",
    295: "Austragungsmodul mit der Adresse 6 ist ausgefallen (DA 86)",
    296: "Austragungsmodul mit der Adresse 7 ist ausgefallen (DA 87)",
    297: "Pelletsmodul mit der Adresse 0 ist ausgefallen (DA 240)",
    298: "Hackgutmodul mit der Adresse 0 ist ausgefallen (DA 241)",
    299: "Saugmodul mit der Adresse 0 ist ausgefallen (DA 242)",
    300: "Breitband Sonden Modul 0 ist ausgefallen (DA 244)",
    301: "Rücklaufmischermodul 0 ist ausgefallen (DA 245)",
    302: "Fühler für Solarreferenz Puffer oben fehlerhaft",
    303: "Fühler für Solarreferenz Puffer unten fehlerhaft",
    304: "MIN Unterdruck im Feuerraum unterschritten",
    305: "Motorschutzschalter der Saugschnecke vom Zyklon 1 gefallen",
    306: "Motorschutzschalter der Saugschnecke vom Zyklon 2 gefallen",
    307: "Zu oft Überstrom der Saugschnecke an Zyklon 1",
    308: "Zu oft Überstrom der Saugschnecke an Zyklon 2",
    309: "Schnecke 1 auf LS nicht angesteckt oder funktioniert nicht",
    310: "Schnecke 2 auf LS nicht angesteckt oder funktioniert nicht",
    311: "Saugschnecke von Zyklon 1 nicht angesteckt oder funktioniert nicht",
    312: "Saugschnecke von Zyklon 2 nicht angesteckt oder funktioniert nicht",
    313: "Rührwerk nicht angesteckt oder funktioniert nicht",
    314: "Zu oft Überstrom der Schnecke 1 auf LS",
    315: "Zu oft Überstrom der Schnecke 2 auf LS",
    316: "Falsche oder fehlerhafte Kesselauswahl",
    317: "Falsche oder fehlerhafte Brennstoffauswahl",
    318: "Temperaturüberschreitung am Stokerrohr",
    319: "Kombiantrieb blockiert",
    320: "AGR-Aktivierungsklappe schließt nicht",
    321: "HK1 - Vorlauf-Temperatur zu lange zu hoch",
    322: "HK2 - Vorlauf-Temperatur zu lange zu hoch",
    323: "HK3 - Vorlauf-Temperatur zu lange zu hoch",
    324: "HK4 - Vorlauf-Temperatur zu lange zu hoch",
    325: "HK5 - Vorlauf-Temperatur zu lange zu hoch",
    326: "HK6 - Vorlauf-Temperatur zu lange zu hoch",
    327: "HK7 - Vorlauf-Temperatur zu lange zu hoch",
    328: "HK8 - Vorlauf-Temperatur zu lange zu hoch",
    329: "HK9- Vorlauf-Temperatur zu lange zu hoch",
    330: "HK10- Vorlauf-Temperatur zu lange zu hoch",
    331: "HK11 - Vorlauf-Temperatur zu lange zu hoch",
    332: "HK12 - Vorlauf-Temperatur zu lange zu hoch",
    333: "HK13 - Vorlauf-Temperatur zu lange zu hoch",
    334: "HK14 - Vorlauf-Temperatur zu lange zu hoch",
    335: "HK15 - Vorlauf-Temperatur zu lange zu hoch",
    336: "HK16 - Vorlauf-Temperatur zu lange zu hoch",
    337: "HK17 - Vorlauf-Temperatur zu lange zu hoch",
    338: "HK18 - Vorlauf-Temperatur zu lange zu hoch",
    339: "Boiler Solarreferenz Fühler Fehlerhaft",
    340: "AGR-Druckregelklappe blockiert",
    341: "Druck im AGR-Druckkanal zu lange außerhalb des erlaubten Bereichs",
    342: "Rost-Differenzdruck zu lange zu niedrig",
    343: "Übertemperatur Durchbrandbogenkühlung",
    344: "Ansteuerung des Saugers defekt, bitte Pelletsmodul tauschen",
    345: "Kipprost 1 schließt nicht",
    346: "Kipprost 1 öffnet nicht",
    347: "Rostantrieb 1 meldet beide Endlagen aktiv",
    348: "Kipprost 2 schließt nicht",
    349: "Kipprost 2 öffnet nicht",
    350: "Rostantrieb 2 meldet beide Endlagen aktiv",
    351: "Temperaturanstieg am Fühler 1 ist zu gering",
    352: "AGR-Primärluftklappe blockiert",
    353: "AGR-Sekundärluftklappe blockiert",
    354: "Raumfühler Heizkreis 1 fehlerhaft",
    355: "Raumfühler Heizkreis 2 fehlerhaft",
    356: "Raumfühler Heizkreis 3 fehlerhaft",
    357: "Raumfühler Heizkreis 4 fehlerhaft",
    358: "Raumfühler Heizkreis 5 fehlerhaft",
    359: "Raumfühler Heizkreis 6 fehlerhaft",
    360: "Raumfühler Heizkreis 7 fehlerhaft",
    361: "Raumfühler Heizkreis 8 fehlerhaft",
    362: "Raumfühler Heizkreis 9 fehlerhaft",
    363: "Raumfühler Heizkreis 10 fehlerhaft",
    364: "Raumfühler Heizkreis 11 fehlerhaft",
    365: "Raumfühler Heizkreis 12 fehlerhaft",
    366: "Raumfühler Heizkreis 13 fehlerhaft",
    367: "Raumfühler Heizkreis 14 fehlerhaft",
    368: "Raumfühler Heizkreis 15 fehlerhaft",
    369: "Raumfühler Heizkreis 16 fehlerhaft",
    370: "Raumfühler Heizkreis 17 fehlerhaft",
    371: "Raumfühler Heizkreis 18 fehlerhaft",
    372: "011 EEPROM Prüfsumme 2 falsch",
    373: "STB, min. Druck, max. Druck oder Wassermangelsicherung ausgelöst.",
    374: "AGR-Klappe blockiert",
    375: "Rücklauftemperatur zu hoch",
    376: "Kesseltür offen oder Unterdruckmessdose defekt",
    377: "Saugzug dreht sich ohne Ansteuerung",
    378: "Bitte den Kessel jetzt zur Vorbereitung für die Kaminkehrermessung anheizen!",
    379: "Rücklauftemperatur zu lange über Kesseltemperatur",
    380: "Ansaugöffnung kontrollieren",
    381: "Kondensatabfluss kontrollieren",
    382: "Unterdruck zu niedrig",
    383: "Laufrichtung Absperrschieber kontrollieren.",
    384: "Aschebehälter voll oder WOS blockiert - Noch 20h Heizbetrieb möglich",
    385: "Stokerantrieb zieht Strom ohne Ansteuerung",
    386: "Kesselüberprüfung im Vorbereiten fehlerhaft",
    387: "Kipprost 3 schließt nicht",
    388: "Kipprost 3 öffnet nicht",
    389: "Rostantrieb 3 meldet beide Endlagen aktiv",
    390: "Fühler Durchbrandbogen fehlerhaft",
    391: "Fühler 2 im Puffer 1 fehlerhaft",
    392: "Fühler 2 im Puffer 2 fehlerhaft",
    393: "Fühler 2 im Puffer 3 fehlerhaft",
    394: "Fühler 2 im Puffer 4 fehlerhaft",
    395: "Rostmotor konnte Endlage nicht halten",
    396: "Unterdruck im VORBEREITEN gering - Reinigungszustand des Kessels prüfen!",
    397: "Unzulässiger Temperaturanstieg am Stoker",
    398: "Motorschutz der Ascheschnecke gefallen.",
    399: "Messbereitschaft konnte nicht hergestellt/aufrecht erhalten werden, Restsauerstoff nicht stabil",
    400: "Messbereitschaft konnte nicht hergestellt/aufrecht erhalten werden, Abgastemperatur zu niedrig",
    401: "Messbereitschaft konnte nicht hergestellt/aufrecht erhalten werden, Feuerraumtemp. zu gering",
    402: "Messbereitschaft konnte nicht hergestellt/aufrecht erhalten werden, Leistungsabnahme zu gering",
    403: "Messbereitschaft konnte nicht hergestellt/aufrecht erhalten werden, Abscheideleistung zu gering",
    404: "Fühler 3 im Puffer 1 fehlerhaft",
    405: "Fühler 3 im Puffer 2 fehlerhaft",
    406: "Fühler 3 im Puffer 3 fehlerhaft",
    407: "Fühler 3 im Puffer 4 fehlerhaft",
    408: "Saugschnecke 1 nicht angesteckt oder funktioniert nicht",
    409: "Saugschnecke 2 nicht angesteckt oder funktioniert nicht",
    410: "Saugschnecke 3 nicht angesteckt oder funktioniert nicht",
    411: "Zu oft Überstrom der Saugschnecke 1",
    412: "Zu oft Überstrom der Saugschnecke 2",
    413: "Zu oft Überstrom der Saugschnecke 3",
    414: "Motorschutzschalter der Saugschnecke 1 gefallen",
    415: "Motorschutzschalter der Saugschnecke 2 gefallen",
    416: "Motorschutzschalter der Saugschnecke 3 gefallen",
    417: "Ist ein Wärmequellenfüher vorhanden?",
    418: "Drehzahlprüfung im Vorbereiten fehlgeschlagen",
    419: "Unterdruck im Vorbereiten gering – Brenner reinigen!",
    420: "Unterdruck im Vorbereiten zu gering",
    421: "Zündversuch ist nicht gelungen. - ACHTUNG! Werden Maßnahmen nicht befolgt, kann eine gefährliche Situation eintreten LEBENSGEFAHR!",
    422: "Fühler in der STB Hülse fehlerhaft",
    423: "Überdruck vor Zyklonabscheider erkannt",
    424: "Kesseltemperaturfühler 2 fehlerhaft",
    425: "Fühler 4 im Puffer 1 fehlerhaft",
    426: "Fühler 5 im Puffer 1 fehlerhaft",
    427: "Fühler 6 im Puffer 1 fehlerhaft",
    428: "Fühler 7 im Puffer 1 fehlerhaft",
    429: "Vorlauffühler für Wärmemengenerfassung des Kessels fehlerhaf"
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
                result = client.read_input_registers(self._register - 30001, count=1, device_id=2)
                if result.isError():
                    _LOGGER.error("Error reading Modbus input register %s", self._register - 30001)
                    self._state = None
                else:
                    raw_value = result.registers[0]
                    if raw_value == 0xFFFF:
                        self._state = "Kein Fehler"
                    else:
                        self._state = self._mapping.get(raw_value, f"Unbekannter Fehler ({raw_value})")
                    _LOGGER.debug( "Reading Modbus input register: %s, raw=%s, state: %s", self._register - 30001, raw_value, self._state)
            except Exception as e:
                _LOGGER.error("Exception during Modbus communication: %s", e)
            finally:
                client.close()
