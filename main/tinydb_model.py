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
