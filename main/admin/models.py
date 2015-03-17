from datetime import datetime

from main import db
from sensor.owsensor_loop import SensorOw


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

    def __init__(self, id='', name=''):
        if id:
            self.id = id
        self.name = name

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
    zone = db.relationship('Zone', backref=db.backref('zone', lazy='dynamic'))
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
    counter_a = db.Column(db.BigInteger)
    counter_b = db.Column(db.BigInteger)
    updated_on = db.Column(db.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow)

    def update(self, sensor):
        assert isinstance(sensor, SensorOw)
        self.address = sensor.address
        self.type = sensor.type
        self.temperature = sensor.temperature
        self.humidity = sensor.humidity
        self.counter_a = sensor.counters_A
        self.counter_b = sensor.counters_B

    def __init__(self, sensor):
        self.update(sensor)

    def __repr__(self):
        return 'Sensor id {}, {}'.format(self.id, self.type)


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