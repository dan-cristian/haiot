from main.logger_helper import L
from main import thread_pool
from pydispatch import dispatcher
from common import Constant, get_json_param
from inspect import getmembers, isfunction
from transport import mqtt_io
from cloud.openhab import rules
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
    if hasattr(obj, Constant.JSON_PUBLISH_SOURCE_HOST):
        source = getattr(obj, Constant.JSON_PUBLISH_SOURCE_HOST)
    elif hasattr(obj, Constant.JSON_PUBLISH_SRC_HOST):
        source = getattr(obj, Constant.JSON_PUBLISH_SRC_HOST)
    else:
        source = 'unknown'
    # process all changes from all hosts
    # if source == Constant.HOST_NAME or source is None:
    try:
        # extract only changed fields
        if hasattr(obj, Constant.JSON_PUBLISH_FIELDS_CHANGED):
            change = obj.last_commit_field_changed_list
        else:
            change = change
        if P.func_list:
            for func in P.func_list:
                if func[1].__defaults__ and len(func[1].__defaults__) > 0:
                    first_param = func[1].__defaults__[0]
                    # calling rule methods with first param type equal to passed object type
                    if type(obj) == type(first_param):
                        # record = Obj()
                        # for attr, value in obj.__dict__.items():
                        #    setattr(record, attr, value)
                        # P.event_list.append([record, func[0], change])
                        P.event_list.append([obj, func[0], change])
                        # optimise CPU, but ensure each function name is unique in rule file
                        break
    except Exception as ex:
        L.l.exception('Error parsing openhab rules, ex={}'.format(ex))


def mqtt_on_message(client, userdata, msg):
    try:
        item = msg.topic.split(P.mqtt_topic_receive_prefix)
        payload = msg.payload.decode('utf-8').lower()
        L.l.info('Got openhab mqtt {}={}'.format(msg.topic, payload))
        if len(item) == 2:
            name = item[1]
            switch_state = None
            if payload == 'on':
                switch_state = True
            elif payload == 'off':
                switch_state = False
            if name.startswith("relay_"):
                rules.custom_relay(name[len('relay_'):], switch_state)
            elif name.startswith("heat_"):
                rules.heat_relay(name[len('heat_'):], switch_state)
            elif name.startswith("thermo_target_"):
                temp = float(payload)
                rules.thermostat(zone_name=name[len('thermo_target_'):], temp_target=temp)
            elif name.startswith("thermo_state_"):
                rules.thermostat(zone_name=name[len('thermo_state_'):], state=switch_state)
            elif name.startswith("thermo_mode_manual_"):
                rules.thermostat(zone_name=name[len('thermo_mode_manual_'):], mode_manual=switch_state)
            elif name.startswith("thermo_mode_presence_"):
                rules.thermostat(zone_name=name[len('thermo_mode_presence_'):], mode_presence=switch_state)
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
    except Exception as ex:
        L.l.error('Error openhab mqtt {} ex={}'.format(msg.payload, ex), exc_info=True)


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
            result = getattr(rules, obj[1])(obj=obj[0], change=obj[2])
            L.l.debug('Rule returned {}'.format(result))
            P.event_list.remove(obj)
        except Exception as ex:
            L.l.critical("Error processing openhab rule err={} obj={}".format(ex, obj), exc_info=True)
    prctl.set_name("idle_openhab")
    threading.current_thread().name = "idle_openhab"


def unload():
    L.l.info('Openhab module unloading')
    thread_pool.remove_callable(thread_run)
    P.initialised = False


def init():
    L.l.info('Openhab module initialising')
    rules.P.openhab_topic = get_json_param(Constant.P_MQTT_TOPIC_OPENHAB_SEND)
    P.mqtt_topic_receive = get_json_param(Constant.P_MQTT_TOPIC_OPENHAB_RECEIVE)
    P.mqtt_topic_receive_prefix = P.mqtt_topic_receive.replace('#', '')
    mqtt_io.P.mqtt_client.message_callback_add(P.mqtt_topic_receive, mqtt_on_message)
    mqtt_io.add_message_callback(P.mqtt_topic_receive, mqtt_on_message)
    __load_rules()
    thread_pool.add_interval_callable(thread_run, run_interval_second=1)
    dispatcher.connect(parse_rules, signal=Constant.SIGNAL_DB_CHANGE_FOR_RULES, sender=dispatcher.Any)
    P.initialised = True
