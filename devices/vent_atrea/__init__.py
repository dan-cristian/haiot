import threading
import prctl
from main.logger_helper import L
from main import thread_pool
from common import utils, get_json_param, Constant, get_secure_general
from storage.model import m

__author__ = 'Dan Cristian<dan.cristian@gmail.com>'


class P:
    initialised = False
    # response: <root lng="2">47040</root>
    auth_url = "/config/login.cgi?magic=<magic>"
    auth_resp_start = '<root lng="2">'
    auth_resp_end = '</root>'
    auth_key = None

    state_url = "/config/xml.xml?auth=<key>"
    mode_url = "/config/xml.cgi?auth=<key>&H107090000X"
    power_level_set_url = "/config/xml.cgi?auth=<key>&H1070800XXX"

    mode_resp_start = '<O I="H10709" V="'
    mode_resp_end = '"/'

    power_level_resp_start = '<O I="H10708" V="'
    power_level_resp_end = '"/'

    mode_values = {0: "off", 1: "automatic", 2: "ventilation", 3: "circulation + ventilation", 4: "circulation",
                   5: "precooling", 6: "disbalance", 7: "overpressure"}

    mode_off = 0
    mode_default = 2

    power_level_min = 12
    power_level_default = 35
    power_level_max = 65

    def __init__(self):
        pass


def auth():
    server_url = get_json_param(Constant.P_ATREA_LOCAL_URL) + P.auth_url
    server_url = server_url.replace("<magic>", get_secure_general("magic_atrea"))
    key = utils.parse_http(server_url, P.auth_resp_start, P.auth_resp_end)
    if key is not None and len(key) == 5:
        P.auth_key = key
        L.l.info("Got Atrea auth key: {}".format(key))
    else:
        L.l.warning("Unable to get Atrea auth key, response was:{}".format(key))


def keep_alive():
    if P.auth_key is None:
        auth()
    if P.auth_key is not None:
        server_url = get_json_param(Constant.P_ATREA_LOCAL_URL) + P.state_url
        state_text = utils.get_url_content(server_url.replace("<key>", P.auth_key))
        if "HTTP: 403 Forbidden AUTH" in state_text:
            auth()
        else:
            try:
                mode = int(utils.parse_text_ex(state_text, P.mode_resp_start, P.mode_resp_end))
                power_level = int(utils.parse_text_ex(state_text, P.power_level_resp_start, P.power_level_resp_end))
                rec = m.Ventilation.find_one({m.Ventilation.id: 0})
                rec.mode = mode
                rec.power_level = power_level
                rec.save_changed_fields(persist=True)
                L.l.info("Atrea mode={}-{} power={}".format(mode, P.mode_values[mode], power_level))
            except Exception as ex:
                L.l.warning("Unexpected Atrea state response: {}".format(state_text))
    else:
        L.l.warning("Unable to get auth key")


def set_mode(mode):
    L.l.info("Setting ventilation mode to {}".format(mode))
    server_url = get_json_param(Constant.P_ATREA_LOCAL_URL) + P.mode_url
    server_url = server_url.replace("X", str(mode))
    if P.auth_key is not None:
        state_text = utils.get_url_content(server_url.replace("<key>", P.auth_key))
        L.l.info("Setting ventilation mode to {} returned {}".format(mode, state_text))
    else:
        L.l.info("Failed setting ventilation mode, not authenticated")


def set_power_level(level):
    if level <= P.power_level_max:
        L.l.info("Setting ventilation power level to {}".format(level))
        server_url = get_json_param(Constant.P_ATREA_LOCAL_URL) + P.power_level_set_url
        level_text = f'{level:03}'
        server_url = server_url.replace("XXX", level_text)
        if P.auth_key is not None:
            state_text = utils.get_url_content(server_url.replace("<key>", P.auth_key))
            L.l.info("Setting ventilation power level to {} returned {}".format(level, state_text))
        else:
            L.l.info("Failed setting ventilation power, not authenticated")
    else:
        L.l.info("Ignoring set power level {} as is higher than max {}".format(level, P.power_level_max))


def ventilation_upsert_listener(record, changed_fields):
    # L.l.info("RECEIVED ATREA {} changed={}".format(record, changed_fields))
    assert isinstance(record, m.Ventilation)
    if "mode" in changed_fields and record.mode is not None:
        set_mode(record.mode)
    if "power_level" in changed_fields and record.power_level is not None:
        set_power_level(record.power_level)


def thread_run():
    prctl.set_name("atrea")
    threading.current_thread().name = "atrea"
    keep_alive()
    prctl.set_name("idle")
    threading.current_thread().name = "idle"
    return 'Processed template_run'


def unload():
    L.l.info('Atrea Ventilation module unloading')
    thread_pool.remove_callable(thread_run)
    P.initialised = False


def init():
    L.l.info('Atrea Ventilation module initialising - DUPLEX RD5 380')
    thread_pool.add_interval_callable(thread_run, run_interval_second=30)
    m.Ventilation.add_upsert_listener(ventilation_upsert_listener)
    P.initialised = True
