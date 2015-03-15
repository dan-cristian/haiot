from datetime import datetime

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

class Zone(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    def __init__(self, id='', name=''):
        if id:
            self.id= id
        self.name= name

    def __repr__(self):
        return '<Zone: id {}, {}>'.format(self.id, self.name[:20])

class SchedulePattern(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    pattern = db.Column(db.String(24))
    def __init__(self, id='', name=''):
        if id:
            self.id= id
        self.name= name
    def __repr__(self):
        return self.name[:24]


class HeatSchedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    zone_id = db.Column(db.Integer, db.ForeignKey('zone.id'))
    zone = db.relationship('Zone', backref=db.backref('zone', lazy='dynamic'))
    pattern_id = db.Column(db.Integer, db.ForeignKey('schedule_pattern.id'))
    pattern = db.relationship('SchedulePattern', backref=db.backref('schedule_pattern', lazy='dynamic'))
    is_week = db.Column(db.Boolean)
    is_weekend = db.Column(db.Boolean)

    def __repr__(self):
        return '<Zone {}, Pattern {}>'.format(self.zone.name, self.pattern.name)

import sensors

class Sensor(db.Model):
    id = db.Column(db.String(50), primary_key=True)
    type=db.Column(db.String(50))
    temperature=db.Column(db.Float)
    humidity=db.Column(db.Float)
    counter_a=db.Column(db.BigInteger)
    counter_b=db.Column(db.BigInteger)

    def update(self, sensor):
        assert isinstance(sensor, sensors.Sensor)
        self.id= sensor.address
        self.type = sensor.type
        self.temperature = sensor.temperature
        self.humidity = sensor.humidity
        self.counter_a=sensor.counters_A
        self.counter_b=sensor.counters_B
    def __init__(self, sensor):
        self.update(sensor)
    def __repr__(self):
        return self.id