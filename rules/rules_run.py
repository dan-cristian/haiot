__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

import time
from flask import url_for, redirect
from main import logger, app
from main.admin import models
from main.admin.thread_pool import do_job
from rules import scheduler

#two types of rules are supported:
#1: cron based rules
#https://apscheduler.readthedocs.org/en/v2.1.2/cronschedule.html
#2: value changed rules, first obj parameter is mandatory

####### VALUE TRIGGER RULES ########
def rule_node(obj = models.Node(), field_changed_list = []):
    return 'rule node ok'

#min & max temperatures
def rule_sensor_temp_target(obj = models.Sensor(), field_changed_list = []):
    temp = obj.temperature
    return 'rule temp ok'

######## CRON RULES ################
@scheduler.scheduled_job('cron', day='*', hour='*', minute='*', second='*/5')
def rule_water_front_on(): do_job(water_front_on)

@scheduler.scheduled_job('cron', day='*', hour='*', minute='*/2', second='*/30')
def rule_water_front_off(): do_job(water_front_off)


###### JOBS executed asyncronously via a thread pool ######

def water_front_on():
    logger.info('water on')
    with app.test_client() as c:
        msg = c.get('/apiv1/relay/get?pin=1').data
        logger.info(msg)
    #with app.test_request_context():
    #    logger.info(redirect('/apiv1/relay/get'))
    # start the pump
    # open valve


def water_front_off():
    logger.info('water off')
    # close the valve
    # let the pump build some pressure
    time.sleep(10)
    # pump off if no other zone is on?

