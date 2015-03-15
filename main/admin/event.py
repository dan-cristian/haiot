from pydispatch import dispatcher
import common.constant
import models

from main import db

def handle_event_sensor( sender ):
    print "Signal was sent by ", sender
    sensor = models.Sensor.query.get(sender.address)
    if sensor==None:
        sensor = models.Sensor(sender)
        db.session.add(sensor)
    else:
        sensor.update(sender)
    db.session.commit()

def init():
    dispatcher.connect(handle_event_sensor, signal=common.constant.SIGNAL_SENSOR, sender=dispatcher.Any)