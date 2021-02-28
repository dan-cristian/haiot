import sys
from pydispatch import dispatcher
import threading
import prctl
from main.logger_helper import L
from main import thread_pool
from common import Constant
from main import general_init
from storage.model import m

class P:
    mqtt_event_list = []
    mqtt_lock = threading.Lock()

    def __init__(self):
        pass


def _handle_internal_event(obj):
    obj['is_event_external'] = False
    P.mqtt_event_list.append(obj)


# executed on every mqqt message received (except those sent by this host)
def handle_event_mqtt_received(obj):
    P.mqtt_event_list.append(obj)


# runs periodically and executes received mqqt messages from queue
def _process_obj(obj):
    try:
        prctl.set_name("event_thread_run")
        threading.current_thread().name = "event_thread_run"
        # events received via mqtt transport
        if Constant.JSON_PUBLISH_SOURCE_HOST in obj:
            source_host = obj[Constant.JSON_PUBLISH_SOURCE_HOST]
        elif Constant.JSON_PUBLISH_SRC_HOST in obj:
            source_host = obj[Constant.JSON_PUBLISH_SRC_HOST]
        else:
            L.l.error('Cannot process without mandatory field source_host')
            return
        obj[Constant.JSON_PUBLISH_SRC_HOST] = source_host
        if source_host != Constant.HOST_NAME:
            if Constant.JSON_PUBLISH_TABLE in obj:
                table = str(obj[Constant.JSON_PUBLISH_TABLE])
                # cls = getattr(sys.modules[tinydb_model.__name__], table)
                cls = getattr(m, table)
                # if cls._is_used_in_module:
                if ('Pwm' in table or 'ZoneCustomRelay' in table or 'Ventilation' in table) and (
                        Constant.HOST_NAME == 'pizero1' or Constant.HOST_NAME == 'netbook'):
                    L.l.info('Got mqtt {}'.format(obj))
                cls.save(obj)
                # else:
                #    L.l.info('Ignoring save for {}'.format(cls.__name__))
                #   pass
        else:
            L.l.error('mqtt message sent from me to me!')
    except Exception as ex:
        L.l.error("Error processing event err={}, mqtt={}".format(ex, obj), exc_info=True)


def mqtt_thread_run():
    prctl.set_name("mqtt_thread_run")
    threading.current_thread().name = "mqtt_thread_run"
    P.mqtt_lock.acquire()
    try:
        last_count = len(P.mqtt_event_list)
        for obj in list(P.mqtt_event_list):
            P.mqtt_event_list.remove(obj)
            _process_obj(obj)
            if len(P.mqtt_event_list) > last_count:
                L.l.debug('Not keeping up with {} mqtt events'.format(len(P.mqtt_event_list)))
            if general_init.P.shutting_down is True:
                break
    except Exception as ex:
        L.l.error("General error processing mqtt: {}".format(ex), exc_info=True)
    finally:
        P.mqtt_lock.release()
        prctl.set_name("idle_thread_run")
        threading.current_thread().name = "idle_thread_run"


# http://pydispatcher.sourceforge.net/
def init():
    # dispatcher.connect(handle_local_event_db_post, signal=Constant.SIGNAL_UI_DB_POST, sender=dispatcher.Any)
    dispatcher.connect(handle_event_mqtt_received, signal=Constant.SIGNAL_MQTT_RECEIVED, sender=dispatcher.Any)
    thread_pool.add_interval_callable(mqtt_thread_run, run_interval_second=0.5)
