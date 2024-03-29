import os
import threading
import prctl
from datetime import datetime
from main.logger_helper import L
from common import Constant, variable
from main import thread_pool
import time
import six
from pydispatch import dispatcher as haiot_dispatch
from storage.model import m


class P:
    network = None
    module_imported = False
    inclusion_started = False
    initialised = False
    thread_run_at_init = False  # was thread run first at init?
    interval = 5
    init_fail_count = 0
    device = "/dev/ttyACM"
    device_index = 0
    log_file = "OZW_Log.log"
    last_value_received = datetime.max
    MAX_SILENCE_SEC = 120
    init_done = False
    DELTA_SAVE_SECONDS = 30
    MAX_SENSOR_POWER_WATTS = 30000  # cap faulty readings
    MAX_SENSOR_VOLTAGE = 1000 # cap faulty readings
    MAX_POWER_FACTOR = 1 # cap faulty readings

    def __init__(self):
        pass


import openzwave
if six.PY3:
    from pydispatch import dispatcher
else:
    from louie import dispatcher
from openzwave.node import ZWaveNode
from openzwave.value import ZWaveValue
from openzwave.scene import ZWaveScene
from openzwave.controller import ZWaveController
from openzwave.network import ZWaveNetwork
from openzwave.option import ZWaveOption
from openzwave.object import ZWaveException
P.module_imported = True
#except Exception as e:
#    L.l.info("Cannot import openzwave")
#    traceback.print_exc(file=sys.stdout)


# http://openzwave.github.io/python-openzwave/network.html
def louie_network_started(network):
    print('Louie signal: OpenZWave network started: homeid {:08x} - {} nodes found.'.format(
        network.home_id, network.nodes_count))


def louie_network_failed(network):
    L.l.info('Louie signal: OpenZWave network failed.')


def louie_network_resetted(network):
    L.l.info('Louie signal: OpenZWave network is resetted.')


# https://raw.githubusercontent.com/OpenZWave/python-openzwave/master/examples/api_demo.py
def louie_network_ready(network):
    L.l.info('Louie signal: ZWave network is ready : {} nodes were found.'.format(network.nodes_count))
    L.l.info('Louie signal: Controller : {}'.format(network.controller))
    dispatcher.connect(louie_node_update, ZWaveNetwork.SIGNAL_NODE)
    # dispatcher.connect(louie_value, ZWaveNetwork.SIGNAL_VALUE)
    dispatcher.connect(louie_value_refreshed, ZWaveNetwork.SIGNAL_VALUE_REFRESHED)
    dispatcher.connect(louie_value_added, ZWaveNetwork.SIGNAL_VALUE_ADDED)
    dispatcher.connect(louie_value_changed, ZWaveNetwork.SIGNAL_VALUE_CHANGED)
    dispatcher.connect(louie_value_removed, ZWaveNetwork.SIGNAL_VALUE_REMOVED)
    dispatcher.connect(louie_ctrl_message, ZWaveController.SIGNAL_CONTROLLER)
    dispatcher.connect(louie_button_on, ZWaveNetwork.SIGNAL_BUTTON_ON)
    dispatcher.connect(louie_button_off, ZWaveNetwork.SIGNAL_BUTTON_OFF)
    dispatcher.connect(louie_node_event, ZWaveNetwork.SIGNAL_NODE_EVENT)
    dispatcher.connect(louie_node_event, ZWaveNetwork.SIGNAL_NODE_ADDED)
    dispatcher.connect(louie_node_event, ZWaveNetwork.SIGNAL_NODE_NEW)
    dispatcher.connect(louie_scene_event, ZWaveNetwork.SIGNAL_SCENE_EVENT)


def louie_network_stopped(network):
    L.l.info('Louie signal: OpenZWave network stopped.')


def louie_network_awaked(network):
    L.l.info('Louie signal: OpenZWave network awaked.')


def louie_node_update(network, node):
    # L.l.info('Louie signal: Node update : {}.'.format(node))
    pass


def _set_custom_relay_state(sensor_address, state):
    # pin_code = '{}:{}'.format(sensor_name, node_id)
    current_relay = m.ZoneCustomRelay.find_one({
        m.ZoneCustomRelay.gpio_pin_code: sensor_address, m.ZoneCustomRelay.gpio_host_name: Constant.HOST_NAME})
    if current_relay is not None:
        current_relay.relay_is_on = state
        current_relay.is_event_external = True
        current_relay.is_device_event = True
        current_relay.save_changed_fields(broadcast=False, persist=True)
    else:
        L.l.info("ZoneCustomRelay with code={} not defined in database".format(sensor_address))


