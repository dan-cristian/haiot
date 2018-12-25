from main.logger_helper import L
from main import thread_pool
from pydispatch import dispatcher
from common import Constant
from main.admin import model_helper
from inspect import getmembers, isfunction
from transport import mqtt_io
import rules
import threading
import prctl
from music import mpd
from cloud import lastfm

__author__ = 'Dan Cristian<dan.cristian@gmail.com>'


class P:
    event_list = []
    func_list = None
    initialised = False
    mqtt_topic_receive = None
    mqtt_topic_receive_prefix = None

    def __init__(self):
        pass


# empty
class Obj:
    def __init__(self):
        pass


def parse_rules(obj, change):
    """ running rule method corresponding with obj type """
    # executed on all db value changes
    L.l.debug('Received openhab obj={} change={} for rule parsing'.format(obj, change))
    try:
        # extract only changed fields
        if hasattr(obj, Constant.JSON_PUBLISH_FIELDS_CHANGED):
            field_changed_list = obj.last_commit_field_changed_list
        else:
            field_changed_list = []
        if P.func_list:
            for func in P.func_list:
                if func[1].func_defaults and len(func[1].func_defaults) > 0:
                    first_param = func[1].func_defaults[0]
                    # calling rule methods with first param type equal to passed object type
                    if type(obj) == type(first_param):
                        record = Obj()
                        for attr, value in obj.__dict__.iteritems():
                            setattr(record, attr, value)
                        P.event_list.append([record, func[0], field_changed_list])
                        # optimise CPU, but ensure each function name is unique in rule file
                        break
    except Exception as ex:
        L.l.exception('Error parsing openhab rules, ex={}'.format(ex))


def mqtt_on_message(client, userdata, msg):
    item = msg.topic.split(P.mqtt_topic_receive_prefix)
    payload = msg.payload.lower()
    if len(item) == 2:
        name = item[1]
        switch_state = None
        if payload == 'on':
            switch_state = 1
        elif payload == 'off':
            switch_state = 0
        if name.startswith("relay_"):
            vals = name.split("relay_")
            rules.custom_relay(vals[1], switch_state)
        elif name.startswith("heat_"):
            vals = name.split("heat_")
            rules.heat_relay(vals[1], switch_state)
        elif name.startswith("mpd_"):
            vals = name.split("mpd_")
            items = vals[1].split('_')
            if len(items) >= 2:
                zone_name = items[1]
            else:
                zone_name = None
            cmd = False
            if items[0] == 'volume':
                mpd.set_volume(zone_name=zone_name, volume=int(payload))
                cmd = True
            elif items[0] == 'position':
                mpd.set_position(zone_name=zone_name, position_percent=float(payload))
                cmd = True
            elif items[0] == 'player' or items[0] == 'state':
                if payload == 'up':
                    mpd.previous_song(zone_name)
                    cmd = True
                elif payload == 'down':
                    mpd.next_song(zone_name=zone_name)
                    cmd = True
                elif payload == 'stop' or payload == 'toggle':
                    mpd.toggle_state(zone_name=zone_name)
                    cmd = True
                elif payload == 'play':
                    mpd.play(zone_name=zone_name)
                    cmd = True
            elif items[0] == 'lastfmloved':
                lastfm.set_current_loved(loved=(switch_state == 1))
                cmd = True
            if cmd:
                mpd.update_state(zone_name=zone_name)
                mpd.save_lastfm()
            else:
                L.l.warning('Undefined mpd command {}'.format(msg.topic))
    else:
        L.l.warning("Unexpected mqtt receive topic {} payload={}".format(msg.topic, msg.payload))


def __load_rules():
    try:
        # load all function entries from hardcoded rule script
        P.func_list = getmembers(rules, isfunction)
    except Exception as ex:
        L.l.exception('Error adding rules into db {}'.format(ex), exc_info=1)


def thread_run():
    prctl.set_name("openhab")
    threading.current_thread().name = "openhab"
    for obj in list(P.event_list):
        try:
            result = getattr(rules, obj[1])(obj=obj[0], field_changed_list=obj[2])
            L.l.debug('Rule returned {}'.format(result))
            P.event_list.remove(obj)
        except Exception as ex:
            L.l.critical("Error processing openhab rule err={}".format(ex), exc_info=1)
    prctl.set_name("idle")
    threading.current_thread().name = "idle"


def unload():
    L.l.info('Openhab module unloading')
    thread_pool.remove_callable(thread_run)
    P.initialised = False


def init():
    L.l.info('Openhab module initialising')
    rules.P.openhab_topic = str(model_helper.get_param(Constant.P_MQTT_TOPIC_OPENHAB_SEND))
    P.mqtt_topic_receive = str(model_helper.get_param(Constant.P_MQTT_TOPIC_OPENHAB_RECEIVE))
    P.mqtt_topic_receive_prefix = P.mqtt_topic_receive.replace('#', '')
    mqtt_io.P.mqtt_client.message_callback_add(P.mqtt_topic_receive, mqtt_on_message)
    __load_rules()
    thread_pool.add_interval_callable(thread_run, run_interval_second=1)
    dispatcher.connect(parse_rules, signal=Constant.SIGNAL_DB_CHANGE_FOR_RULES, sender=dispatcher.Any)
    P.initialised = True
