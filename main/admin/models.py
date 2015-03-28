from datetime import datetime

from flask_sqlalchemy import SQLAlchemy #workaround for resolve issue
from main import db
import graphs

class DbEvent:
    db_notified_=False
    notify_enabled_=False

class Blog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), unique=True)
    body = db.Column(db.Text())
    created_on = db.Column(db.DateTime(), default=datetime.utcnow)
    updated_on = db.Column(db.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow)

    def __init__(self, title="", body=""):
        self.title = title
        self.body = body

    def __repr__(self):
        return '<Blogpost - {}>'.format(self.title)


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    blog_id = db.Column(db.Integer, db.ForeignKey('blog.id'))
    blog = db.relationship('Blog', backref=db.backref('comment', lazy='dynamic'))
    username = db.Column(db.String(50))
    comment = db.Column(db.Text())
    visible = db.Column(db.Boolean(), default=False)
    created_on = db.Column(db.DateTime(), default=datetime.utcnow)

    def __init__(self, post='', username='', comment=''):
        if post:
            self.blog = post
        self.username = username
        self.comment = comment

    def __repr__(self):
        return '<Comment: blog {}, {}>'.format(self.blog_id, self.comment[:20])


class Module(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    active = db.Column(db.Boolean(), default=False)
    start_order = db.Column(db.Integer)

    def __init__(self, id='', name='', active=False, start_order='999'):
        if id:
            self.id = id
        self.name = name
        self.active = active
        self.start_order = start_order

    def __repr__(self):
        return 'Module id {}, {}'.format(self.id, self.name[:50])




class Zone(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))

    def __init__(self, id='', name=''):
        if id:
            self.id = id
        self.name = name

    def __repr__(self):
        return '<Zone: id {}, {}>'.format(self.id, self.name[:20])


class SchedulePattern(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    pattern = db.Column(db.String(24))

    def __init__(self, id='', name=''):
        if id:
            self.id = id
        self.name = name

    def __repr__(self):
        return self.name[:24]


class TemperatureTarget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(1))
    target = db.Column(db.Float)

    def __repr__(self):
        return '{} code {}={}'.format(self.id, self.code, self.target)


class HeatSchedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    zone_id = db.Column(db.Integer, db.ForeignKey('zone.id'), nullable=False)
    zone = db.relationship('Zone', backref=db.backref('heat schedule zone', lazy='dynamic'))
    pattern_week_id = db.Column(db.Integer, db.ForeignKey('schedule_pattern.id'), nullable=False)
    pattern_weekend_id = db.Column(db.Integer, db.ForeignKey('schedule_pattern.id'), nullable=False)
    pattern_week = db.relationship('SchedulePattern', foreign_keys='[HeatSchedule.pattern_week_id]',
                                   backref=db.backref('schedule_pattern_week', lazy='dynamic'))
    pattern_weekend = db.relationship('SchedulePattern', foreign_keys='[HeatSchedule.pattern_weekend_id]',
                                    backref=db.backref('schedule_pattern_weekend', lazy='dynamic'))
    active = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return 'Zone {}, Active {}, Week {}, Weekend {}'.format(self.zone.name, self.active,
                self.pattern_week.name, self.pattern_weekend.name)


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

    def __init__(self, id='', address=''):
        if id:
            self.id = id
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
    zone = db.relationship('Zone', backref=db.backref('ZoneSensor(zone)', lazy='dynamic'))
    sensor_address = db.Column(db.Integer, db.ForeignKey('sensor.address'))
    sensor = db.relationship('Sensor', backref=db.backref('ZoneSensor(sensor)', lazy='dynamic'))

    def __init__(self, id='', sensor_name =''):
        if id:
            self.id = id
        self.sensor_name = sensor_name

    def __repr__(self):
        return 'ZoneSensor zone {} sensor {}'.format(self.zone,  self.sensor_name)

class Node(db.Model, graphs.NodeGraph, DbEvent):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    ip = db.Column(db.String(15), nullable=False)
    is_master_overall = db.Column(db.Boolean(), default=False)
    is_master_db_archive = db.Column(db.Boolean(), default=False)
    is_master_graph = db.Column(db.Boolean(), default=False)
    is_master_rule = db.Column(db.Boolean(), default=False)
    priority = db.Column(db.Integer)
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

class GraphPlotly(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True)
    url = db.Column(db.String(255))
    field_list = db.Column(db.String(2000))

    def __init__(self, id='', name ='', url=''):
        if id:
            self.id = id
        self.name = name
        self.url = url

    def __repr__(self):
        return 'GraphPlotly {} ip {}'.format(self.name,  self.url)

class SystemMonitor(db.Model, graphs.SystemMonitorGraph, DbEvent):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True)
    cpu_usage_percent = db.Column(db.Float)
    memory_available_percent = db.Column(db.Float)
    updated_on = db.Column(db.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return '{} {} {}'.format(self.id, self.name, self.updated_on)

    def comparator_unique_graph_record(self):
        return str(self.cpu_usage_percent) + str(self.memory_available_percent)

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