# Qubino Meter Values
# Powerlevel (Normal), Energy (kWh),  Energy (kVAh), Power (W), Voltage (V), Current (A), Power Factor, Unknown
# Exporting=False, Unknown=-70.5

# TMBK Switch values
# Switch All=On and Off Enabled, Powerlevel=Normal, Switch=True, Exporting=False, Energy=0.483kWh, Power=109.6W,
# Voltage=222.7V, Current=0.912A, Power Factor=0.54, Timeout=0

# May  5 05:54:42 homew start.sh[12282]: 2019-05-05 05:54:42,940 haiot INFO -1433127824 __init__:set_value
# Cannot find zwave sensor in db, address=Unknown: type=0007, id=0052_2
# node=home_id: [0xe39aea61] id: [2] name: [] model: [Unknown: type=0007, id=0052]
# value=home_id: [0xe39aea61] id: [72057594076496002] parent_id: [2] label: [Power] data: [774.0999755859375]
# https://github.com/OpenZWave/python-openzwave/blob/master/examples/api_demo.py
def set_value(network, node, value):
    try:
        # L.l.info('Louie set_value signal: Node={} Value={}'.format(node, value))
        sensor_address = "{}_{}".format(node.product_name, node.node_id)
        zone_sensor = m.ZoneSensor.find_one({m.ZoneSensor.sensor_address: sensor_address})
        if zone_sensor is not None:
            sensor_name = zone_sensor.sensor_name
            P.last_value_received = datetime.now()
            if value.label == "Switch":
                _set_custom_relay_state(sensor_address=sensor_address, state=value.data)
            elif value.label == "Power":
                if value.units == "W":
                    units_adjusted = "watt"  # this should match Utility unit name in models definition
                    value_adjusted = round(value.data, 0)
                    if abs(value_adjusted) < P.MAX_SENSOR_POWER_WATTS:
                        haiot_dispatch.send(Constant.SIGNAL_UTILITY_EX, sensor_name=sensor_name, value=value_adjusted,
                                            unit=units_adjusted)
                    else:
                        L.l.warning("Faulty power reading, value={}, cap={}".format(value_adjusted,
                                                                                    P.MAX_SENSOR_POWER_WATTS))
                else:
                    L.l.warning("Unknown power units {} for sensor {}".format(value.units, sensor_name))
                # L.l.info("Saving power utility {} {} {}".format(sensor_name, value.units, value.data))
            elif value.label == "Energy" and value.units == "kWh":
                haiot_dispatch.send(Constant.SIGNAL_UTILITY_EX, sensor_name=sensor_name, value=value.data,
                                    unit=value.units)
                # L.l.info("Saving energy utility {} {} {}".format(sensor_name, value.units, value.data))
            else:
                # skip controller node
                if node.node_id > 1:
                    record = m.Sensor.find_one({m.Sensor.address: sensor_address})
                    delta_last_save = P.DELTA_SAVE_SECONDS
                    if record is None:
                        L.l.info("Zwave sensor address not found:[{}]".format(sensor_address))
                        record = m.Sensor()
                        record.address = sensor_address
                        record.sensor_name = zone_sensor.sensor_name
                        record.updated_on = datetime.now()
                    else:
                        if record.updated_on is not None:
                            delta_last_save = (datetime.now() - record.updated_on).total_seconds()
                    record.is_event_external = True
                    if value.label == "Voltage":
                        if abs(value.data) < P.MAX_SENSOR_VOLTAGE:
                            record.vad = round(value.data, 0)
                            record.save_changed_fields(broadcast=False, persist=True)
                        else:
                            L.l.warning("Faulty voltage reading, value={}, cap={}".format(
                                value.data, P.MAX_SENSOR_VOLTAGE))
                        # L.l.info("Saving voltage {} {}".format(sensor_name, value.data))
                    elif value.label == "Current":
                        record.iad = round(value.data, 1)
                        record.save_changed_fields(broadcast=False, persist=True)
                        # L.l.info("Saving current {} {}".format(sensor_name, value.data))
                    elif value.label == "Power Factor":
                        if abs(value.data) < P.MAX_POWER_FACTOR:
                            record.vdd = round(value.data, 1)
                            record.save_changed_fields(broadcast=False, persist=True)
                        else:
                            L.l.warning("Faulty pf reading, value={}, cap={}".format(
                                value.data, P.MAX_POWER_FACTOR))
                        # L.l.info("Saving power factor {} {}".format(sensor_name, value.data))
                    else:
                        # L.l.warning("Doing nothing on zwave set value {}".format(value))
                        pass
        else:
            L.l.info("Cannot find zwave sensor in db, address={} node={} value={}".format(sensor_address, node, value))
    except Exception as ex:
        L.l.error("Error in zwave value={}".format(ex), exc_info=True)


