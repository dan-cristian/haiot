__author__ = 'dcristian'
import logging
import json
import sys
import socket
import datetime
import models
from common import constant, utils
from main import db
from sqlalchemy.exc import IntegrityError

def model_row_to_json(obj, operation=''):
    try:
        safe_obj = {}
        table_cols=obj._sa_class_manager
        for attr in table_cols:
            safe_obj[constant.JSON_PUBLISH_TABLE]=str(table_cols[attr]).split('.')[0]
            break
        safe_obj[constant.JSON_PUBLISH_RECORD_OPERATION]=operation
        safe_obj[constant.JSON_PUBLISH_SOURCE_HOST]=str(socket.gethostname())
        safe_obj[constant.JSON_PUBLISH_DATE]=str(datetime.datetime.now())
        safe_obj[constant.JSON_PUBLISH_TARGET_HOST]=constant.JSON_PUBLISH_VALUE_TARGET_HOST_ALL
        #removing infinite recursions and class noise
        #for attr in obj._sa_class_manager:
        for attr in dir(obj):
            if not attr.startswith('_') and not '(' in attr \
                    and attr != 'query' and not callable(getattr(obj, attr))\
                    and attr != 'metadata':
                value=getattr(obj, attr)
                if value: safe_obj[attr] = value
        return utils.obj2json(safe_obj)
    except Exception, ex:
        logging.critical('Error convert model obj to json, err {}'.format(ex))

def get_param(name):
    try:
        val = models.Parameter.query.filter_by(name=name).first().value
        return val
    except ValueError:
        logging.warning('Unable to get parameter {} error {}'.format(name, sys.exc_info()[0]))
        raise ValueError

def commit(session):
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        logging.warning('Unable to commit DB session {}, rolled back'.format(session))


def get_mod_name(module):
    return str(module).split("'")[1]

def populate_tables():
    if len(models.Parameter.query.all()) < 3:
        logging.info('Populating Parameter with default values')
        db.session.add(models.Parameter('', constant.P_MZP_SERVER_URL, 'http://192.168.0.10'))
        commit(db.session)
        db.session.add(models.Parameter('', constant.P_OWSERVER_HOST_1, '192.168.0.113'))
        commit(db.session)
        db.session.add(models.Parameter('', constant.P_OWSERVER_PORT_1, '4304'))
        commit(db.session)
        db.session.add(models.Parameter('', constant.P_MQTT_HOST, '192.168.0.9'))
        commit(db.session)
        db.session.add(models.Parameter('', constant.P_MQTT_PORT, '1883'))
        commit(db.session)
        db.session.add(models.Parameter('', constant.P_MQTT_TOPIC, 'iot/main'))
        commit(db.session)
        db.session.add(models.Parameter('', constant.P_PLOTLY_USERNAME, 'dancri77'))
        commit(db.session)
        db.session.add(models.Parameter('', constant.P_PLOTLY_APIKEY, 'lw2w6fz9xk'))
        commit(db.session)


    if len(models.Node.query.all()) == 0:
        logging.info('Populating Node with default values')
        db.session.add(models.Node(1, 'localhost', '127.0.0.1', has_sensor=True, sensor_port=4304))
        commit(db.session)

    if len(models.Sensor.query.all()) == 0:
        logging.info('Populating Sensor with a test value')
        sens = models.Sensor(address='ADDRESSTEST')
        #db.session.add(models.Sensor(0, address='ADDRESSTEST'))
        db.session.add(sens)
        commit(db.session)


    import alarm, heat, sensor, relay, mqtt_io, health_monitor, graph_plotly
    if len(models.Module.query.all()) < 7:
        logging.info('Populating Module with default values')
        db.session.add(models.Module(1, get_mod_name(health_monitor), True, 1))
        commit(db.session)
        db.session.add(models.Module(2, get_mod_name(mqtt_io), True, 2))
        commit(db.session)
        db.session.add(models.Module(3, get_mod_name(sensor), True, 3))
        commit(db.session)
        db.session.add(models.Module(4, get_mod_name(relay), False, 4))
        commit(db.session)
        db.session.add(models.Module(5, get_mod_name(heat), True, 5))
        commit(db.session)
        db.session.add(models.Module(6, get_mod_name(alarm), False, 6))
        commit(db.session)
        db.session.add(models.Module(7, get_mod_name(graph_plotly), True, 7))
        commit(db.session)