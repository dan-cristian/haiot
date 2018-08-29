from main.logger_helper import L
from main import thread_pool
from pydispatch import dispatcher
from common import Constant
from main.admin import model_helper
from inspect import getmembers, isfunction
from transport import mqtt_io
import rules

__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

initialised = False


class P:
    event_list = []
    func_list = None


class Obj:
    pass


def parse_rules(obj, change):
    """ running rule method corresponding with obj type """
    # executed on all db value changes
    L.l.debug('Received openhab obj={} change={} for rule parsing'.format(obj, change))
    try:
        # extract only changed fields
        if hasattr(obj, 'last_commit_field_changed_list'):
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
    if "=" in msg.payload:
        vals = msg.payload.split("=")
        name = vals[0]
        value = vals[1]
        L.l.info("Got openhab event {}={}".format(name, value))
        if name.startswith("relay_"):
            vals = name.split("relay_")
            rules.custom_relay(vals[1], value)
        elif name.startswith("heat_"):
            vals = name.split("heat_")
            rules.heat_relay(vals[1], value)
    else:
        L.l.warning("Openhab payload does not contain = character, invalid payload={}".format(msg.payload))


def __load_rules():
    try:
        # load all function entries from hardcoded rule script
        P.func_list = getmembers(rules, isfunction)
    except Exception as ex:
        L.l.exception('Error adding rules into db {}'.format(ex), exc_info=1)


def thread_run():
    for obj in list(P.event_list):
        try:
            result = getattr(rules, obj[1])(obj=obj[0], field_changed_list=obj[2])
            L.l.debug('Rule returned {}'.format(result))
            P.event_list.remove(obj)
        except Exception as ex:
            L.l.critical("Error processing openhab rule err={}".format(ex), exc_info=1)


def unload():
    L.l.info('Openhab module unloading')
    thread_pool.remove_callable(thread_run)
    global initialised
    initialised = False


def init():
    L.l.info('Openhab module initialising')
    rules.P.openhab_topic = str(model_helper.get_param(Constant.P_MQTT_TOPIC_OPENHAB))
    mqtt_io.P.mqtt_client.message_callback_add(rules.P.openhab_topic, mqtt_on_message)
    __load_rules()
    thread_pool.add_interval_callable(thread_run, run_interval_second=1)
    dispatcher.connect(parse_rules, signal=Constant.SIGNAL_DB_CHANGE_FOR_RULES, sender=dispatcher.Any)
    global initialised
    initialised = True


