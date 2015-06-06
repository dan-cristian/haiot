__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

from main import logger
from main.admin import models

def rule_node(obj = models.Node(), field_changed_list = []):
    return 'rule node ok'

#min & max temperatures
def rule_sensor_temp_target(obj = models.Sensor(), field_changed_list = []):
    temp = obj.temperature
    return 'rule temp ok'

