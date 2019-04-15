from datetime import datetime
from main.tinydb_helper import TinyBase


class Module(TinyBase):
    id = 0
    name = ''
    start_order = 0
    active = False
    host_name = ''

    def __init__(self, copy=None):
        TinyBase.__init__(self, Module, copy)


class Pwm(TinyBase):
    id = 0
    name = ''
    frequency = 0
    duty_cycle = 0
    gpio_pin_code = 0
    host_name = ''
    update_on = datetime.now()

    def __init__(self, copy=None):
        TinyBase.__init__(self, Pwm, copy)


class GpioPin(TinyBase):
    id = 0
    host_name = ''
    pin_type = ''  # bbb, pi, piface
    pin_code = ''  # friendly format, unique for host, Beagle = P9_11, PI = pin_index
    pin_index_bcm = ''  # bcm format, 0 to n
    pin_value = 0  # 0, 1 or None
    pin_direction = ''  # in, out, None
    board_index = 0  # 0 to n (max 3 for piface)
    description = ''
    is_active = False  # if pin was setup(exported) through this app. will be unexported when app exit
    updated_on = datetime.now

    def __init__(self, copy=None):
        TinyBase.__init__(self, GpioPin, copy)


class Sensor(TinyBase):
    id = 0
    address = ''
    type = ''
    temperature = 0.0
    humidity = 0.0
    pressure = 0.0
    counters_a = 0
    counters_b = 0
    delta_counters_a = 0
    delta_counters_b = 0
    iad = 0.0  # current in Amper for qubino sensors
    vdd = 0.0  # power factor for qubino sensors
    vad = 0.0  # voltage in Volts for qubino sensors
    pio_a = 0
    pio_b = 0
    sensed_a = 0
    sensed_b = 0
    battery_level = 0  # RFXCOM specific, sensor battery
    rssi = 0  # RFXCOM specific, rssi - distance
    updated_on = datetime.now
    added_on = datetime.now
    # FIXME: now filled manually, try relations
    # zone_name = Column(String(50))
    sensor_name = ''
    alt_address = ''  # alternate address format, use for 1-wire, better readability
    comment = ''

    def __init__(self, copy=None):
        TinyBase.__init__(self, Sensor, copy)


class ZoneSensor(TinyBase):
    id = 0
    sensor_name = ''
    zone_id = 0
    # zone = db.relationship('Zone', backref=db.backref('ZoneSensor(zone)', lazy='dynamic'))
    sensor_address = ''
    target_material = ''  # what material is being measured, water, air, etc
    alt_address = ''
    is_main = False  # is main temperature sensor for heat reference

    def __init__(self, copy=None):
        TinyBase.__init__(self, ZoneSensor, copy)


class ZoneCustomRelay(TinyBase):
    id = 0
    relay_pin_name = ''
    zone_id = 0
    gpio_pin_code = ''
    gpio_host_name = ''
    relay_is_on = False
    relay_type = ''
    expire = 0  # after how many seconds state goes back to original state
    updated_on = datetime.now()

    def __init__(self, copy=None):
        TinyBase.__init__(self, ZoneCustomRelay, copy)


class Zone(TinyBase):
    id = 0
    name = ''
    # active_heat_schedule_pattern_id = Column(Integer)
    # heat_is_on = Column(Boolean, default=False)
    # last_heat_status_update = Column(DateTime(), default=None)
    # heat_target_temperature = Column(Integer)
    is_indoor_heated = False
    is_indoor = False
    is_outdoor = False
    is_outdoor_heated = False

    def __init__(self, copy=None):
        TinyBase.__init__(self, Zone, copy)


class DustSensor(TinyBase):
    id = 0
    address = ''
    pm_1 = 0
    pm_2_5 = 0
    pm_10 = 0
    p_0_3 = 0
    p_0_5 = 0
    p_1 = 0
    p_2_5 = 0
    p_5 = 0
    p_10 = 0
    updated_on = datetime.now()

    def __init__(self, copy=None):
        TinyBase.__init__(self, DustSensor, copy)


class PowerMonitor(TinyBase):
    id = 0
    name = ''
    type = ''  # INA, etc
    host_name = ''
    voltage = 0.0  # volts, estimated voltage when using divider and batteries in series
    current = 0.0  # miliamps
    power = 0.0
    raw_voltage = 0.0  # volts, read from sensor without
    max_voltage = 0.0
    warn_voltage = 0.0
    critical_voltage = 0.0
    min_voltage = 0.0
    warn_current = 0.0
    critical_current = 0.0
    i2c_addr = ''
    voltage_divider_ratio = 0.0  # divider (0.5 etc)
    subtracted_sensor_id_list = ''  # comma separated sensor ids, total voltage to be subtracted
    updated_on = datetime.now()

    def __init__(self, copy=None):
        TinyBase.__init__(self, PowerMonitor, copy)
