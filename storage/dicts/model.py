from datetime import datetime
from storage.dicts.model_helper import ModelBase


class Module(ModelBase):
    """key=id"""
    id = 0
    name = ''
    start_order = 0
    active = False
    host_name = ''


class Pwm(ModelBase):
    """key=name"""
    id = 0
    name = ''
    frequency = 0
    duty_cycle = 0
    gpio_pin_code = 0
    host_name = ''
    target_watts = 0
    update_on = datetime.now()


class GpioPin(ModelBase):
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
    contact_type = ''
    updated_on = datetime.now


class Sensor(ModelBase):
    address = ''
    id = 0
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
    sensor_name = ''
    alt_address = ''  # alternate address format, use for 1-wire, better readability
    comment = ''


class ZoneSensor(ModelBase):
    id = 0
    sensor_address = ''
    sensor_name = ''
    zone_id = 0
    # zone = db.relationship('Zone', backref=db.backref('ZoneSensor(zone)', lazy='dynamic'))
    target_material = ''  # what material is being measured, water, air, etc
    alt_address = ''
    is_main = False  # is main temperature sensor for heat reference


class ZoneCustomRelay(ModelBase):
    relay_pin_name = ''
    id = 0
    zone_id = 0
    gpio_pin_code = ''
    gpio_host_name = ''
    relay_is_on = False
    relay_type = ''
    expire = 0  # after how many seconds state goes back to original state
    updated_on = datetime.now()


class Zone(ModelBase):
    name = ''
    id = 0
    is_indoor_heated = False
    is_indoor = False
    is_outdoor = False
    is_outdoor_heated = False


class DustSensor(ModelBase):
    """key=address"""
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


class AirSensor(ModelBase):
    """key=address"""
    id = 0
    address = ''
    co2 = 0
    temperature = 0


class PowerMonitor(ModelBase):
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


class SystemDisk(ModelBase):
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


class SystemMonitor(ModelBase):
    """key=name"""
    id = 0
    name = ''
    cpu_usage_percent = 0.0
    cpu_temperature = 0.0
    memory_available_percent = 0.0
    uptime_days = 0
    updated_on = datetime.now()


class ZoneThermostat(ModelBase):
    """key=zone_id"""
    id = 0
    zone_id = 0
    zone_name = ''
    active_heat_schedule_pattern_id = 0
    heat_is_on = False
    last_heat_status_update = datetime.now()
    heat_actual_temperature = 0.0
    heat_target_temperature = 0.0
    mode_presence_auto = False
    last_presence_set = datetime.now()
    is_mode_manual = False
    manual_duration_min = 0  # period to keep heat on for manual mode
    manual_temp_target = 0.0
    last_manual_set = datetime.now()


class HeatSchedule(ModelBase):
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


class SchedulePattern(ModelBase):
    id = 0
    name = ''
    pattern = ''
    keep_warm = False  # keep the zone warm, used for cold floors
    keep_warm_pattern = ''  # pattern, 5 minutes increments of on/off: 100001000100
    activate_on_condition = False  # activate heat only if relay state condition is meet
    activate_condition_relay = ''  # the relay that must be on to activate this schedule pattern
    season_name = ''  # season name when this will apply
    main_source_needed = True  # main source must be on as well (i.e. gas heater)


class TemperatureTarget(ModelBase):
    id = 0
    code = ''
    target = 0.0
    direction = 1  # > 0 is a heating zone, < 0 is a cooling zone (fridge)


class ZoneHeatRelay(ModelBase):
    """key=zone_id"""
    id = 0
    # friendly display name for pin mapping
    heat_pin_name = ''
    zone_id = 0
    gpio_pin_code = ''  # user friendly format, e.g. P8_11
    relay_type = ''
    gpio_host_name = ''
    heat_is_on = False
    is_main_heat_source = False
    is_alternate_source_switch = False  # switch to alternate source
    is_alternate_heat_source = False  # used for low cost/eco main heat sources
    temp_sensor_name = ''  # temperature sensor name for heat sources to check for heat limit
    updated_on = datetime.now()


class Presence(ModelBase):
    """key=sensor_name"""
    id = 0
    zone_id = 0
    zone_name = ''
    sensor_name = ''
    event_type = ''  # cam, pir, contact, wifi, bt
    event_camera_date = datetime.now()
    event_alarm_date = datetime.now()
    event_io_date = datetime.now()
    event_wifi_date = datetime.now()
    event_bt_date = datetime.now()
    is_connected = False  # pin connected? true on unarmed sensors, false on alarm/move
    updated_on = datetime.now()


