__author__ = 'dcristian'
import logging
import models
from common import constant
from main import db
from sqlalchemy.exc import IntegrityError

def get_param(name):
    try:
        val = models.Parameter.query.filter_by(name=name).first().value
        return val
    except:
        logging.warning('Unable to get parameter ' + name)

def commit(session):
    try:
        session.commit()
    except IntegrityError:
        session.rollback()


def get_mod_name(module):
    return str(module).split("'")[1]

def populate_tables():
    if len(models.Parameter.query.all()) < 3:
        logging.info('Populating Parameter with default values')
        db.session.add(models.Parameter(1, constant.PARAM_MZP_SERVER_URL, 'http://192.168.0.10'))
        commit(db.session)
        db.session.add(models.Parameter(2, constant.PARAM_OWSERVER_HOST_1, '192.168.0.113'))
        commit(db.session)
        db.session.add(models.Parameter(3, constant.PARAM_MQTT_HOST, '192.168.0.9'))
        commit(db.session)
        db.session.add(models.Parameter(4, constant.PARAM_MQTT_PORT, '1883'))
        commit(db.session)

    if len(models.Node.query.all()) == 0:
        logging.info('Populating Node with default values')
        db.session.add(models.Node(1, 'localhost', '127.0.0.1', has_sensor=True, sensor_port=4304))
        commit(db.session)



    import alarm, heat, sensor, relay, mqtt_publisher, health_monitor
    if len(models.Module.query.all()) == 0:
        logging.info('Populating Module with default values')
        db.session.add(models.Module(1, get_mod_name(health_monitor), True, 1))
        commit(db.session)
        db.session.add(models.Module(2, get_mod_name(mqtt_publisher), False, 2))
        commit(db.session)
        db.session.add(models.Module(3, get_mod_name(sensor), False, 3))
        commit(db.session)
        db.session.add(models.Module(4, get_mod_name(relay), False, 4))
        commit(db.session)
        db.session.add(models.Module(5, get_mod_name(heat), False, 5))
        commit(db.session)
        db.session.add(models.Module(6, get_mod_name(alarm), False, 6))
        commit(db.session)
