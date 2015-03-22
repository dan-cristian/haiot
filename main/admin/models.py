from datetime import datetime

from flask_sqlalchemy import SQLAlchemy #workaround for resolve issue
from main import db

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


class Sensor(db.Model):
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
    save_to_graph = db.Column(db.Boolean, default=False)

    @staticmethod
    def graph_x_():
        return 'updated_on'
    @staticmethod
    def graph_y_():
        fields = ["temperature", "humidity"]
        return fields
    @staticmethod
    def graph_id_():
        return 'address'
    @staticmethod
    def graph_legend_():
        return 'sensor_name'

    graph_x_ = graph_x_.__func__()
    graph_y_ = graph_y_.__func__()
    graph_id_ = graph_id_.__func__()
    graph_legend_ = graph_legend_.__func__()

    def __init__(self, id='', address=''):
        if id:
            self.id = id
        self.address= address
        self.save_to_graph = False

    def __repr__(self):
        return 'Sensor {}, {}{}'.format(self.type, self.sensor_name, self.address)
    
    def comparator(self):
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

class Node(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    ip = db.Column(db.String(15), nullable=False)
    has_sensor = db.Column(db.Boolean)
    sensor_port = db.Column(db.Integer)
    has_alarm = db.Column(db.Boolean)
    has_relay = db.Column(db.Boolean)

    def __init__(self, id='', name ='', ip='', has_sensor=False, sensor_port=''):
        if id:
            self.id = id
        self.name = name
        self.ip = ip
        self.has_sensor = has_sensor
        self.sensor_port = sensor_port

    def __repr__(self):
        return 'Node {} ip {}'.format(self.name,  self.ip)

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