class ZoneArea(ModelBase):
    """key=id"""
    id = 0
    area_id = 0
    zone_id = 0


class Area(ModelBase):
    """key=name"""
    name = ''
    id = 0
    is_armed = False


# fixme: should be more generic, i.e. ZoneContact (with types = sensor, contact)
class ZoneAlarm(ModelBase):
    """key=id"""
    id = 0
    # friendly display name for pin mapping
    alarm_pin_name = ''
    zone_id = 0
    gpio_pin_code = ''
    gpio_host_name = ''
    sensor_type = ''
    alarm_pin_triggered = False  # True if alarm sensor is connected (move detected)
    is_false_alarm_prone = False  # True if sensor can easily trigger false alarms (gate move by wind)
    start_alarm = False  # True if alarm must start (because area/zone is armed)
    relay_type = ''
    updated_on = datetime.now()


class IOSensor(ModelBase):
    """key=sensor_name"""
    sensor_name = ''
    zone_id = 0
    io_code = ''
    host_name = ''
    sensor_type = ''
    purpose = ''
    relay_type = ''


class Node(ModelBase):
    name = ''
    id = 0
    ip = ''
    mac = ''
    os_type = ''
    machine_type = ''
    app_start_time = datetime.now()
    is_master_overall = False
    is_master_db_archive = False
    is_master_graph = False
    is_master_rule = False
    is_master_logging = False
    priority = 0  # used to decide who becomes main master in case several hosts are active
    master_overall_cycles = 0  # count of update cycles while node was master
    run_overall_cycles = 0  # count of total update cycles
    execute_command = ''
    updated_on = datetime.now()


class Utility(ModelBase):
    utility_name = ''  # unique name, can be different than sensor name for dual counter
    id = 0
    sensor_name = ''
    sensor_index = 0  # 0 for counter_a, 1 for counter_b
    units_total = 0.0  # total number of units measured
    units_delta = 0.0  # total number of units measured since last measurement
    units_2_delta = 0.0  # total number of units measured since last measurement
    ticks_delta = 0
    ticks_per_unit = 0.0  # number of counter ticks in a unit (e.g. 10 for a watt)
    unit_name = ''  # kwh, liter etc.
    unit_2_name = ''  # 2nd unit type, optional, i.e. watts
    unit_cost = 0.0
    cost = 0.0
    utility_type = ''  # water, electricity, gas
    updated_on = datetime.now()


class Device(ModelBase):
    id = 0
    name = ''
    type = ''
    bt_address = ''
    wifi_address = ''
    bt_signal = 0
    wifi_signal = 0
    last_bt_active = datetime.now()
    last_wifi_active = datetime.now()
    last_active = datetime.now()
    updated_on = datetime.now()


class People(ModelBase):
    id = 0
    name = ''  # unique name
    email = ''
    updated_on = datetime.now()


class PeopleDevice(ModelBase):
    id = 0
    people_id = 0
    device_id = 0
    give_presence = False
    updated_on = datetime.now()


class Rule(ModelBase):
    id = 0
    host_name = ''
    name = ''
    command = ''
    hour = ''
    minute = ''
    second = ''
    day_of_week = ''
    week = ''
    day = ''
    month = ''
    year = ''
    start_date = datetime.now()
    execute_now = False
    is_async = False
    is_active = False


class ZoneMusic(ModelBase):
    id = 0
    zone_id = 0
    server_ip = ''
    server_port = 0


class Music(ModelBase):
    """key=zone_name"""
    zone_name = ''  # unique name
    id = 0
    state = ''
    volume = 0
    position = 0  # percent
    title = ''
    artist = ''
    song = ''
    album = ''
    updated_on = datetime.now()


class MusicLoved(ModelBase):
    """key=lastfmsong"""
    id = 0
    lastfmsong = ''
    lastfmloved = False


class Ups(ModelBase):
    """key=name"""
    id = 0
    name = ''
    system_name = ''
    port = ''
    input_voltage = 0.0
    remaining_minutes = 0
    output_voltage = 0
    load_percent = 0.0
    power_frequency = 0
    battery_voltage = 0.0
    temperature = 0.0
    power_failed = False
    beeper_on = False
    test_in_progress = False
    other_status = ''
    updated_on = datetime.now()
