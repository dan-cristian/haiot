from datetime import datetime
from main.tinydb_helper import TinyBase


class Module(TinyBase):
    id = 0
    name = ''
    start_order = 0
    active = False
    host_name = ''


class Pwm(TinyBase):
    id = 0
    name = ''
    frequency = 0
    duty_cycle = 0
    gpio_pin_code = 0
    host_name = ''
    update_on = datetime.now()


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


class ZoneSensor(TinyBase):
    id = 0
    sensor_name = ''
    zone_id = 0
    # zone = db.relationship('Zone', backref=db.backref('ZoneSensor(zone)', lazy='dynamic'))
    sensor_address = ''
    target_material = ''  # what material is being measured, water, air, etc
    alt_address = ''
    is_main = False  # is main temperature sensor for heat reference


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


class SystemDisk(TinyBase):
    id = 0
    serial = ''
    system_name = ''
    hdd_name = ''  # netbook /dev/sda
    hdd_device = ''  # usually empty?
    hdd_disk_dev = ''  # /dev/sda
    temperature = 0.0
    sector_error_count = 0
    smart_status = ''
    power_status = 0
    load_cycle_count = 0
    start_stop_count = 0
    last_reads_completed_count = 0.0
    last_reads_datetime = datetime.now()
    last_writes_completed_count = 0.0
    last_writes_datetime = datetime.now()
    last_reads_elapsed = 0.0
    last_writes_elapsed = 0.0
    updated_on = datetime.now()


class SystemMonitor(TinyBase):
    id = 0
    name = ''
    cpu_usage_percent = 0.0
    cpu_temperature = 0.0
    memory_available_percent = 0.0
    uptime_days = 0
    updated_on = datetime.now()


class ZoneThermostat(TinyBase):
    id = 0
    zone_id = 0
    zone_name = ''
    active_heat_schedule_pattern_id = 0
    heat_is_on = False
    last_heat_status_update = datetime.now()
    heat_target_temperature = 0.0
    mode_presence_auto = False  # fixme: not used yet
    last_presence_set = datetime.now()
    is_mode_manual = False
    manual_duration_min = 0  # period to keep heat on for manual mode
    manual_temp_target = 0.0
    last_manual_set = datetime.now()


class HeatSchedule(TinyBase):
    id = 0
    zone_id = 0
    # zone = db.relationship('Zone', backref=db.backref('heat schedule zone', lazy='dynamic'))
    pattern_week_id = 0
    pattern_weekend_id = 0
    ''' temp pattern if there is move in a zone, to ensure there is heat if someone is at home unplanned'''
    pattern_id_presence = 0
    ''' temp pattern if there is no move, to preserve energy'''
    pattern_id_no_presence = 0
    season = ''  # season name when this schedule will apply
    # active = True


class SchedulePattern(TinyBase):
    id = 0
    name = ''
    pattern = ''
    keep_warm = False  # keep the zone warm, used for cold floors
    keep_warm_pattern = ''  # pattern, 5 minutes increments of on/off: 100001000100
    activate_on_condition = False  # activate heat only if relay state condition is meet
    activate_condition_relay = ''  # the relay that must be on to activate this schedule pattern
    season_name = ''  # season name when this will apply
    main_source_needed = True  # main source must be on as well (i.e. gas heater)


class TemperatureTarget(TinyBase):
    id = 0
    code = ''
    target = 0.0


class ZoneHeatRelay(TinyBase):
    id = 0
    # friendly display name for pin mapping
    heat_pin_name = ''
    zone_id = 0
    gpio_pin_code = ''  # user friendly format, e.g. P8_11
    gpio_host_name = ''
    heat_is_on = False
    is_main_heat_source = False
    is_alternate_source_switch = False  # switch to alternate source
    is_alternate_heat_source = False  # used for low cost/eco main heat sources
    temp_sensor_name = ''  # temperature sensor name for heat sources to check for heat limit
    updated_on = datetime.now()
