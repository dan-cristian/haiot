from pydispatch import dispatcher
import logging
import paho.mqtt.client as mqtt
import json
import common.constant
import common.utils
import models

from main import db

def handle_event_sensor(sender):
    #print "Signal was sent by ", sender
    sensor = models.Sensor.query.filter_by(address=sender.address).first()
    if sensor==None:
        sensor = models.Sensor(sender)
        db.session.add(sensor)
    else:
        sensor.update(sender)
    db.session.commit()

def handle_event_db_model_post(model, row):
    print 'Signal was sent by model {} row {}'.format(model, row)
    if str(models.Parameter) in str(model):
        logging.info('Detected Parameter change ' + row)
    elif str(models.Module) in str(model):
        logging.info('Detected Module change')


def init():
    #http://pydispatcher.sourceforge.net/
    dispatcher.connect(handle_event_sensor, signal=common.constant.SIGNAL_SENSOR, sender=dispatcher.Any)
    dispatcher.connect(handle_event_db_model_post, signal=common.constant.SIGNAL_SENSOR_DB_POST, sender=dispatcher.Any)