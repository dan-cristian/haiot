__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

from main import logger
from main.admin import models
from main.admin.cron import sched

#two types of rules are supported:
#1: cron based rules
#https://apscheduler.readthedocs.org/en/v2.1.2/cronschedule.html
#2: value changed rules, first obj parameter is mandatory

def rule_node(obj = models.Node(), field_changed_list = []):
    return 'rule node ok'

#min & max temperatures
def rule_sensor_temp_target(obj = models.Sensor(), field_changed_list = []):
    temp = obj.temperature
    return 'rule temp ok'

@sched.scheduled_job('cron', day='*', hour='*', minute='*/2')
def rule_water_front_on():
    logger.info('water on')

@sched.scheduled_job('cron', day='*', hour='*', minute='*/3')
def rule_water_front_off():
    logger.info('water off')
