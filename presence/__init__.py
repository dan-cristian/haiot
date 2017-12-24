from main.logger_helper import Log
from pydispatch import dispatcher
from main import thread_pool
from main.admin import models
from common import Constant, utils
import presence_bt
import presence_wifi

__author__ = 'Dan Cristian<dan.cristian@gmail.com>'
initialised = False


def record_update(json=''):
    # Log.logger.info('Got presence update')
    models.Presence().json_to_record_query(json_obj=json)


def handle_event_presence_io(gpio_pin_code='', direction='', pin_value='', pin_connected=None):
    try:
        # Log.logger.info('Presence got event pin {} connected={}'.format(gpio_pin_code, pin_connected))
        # skip too many updates, only capture when contact is not connected (for PIR sensors this is alarm)

        #if not pin_connected:
        zonealarm = models.ZoneAlarm().query_filter_first(
            models.ZoneAlarm.gpio_host_name.in_([Constant.HOST_NAME]),
            models.ZoneAlarm.gpio_pin_code.in_([gpio_pin_code]))
        # zone_id = None
        # fixme: for now zonealarm holds gpio to zone mapping, should be made more generic
        if zonealarm is not None:
            zone_id = zonealarm.zone_id
            if zone_id is not None:
                zone = models.Zone().query_filter_first(models.Zone.id == zone_id)
                if zone is not None:
                    zone_name = zone.name
                else:
                    Log.logger.warning("Zone not found for presence zoneid={}".format(zone_id))
                    zone_name = "zone_name not found"
                current_record = models.Presence().query_filter_first(models.Presence.zone_id == zone_id)
                record = models.Presence()
                record.event_type = zonealarm.sensor_type
                record.zone_id = zone_id
                record.zone_name = zone_name
                # record.event_io_date = utils.get_base_location_now_date()
                record.sensor_name = zonealarm.alarm_pin_name
                record.is_connected = pin_connected
                # Log.logger.info('Presence saving sensor {}'.format(record.sensor_name))
                record.save_changed_fields(current_record=current_record, new_record=record,
                                           notify_transport_enabled=True, save_to_graph=True,
                                           save_all_fields=True)
            else:
                Log.logger.warning('Unable to find presence zone for pin {} in Alarm table'.format(gpio_pin_code))
    except Exception, ex:
        Log.logger.critical("Unable to save presence, er={}".format(ex), exc_info=True)


def handle_event_presence_cam(zone_name, cam_name, has_move):
    Log.logger.debug("Got cam event zone {} cam {} move={}".format(zone_name, cam_name, has_move))
    zone = models.Zone().query_filter_first(models.Zone.name == zone_name)
    if zone is not None:
        current_record = models.Presence().query_filter_first(models.Presence.zone_id == zone.id)
        record = models.Presence()
        record.event_type = Constant.PRESENCE_TYPE_CAM
        record.zone_id = zone.id
        record.zone_name = zone_name
        # record.event_camera_date = utils.get_base_location_now_date()
        record.sensor_name = cam_name
        record.is_connected = bool(int(has_move))
        Log.logger.debug("Saving cam event zone {} sensor {} is_conn={} record={}".format(
            record.zone_name, record.sensor_name, record.is_connected, record))
        record.save_changed_fields(current_record=current_record, new_record=record,
                                   notify_transport_enabled=True, save_to_graph=True,
                                   save_all_fields=True)
    else:
        Log.logger.warning('Unable to find presence zone for camera zone {}'.format(zone_name))


def unload():
    Log.logger.info('Presence module unloading')
    # ...
    thread_pool.remove_callable(presence_bt.thread_run)
    global initialised
    initialised = False


def init():
    Log.logger.debug('Presence module initialising')
    #thread_pool.add_interval_callable(presence_bt.thread_run, run_interval_second=20)
    thread_pool.add_interval_callable(presence_wifi.thread_run, run_interval_second=20)
    dispatcher.connect(handle_event_presence_io, signal=Constant.SIGNAL_GPIO, sender=dispatcher.Any)
    dispatcher.connect(handle_event_presence_cam, signal=Constant.SIGNAL_CAMERA, sender=dispatcher.Any)
    # handle_event_presence(gpio_pin_code='66')
    global initialised
    initialised = True


if __name__ == '__main__':
    presence_bt.thread_run()
