__author__ = 'dcristian'
from pydispatch import dispatcher

from main.logger_helper import Log
from main.admin import models
#import alarm_loop
from main import thread_pool
from common import Constant, utils
from main.admin.model_helper import commit

initialised=False


def handle_event_alarm(gpio_pin_code='', direction='', pin_value='', pin_connected=None):
    zonealarm= models.ZoneAlarm.query.filter_by(gpio_pin_code=gpio_pin_code).first()
    if zonealarm:
        Log.logger.info('Got alarm event zoneid={} pin_connected={} pin_value={}'.format(
            zonealarm.zone_id, pin_connected, pin_value))
        zonealarm.alarm_status = pin_value
        zonealarm.updated_on = utils.get_base_location_now_date()
        zonealarm.notify_transport_enabled= False
        commit()
    else:
        Log.logger.warning('Unexpected mising zone alarm for gpio code {}'.format(gpio_pin_code))


def unload():
    Log.logger.info('Alarm module unloading')
    global initialised
    dispatcher.disconnect(dispatcher.connect(handle_event_alarm, signal=Constant.SIGNAL_GPIO, sender=dispatcher.Any))
    #thread_pool.remove_callable(alarm_loop.thread_run)
    initialised = False


def init():
    Log.logger.info('Alarm module initialising')
    #alarm_loop.init()
    #thread_pool.add_interval_callable(alarm_loop.thread_run)
    dispatcher.connect(handle_event_alarm, signal=Constant.SIGNAL_GPIO, sender=dispatcher.Any)
    # get list of input gpio ports and communicate them to gpio modules for proper port setup as "IN"
    port_list = []
    local_alarms = models.ZoneAlarm().query_filter_all(models.ZoneAlarm.gpio_host_name.in_([Constant.HOST_NAME]))
    for alarm in local_alarms:
        gpio_pin = models.GpioPin().query_filter_first(models.GpioPin.pin_code.in_([alarm.gpio_pin_code]),
                                                     models.GpioPin.host_name.in_([Constant.HOST_NAME]))
        if gpio_pin:
            Log.logger.info('Schedule setup alarm port pin={} type={}'.format(gpio_pin.pin_code, gpio_pin.pin_type))
            port_list.append(gpio_pin)
        else:
            Log.logger.warning('Unexpected empty gpio pin response for alarm setup')
    dispatcher.send(signal=Constant.SIGNAL_GPIO_INPUT_PORT_LIST, gpio_pin_list=port_list)
    global initialised
    initialised = True
