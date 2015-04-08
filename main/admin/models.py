from datetime import datetime

from flask_sqlalchemy import SQLAlchemy #workaround for resolve issue
from sqlalchemy_utils import ChoiceType
from main import db
import graphs

class DbEvent:
    db_notified_=False
    notify_enabled_=False
    event_sent_datetime_ = None

class Module(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    host_name = db.Column(db.String(50))
    name = db.Column(db.String(50))
    active = db.Column(db.Boolean(), default=False)
    start_order = db.Column(db.Integer)

    def __init__(self, id='', host_name='', name='', active=False, start_order='999'):
        if id:
            self.id = id
        self.host_name = host_name
        self.name = name
        self.active = active
        self.start_order = start_order

    def __repr__(self):
        return 'Module {} {}, {}'.format(self.id, self.host_name, self.name[:50])

class Zone(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))

    def __init__(self, id='', name=''):
        if id:
            self.id = id
        self.name = name

    def __repr__(self):
        return 'Zone id {} {}'.format(self.id, self.name[:20])

class SchedulePattern(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    pattern = db.Column(db.String(24))

    def __init__(self, id, name, pattern):
        if id:
            self.id = id
        self.name = name
        self.pattern = pattern

    def __repr__(self):
        return self.name[:len('1234-5678-9012-3456-7890-1234')]


class TemperatureTarget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(1))
    target = db.Column(db.Float)

    def __init__(self, id, code, target):
        self.id = id
        self.code = code
        self.target = target

    def __repr__(self):
        return '{} code {}={}'.format(self.id, self.code, self.target)


class HeatSchedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    zone_id = db.Column(db.Integer, db.ForeignKey('zone.id'), nullable=False)
    #zone = db.relationship('Zone', backref=db.backref('heat schedule zone', lazy='dynamic'))
    pattern_week_id = db.Column(db.Integer, db.ForeignKey('schedule_pattern.id'), nullable=False)
    pattern_weekend_id = db.Column(db.Integer, db.ForeignKey('schedule_pattern.id'), nullable=False)
    #pattern_week = db.relationship('SchedulePattern', foreign_keys='[HeatSchedule.pattern_week_id]',
    #                               backref=db.backref('schedule_pattern_week', lazy='dynamic'))
    #pattern_weekend = db.relationship('SchedulePattern', foreign_keys='[HeatSchedule.pattern_weekend_id]',
    #                                backref=db.backref('schedule_pattern_weekend', lazy='dynamic'))
    active = db.Column(db.Boolean, default=True)

    def __init__(self, id, zone_id, pattern_week_id, pattern_weekend_id):
        self.id = id
        self.zone_id= zone_id
        self.pattern_week_id= pattern_week_id
        self.pattern_weekend_id= pattern_weekend_id

    def __repr__(self):
        return 'Zone {}, Active {}, Week {}, Weekend {}'.format(self.zone_id, self.active,
                self.pattern_week_id, self.pattern_weekend_id)


class Sensor(db.Model, graphs.SensorGraph, DbEvent):
    id = db.Column(db.Integer, primary_key=True)
    address = db.Column(db.String(50), unique=True)
    type = db.Column(db.String(50))
    temperature = db.Column(db.Float)
    humidity = db.Column(db.Float)
    counters_a = db.Column(db.BigInteger)
    counters_b = db.Column(db.BigInteger)
    iad = db.Column(db.Float)
    vdd = db.Column(db.Float)
    vad = db.Column(db.Float)
    pio_a = db.Column(db.Integer)
    pio_b = db.Column(db.Integer)
    sensed_a = db.Column(db.Integer)
    sensed_b = db.Column(db.Integer)
    updated_on = db.Column(db.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow)
    #FIXME: now filled manually, try relations
    zone_name = db.Column(db.String(50))
    sensor_name = db.Column(db.String(50))

    def __init__(self, address=''):
        self.address= address

    def __repr__(self):
        return 'Sensor {}, {}{}'.format(self.type, self.sensor_name, self.address)
    
    def comparator_unique_graph_record(self):
        return str(self.temperature)+str(self.humidity)+str(self.counters_a)+str(self.counters_b) \
               + str(self.iad) + str(self.vad) + str(self.vdd) + str(self.pio_a) + str(self.pio_b) \
                + str(self.sensed_a) + str(self.sensed_b)


class Parameter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True)
    value = db.Column(db.String(255))

    def __init__(self, id='', name='', value=''):
        if id:
            self.id = id
        self.name = name
        self.value = value

    def __repr__(self):
        return '{}, {}'.format(self.name, self.value)

class ZoneSensor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sensor_name = db.Column(db.String(50))
    zone_id = db.Column(db.Integer, db.ForeignKey('zone.id'))
    #zone = db.relationship('Zone', backref=db.backref('ZoneSensor(zone)', lazy='dynamic'))
    sensor_address = db.Column(db.String(50), db.ForeignKey('sensor.address'))
    #sensor = db.relationship('Sensor', backref=db.backref('ZoneSensor(sensor)', lazy='dynamic'))

    def __init__(self, zone_id='', sensor_address ='', sensor_name=''):
        self.sensor_address= sensor_address
        self.zone_id = zone_id
        self.sensor_name = sensor_name

    def __repr__(self):
        return 'ZoneSensor zone {} sensor {}'.format(self.zone_id,  self.sensor_name)

