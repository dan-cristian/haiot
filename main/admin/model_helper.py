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

def populate_tables():
    if len(models.Parameter.query.all()) < 3:
        logging.info('Populating Parameter with default values')
        db.session.add(models.Parameter(1, constant.PARAM_MZP_SERVER_URL, 'http://192.168.0.10'))
        commit(db.session)
        db.session.add(models.Parameter(2, constant.PARAM_OWSERVER_HOST_1, '192.168.0.113'))
        commit(db.session)
        db.session.add(models.Parameter(3, constant.PARAM_MQTT_HOST, '192.168.0.9'))
        commit(db.session)