def louie_button_on(network, node):
    L.l.info('Louie signal: Button on: {}.'.format(node))


def louie_button_off(network, node):
    L.l.info('Louie signal: Button off: {}.'.format(node))


def louie_node_event(network, node, value=None, extra=None):
    L.l.info('Louie signal: Node event: {} = {}, extra={}.'.format(node, value, extra))


def louie_node_event(network, node, value=None):
    L.l.info('Louie signal: Node event: {} = {}'.format(node, value))


def louie_scene_event(network, node, scene_id):
    L.l.info('Louie signal: Scene event: {} = {}.'.format(node, scene_id))


def louie_value_refreshed(network, node, value):
    L.l.info('Louie signal: Value refreshed: {} = {}.'.format(node, value))


def louie_value_changed(network, node, value):
    # L.l.info('Louie signal: Value changed for {}={} {}'.format(value.label, value.data, value.units))
    set_value(network, node, value)


def louie_value_added(network, node, value):
    L.l.info('Louie signal: Value added: {} = {}.'.format(node, value))
    set_value(network, node, value)


def louie_value_removed(network, node, value):
    L.l.info('Louie signal: Value removed: {} = {}.'.format(node, value))


def louie_ctrl_message(state, message, network, controller):
    L.l.info('Louie signal : Controller message : {}.'.format(message))


def _stop_net():
    if P.network is not None:
        L.l.info('Stopping network')
        P.network.stop()
        count = 0
        while P.network.state != ZWaveNetwork.STATE_STOPPED or count < 50:
            time.sleep(0.2)
            count += 1
        if P.network.state == ZWaveNetwork.STATE_STOPPED:
            L.l.info("Stop network successfull")
        else:
            L.l.info("Stop network failed, state={}".format(P.network.state))
        P.network = None
    else:
        # L.l.info("Zwave network already stopped (none)")
        pass


# http://openzwave.github.io/python-openzwave/network.html
def _init_controller():
    if P.module_imported:
        device = '{}{}'.format(P.device, P.device_index)
        L.l.info('Zwave initialising on {}'.format(device))
        _stop_net()
        # Define some manager options
        try:
            options = ZWaveOption(device, config_path="../openzwave/config", user_path=".", cmd_line="")
            options.set_log_file(P.log_file)
            options.set_append_log_file(True)
            options.set_console_output(False)
            # options.set_save_log_level('Debug')
            # options.set_save_log_level('Info')
            options.set_save_log_level('Warning')
            # options.set_save_log_level('Error')
            options.set_logging(False)
            #options.set_logging(True)
            # options.set_poll_interval(5)
            options.set_save_configuration(True)
            options.lock()

            # Create a network object
            P.network = ZWaveNetwork(options, log=None, autostart=False)
            dispatcher.connect(louie_network_started, ZWaveNetwork.SIGNAL_NETWORK_STARTED)
            dispatcher.connect(louie_network_failed, ZWaveNetwork.SIGNAL_NETWORK_FAILED)
            dispatcher.connect(louie_network_resetted, ZWaveNetwork.SIGNAL_NETWORK_RESETTED)
            dispatcher.connect(louie_network_ready, ZWaveNetwork.SIGNAL_NETWORK_READY)
            dispatcher.connect(louie_network_stopped, ZWaveNetwork.SIGNAL_NETWORK_STOPPED)
            dispatcher.connect(louie_network_awaked, ZWaveNetwork.SIGNAL_NETWORK_AWAKED)

            P.network.start()

            L.l.info("Waiting for zwave driver")
            for i in range(0, 120):
                if P.network.state >= P.network.STATE_STARTED:
                    L.l.info("Zwave driver started")
                    break
                else:
                    time.sleep(0.1)
            if P.network.state < P.network.STATE_STARTED:
                L.l.info("Can't initialise zwave driver. Look at the logs in {}".format(P.log_file))
                return False
            L.l.info("Home id : {}, Nodes in network : {}".format(P.network.home_id_str, P.network.nodes_count))

            L.l.info("Waiting 120 sec for zwave network to become ready")
            for i in range(0, 240):
                if P.network.state >= P.network.STATE_READY:
                    break
                else:
                    time.sleep(0.5)
                    # L.l.info("state = {}".format(P.network.state))
            if not P.network.is_ready:
                L.l.info("Can't start network! Look at the logs in OZW_Log.log")
                P.network.stop()
                return False
            else:
                L.l.info("Zwave network is started!")
            # print nodes
            for node_id in P.network.nodes:
                node = P.network.nodes[node_id]
                try:
                    L.l.info("Node {}={}".format(node_id, node))
                    # L.l.info("Node {} attrib: model={} man={} prod_name={} prod_id={}".format(
                    #     node_id, node.manufacturer_name, node.product_name, node.product_id))
                except Exception as ex:
                    pass
            # not working
            # P.network.set_poll_interval(milliseconds=3000, bIntervalBetweenPolls=False)
            # P.network.test(1)
            variable.USB_PORTS_IN_USE.append(device)
            return True
        except ZWaveException as ze:
            L.l.error('Unable to init zwave, exception={}'.format(ze))
            P.device_index += 1
            if P.device_index > 3:
                P.device_index = 0
    return False