class Node(db.Model, DbEvent):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    ip = db.Column(db.String(15), nullable=False)
    is_master_overall = db.Column(db.Boolean(), default=False)
    is_master_db_archive = db.Column(db.Boolean(), default=False)
    is_master_graph = db.Column(db.Boolean(), default=False)
    is_master_rule = db.Column(db.Boolean(), default=False)
    priority = db.Column(db.Integer)
    execute_command=db.Column(db.String(50))
    updated_on = db.Column(db.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow)

    def __init__(self, id='', name ='', ip='', priority=''):
        if id:
            self.id = id
        self.name = name
        self.ip = ip
        self.priority = priority

    def __repr__(self):
        return 'Node {} ip {}'.format(self.name,  self.ip)

    def comparator_unique_graph_record(self):
        return str(self.is_master_overall) + str(self.is_master_db_archive) \
               + str(self.is_master_graph) + str(self.is_master_rule) + str(self.priority) + str(self.ip)

#class GraphPlotly(db.Model):
#    id = db.Column(db.Integer, primary_key=True)
#    name = db.Column(db.String(50), unique=True)
#    url = db.Column(db.String(255))
#    field_list = db.Column(db.String(2000))

#    def __init__(self, id='', name ='', url=''):
#        if id:
#            self.id = id
#        self.name = name
#        self.url = url
#
#    def __repr__(self):
#        return 'GraphPlotly {} ip {}'.format(self.name,  self.url)

class SystemMonitor(db.Model, graphs.SystemMonitorGraph, DbEvent):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True)
    cpu_usage_percent = db.Column(db.Float)
    memory_available_percent = db.Column(db.Float)
    uptime_days = db.Column(db.Integer)
    updated_on = db.Column(db.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return '{} {} {}'.format(self.id, self.name, self.updated_on)

    def comparator_unique_graph_record(self):
        return 'c{}m{}u{}'.format(self.cpu_usage_percent, self.memory_available_percent, self.uptime_days)

class SystemDisk(db.Model, graphs.SystemDiskGraph, DbEvent):
    id = db.Column(db.Integer, primary_key=True)
    serial = db.Column(db.String(50), unique=True)
    system_name = db.Column(db.String(50))
    hdd_name = db.Column(db.String(50))
    hdd_disk_dev = db.Column(db.String(50))
    temperature = db.Column(db.Float)
    sector_error_count = db.Column(db.Integer)
    smart_status = db.Column(db.String(50))
    power_status = db.Column(db.String(50))
    load_cycle_count = db.Column(db.Integer)
    start_stop_count = db.Column(db.Integer)
    updated_on = db.Column(db.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return '{} {} {} {} {}'.format(self.id, self.serial,  self.system_name, self.hdd_name, self.hdd_disk_dev)

    def comparator_unique_graph_record(self):
        return str(self.temperature) + str(self.sector_error_count) + str(self.smart_status) \
               + str(self.power_status) + str(self.hdd_disk_dev) + str(self.load_cycle_count) \
                + str(self.start_stop_count)

class GpioPin(db.Model, DbEvent):
    id = db.Column(db.Integer, primary_key=True)
    host_name = db.Column(db.String(50))
    pin_type = db.Column(db.String(50))
    pin_code = db.Column(db.String(50), unique=True)
    pin_value = db.Column(db.Integer)

    def __repr__(self):
        return 'host {} code {} type {} value {}'.format(self.host_name, self.pin_code, self.pin_type, self.pin_value)

class ZoneAlarm(db.Model, DbEvent):
    id = db.Column(db.Integer, primary_key=True)
    #friendly display name for pin mapping
    alarm_pin_name = db.Column(db.String(50))
    zone_id = db.Column(db.Integer)#, db.ForeignKey('zone.id'))
    #zone = db.relationship('Zone', backref=db.backref('ZoneAlarm(zone)', lazy='dynamic'))
    #gpio_pin_code = db.Column(db.String(50), db.ForeignKey('gpio_pin.pin_code'))
    gpio_pin_code = db.Column(db.String(50))
    gpio_host_name = db.Column(db.String(50))
    #gpio_pin = db.relationship('GpioPin', backref=db.backref('ZoneAlarm(gpiopincode)', lazy='dynamic'))
    alarm_status = db.Column(db.Integer)
    updated_on = db.Column(db.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow)

    def __init__(self, zone_id='', gpio_pin_code='', host_name=''):
        self.zone_id = zone_id
        self.gpio_pin_code = gpio_pin_code
        self.gpio_host_name = host_name

    def __repr__(self):
        return 'host {} gpiopin {} {}'.format(self.gpio_host_name, self.gpio_pin_code, self.alarm_pin_name)

class ZoneHeatRelay(db.Model, DbEvent):
    id = db.Column(db.Integer, primary_key=True)
    #friendly display name for pin mapping
    heat_pin_name = db.Column(db.String(50))
    zone_id = db.Column(db.Integer)
    gpio_pin_code = db.Column(db.String(50))
    gpio_host_name = db.Column(db.String(50))
    heat_status = db.Column(db.Integer)
    updated_on = db.Column(db.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow)

    def __init__(self, zone_id='', gpio_pin_code='', host_name=''):
        self.zone_id = zone_id
        self.gpio_pin_code = gpio_pin_code
        self.gpio_host_name = host_name

    def __repr__(self):
        return 'host {} gpiopin {} {}'.format(self.gpio_host_name, self.gpio_pin_code, self.heat_pin_name)