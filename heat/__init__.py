__author__ = 'dcristian'

from pydispatch import dispatcher
import heat_loop
import logging
from main.admin import thread_pool
from main.admin import models, db
from common import constant, utils
import relay

initialised=False

def heat_update(obj={}):
    try:
        source_host_name = utils.get_object_field_value(obj, 'name')
        logging.debug('Received heat relay state update from {}'.format(source_host_name))
        zone_id = utils.get_object_field_value(obj, 'zone_id')
        zone_heat_relay = models.ZoneHeatRelay.query.filter_by(zone_id=zone_id).first()
        if zone_heat_relay and zone_heat_relay.gpio_host_name == constant.HOST_NAME:
            cmd_heat_is_on = utils.get_object_field_value(obj, 'heat_is_on')
            if cmd_heat_is_on != zone_heat_relay.heat_is_on:
                logging.info('Local heat state zone_id {} must be changed to {}'.format(zone_id, cmd_heat_is_on))
                pin_state = relay.relay_update(zone_heat_relay.gpio_pin_code, cmd_heat_is_on)
                if pin_state == cmd_heat_is_on:
                    zone_heat_relay.heat_is_on = pin_state
                    zone_heat_relay.notify_transport_enabled = False
                    db.session.commit()
                else:
                    logging.warning('Heat state zone_id {} unexpected value {} after set'.format(zone_id, pin_state))
            else:
                logging.debug('No change needed in heat state')
        else:
            logging.debug('Ignoring heat change, not owning the zone relay pin on this host')
    except Exception, ex:
        logging.warning('Error updating heat relay state, err {}'.format(ex))

def handle_event_heat(zone='', heat_is_on=''):
    assert isinstance(zone, models.Zone)

    pass

def unload():
    logging.info('Heat module unloading')
    global initialised
    initialised = False
    thread_pool.remove_callable(heat_loop.thread_run)
    dispatcher.disconnect(handle_event_heat,signal=constant.SIGNAL_HEAT,sender=dispatcher.Any)

def init():
    logging.info('Heat module initialising')
    dispatcher.connect(handle_event_heat, signal=constant.SIGNAL_HEAT, sender=dispatcher.Any)
    thread_pool.add_callable(heat_loop.thread_run, 30)
    global initialised
    initialised = True