def include_node():
    if not P.inclusion_started:
        if P.network is not None:
            L.l.info("Starting node inclusion")
            res = P.network.controller.add_node()
            L.l.info("Node inclusion returned {}".format(res))
            P.inclusion_started = True
    else:
        L.l.info("Zwave inclusion already started")


def stop_include_node():
    if P.inclusion_started:
        if P.network is not None:
            L.l.info("Stopping node inclusion by cancel command")
            res = P.network.controller.cancel_command()
            L.l.info("Cancel command returned {}".format(res))
            P.inclusion_started = False
    else:
        L.l.info("Zwave inclusion not started")


def remove_node(node_id):
    node = P.network.nodes[node_id]
    if node.is_failed:
        L.l.info("Node failed: {}".format(node))
        res = P.network.controller.remove_failed_node(node_id)
        L.l.info("Removing failed node {} returned {}".format(node, res))


def switch_all_on():
    for node in P.network.nodes:
        for val in P.network.nodes[node].get_switches():
            L.l.info("Activate switch {} on node {}".format(P.network.nodes[node].values[val].label, node))
            P.network.nodes[node].set_switch(val, True)
            L.l.info("Sleep 10 seconds")
            time.sleep(10)
            L.l.info("Dectivate switch {} on node {}".format(P.network.nodes[node].values[val].label, node))
            P.network.nodes[node].set_switch(val, False)


def get_node_id_from_txt(gpio_pin_code):
    vals = gpio_pin_code.split('_')
    if len(vals) == 2:
        node_id = int(vals[1])
        return node_id
    return None


def set_switch_state(node_id, state):
    L.l.info("Setting switch node_id={} to {}".format(node_id, state))
    found = False
    for nid in P.network.nodes:
        node = P.network.nodes[nid]
        if node.node_id == node_id:
            for switch in node.get_switches():
                node.set_switch(switch, state)
                L.l.info("Switch set, switch={} state={}".format(switch, state))
                found = True
            break
    if not found:
        L.l.error("Switch with id={} not found in zwave network".format(node_id))
    else:
        return state


# https://hk.saowen.com/a/b5d414ca130fafc1f306a46dc0e2f13ec54876d9070ff3122a0a93a956b1fa2f
def _set_param(node_id, param_name, value, param_code):
    node = P.network.nodes[node_id]
    configs = node.get_configs()
    conf = []
    for c in configs:
        if configs[c].label == param_name:
            old = configs[c].data
            node.set_config(c, value)
            L.l.info("Set ok param {} {} to {}, old value={}".format(c, configs[c].label, value, old))
            return True
        conf.append(configs[c])
    L.l.warning("Could not find parameter {} in config list {}, trying alternate config set".format(param_name, conf))
    node.set_config(param_code, value)
    return False


# https://github.com/openhab/org.openhab.binding.zwave/blob/master/doc/qubino/zmnhxd_0_0.md
def _initial_node_init():
    if not P.init_done:
        # Parameter no. 40 –Reporting Watts on power change
        # Set value means percentage from 0-100 = 0% - 100%
        # Values (size is 1 byte dec):
        # • Default value 10
        # • 0 – reporting disabled
        # • 1-100 = 1% - 100% reporting enabled. Power report is send (push) only when actual
        # power in Watts (in real time changes for more than set percentage comparing to
        # previous actual power in Watts, step is 1%.
        _set_param(2, 'Power reporting in Watts on power change',  1, 40)
        # Parameter no. 43 – Other Values - Reporting on time interval
        # This parameter is valid only for Voltage (V of ph1, ph2, ph3), Current (A of ph1, ph2, ph3), Total
        # Power Factor, Total Reactive Power (var)
        # Available configuration parameters (data type is 2 Byte DEC)
        # • Default value 600 (600 seconds - 10 minutes)
        # • 0 – reporting disabled
        # • 30-32535 = 30 (30 seconds – 32535 seconds). Reporting enabled. Report is send
        # with the time interval set by entered value.
        # • Note: Device is reporting only if there was a change
        _set_param(2, 'Other Values - Reporting on time interval', 30, 43)
        # Parameter no. 42 – Reporting on time interval
        # Values (size is 2 byte dec):
        # • Default value 600 (10 minutes)
        # • 0-59 = reporting disabled
        # • 60-32535 = 60 seconds - 32535 seconds. Reporting enabled. Report is send with the
        # time interval set by entered value.
        _set_param(2, 'Power reporting in Watts by time interval', 60, 42)
        P.init_done = True
        node = P.network.nodes[2]
        configs = node.get_configs()
        prod = node.product_name
        for c in configs:
            L.l.info("config {}".format(configs[c]))


def thread_run():
    prctl.set_name("zwave")
    threading.current_thread().name = "zwave"
    # L.l.info("State is {}".format(P.network.state))
    try:
        if not P.initialised:
            P.initialised = _init_controller()
            if not P.initialised:
                P.init_fail_count += 1
                if P.init_fail_count > 10:
                    unload()
        # iterate if inclusion is not started
        if P.initialised and not P.inclusion_started:
            for node_id in P.network.nodes:
                node = P.network.nodes[node_id]
                if node_id == 2 or not P.thread_run_at_init:
                    if not P.thread_run_at_init:
                        L.l.info("Request state for node {}".format(node))
                    node.request_state()
            if not P.thread_run_at_init:
                P.thread_run_at_init = True
            sec = (datetime.now() - P.last_value_received).total_seconds()
            if sec > P.MAX_SILENCE_SEC:
                L.l.info("Zwave seems inactive, no value received since {} sec, reset now".format(sec))
                P.initialised = _init_controller()
            _initial_node_init()
    except Exception as ex:
        L.l.error("Error in zwave thread run={}".format(ex), exc_info=True)
    prctl.set_name("idle_zwave")
    threading.current_thread().name = "idle_zwave"


def unload():
    L.l.info("Unloading zwave")
    if P.network is not None:
        P.network.stop()
    thread_pool.remove_callable(thread_run)
    P.initialised = False


# called once a usb change is detected
def _init_recovery():
    if not P.initialised:
        thread_pool.add_interval_callable(thread_run, run_interval_second=P.interval)


def init():
    if P.module_imported:
        thread_pool.add_interval_callable(thread_run, run_interval_second=P.interval)
        opath = '../openzwave/config'
        if not os.path.isdir(opath):
            L.l.info('Openzawave config directory does not exist, creating')
            if not os.path.isdir('../openzwave'):
                os.mkdir('../openzwave')
            if not os.path.isdir(opath):
                os.mkdir(opath)
        if not os.path.isfile(opath + '/zwcfg.xsd'):
            L.l.info('Openzawave config file does not exist, creating empty')
            with open(opath + "/zwcfg.xsd", "w") as text_file:
                print("", file=text_file)
        if not os.path.isfile(opath + '/options.xml'):
            L.l.info('Openzawave options file does not exist, creating empty')
            with open(opath + "/options.xml", "w") as text_file:
                print("", file=text_file)
        dispatcher.connect(_init_recovery, signal=Constant.SIGNAL_USB_DEVICE_CHANGE, sender=dispatcher.Any)

