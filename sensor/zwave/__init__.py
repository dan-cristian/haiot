import threading
import prctl
from datetime import datetime
from main.logger_helper import L
from common import Constant, variable
from main.admin import models
from main import thread_pool
import six
if six.PY3:
    from pydispatch import dispatcher
else:
    from louie import dispatcher
import time
from pydispatch import dispatcher as haiot_dispatch


class P:
    network = None
    module_imported = False
    did_inclusion = False
    initialised = False
    interval = 10
    init_fail_count = 0
    device = "/dev/ttyACM"
    device_index = 0
    log_file = "OZW_Log.log"
    last_value_received = datetime.max
    MAX_SILENCE_SEC = 120


try:
    import openzwave
    from openzwave.node import ZWaveNode
    from openzwave.value import ZWaveValue
    from openzwave.scene import ZWaveScene
    from openzwave.controller import ZWaveController
    from openzwave.network import ZWaveNetwork
    from openzwave.option import ZWaveOption
    from openzwave.object import ZWaveException
    P.module_imported = True
except Exception as e:
    L.l.info("Cannot import openzwave")


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
    dispatcher.connect(louie_scene_event, ZWaveNetwork.SIGNAL_SCENE_EVENT)


def louie_network_stopped(network):
    L.l.info('Louie signal: OpenZWave network stopped.')


def louie_network_awaked(network):
    L.l.info('Louie signal: OpenZWave network awaked.')


def louie_node_update(network, node):
    # L.l.info('Louie signal: Node update : {}.'.format(node))
    pass


def _set_custom_relay_state(sensor_name, node_id, state):
    pin_code = '{}:{}'.format(sensor_name, node_id)
    current_relay = models.ZoneCustomRelay.query.filter_by(
        gpio_pin_code=pin_code, gpio_host_name=Constant.HOST_NAME).first()
    if current_relay is not None:
        new_relay = models.ZoneCustomRelay(gpio_pin_code=pin_code, gpio_host_name=Constant.HOST_NAME)
        new_relay.relay_is_on = state
        models.ZoneCustomRelay().save_changed_fields(
            current_record=current_relay, new_record=new_relay, notify_transport_enabled=True, save_to_graph=True)
    else:
        L.l.error("ZoneCustomRelay with code {} does not exist in database".format(pin_code))


# Qubino Meter Values
# Powerlevel (Normal), Energy (kWh),  Energy (kVAh), Power (W), Voltage (V), Current (A), Power Factor, Unknown
# Exporting=False, Unknown=-70.5

# TMBK Switch values
# Switch All=On and Off Enabled, Powerlevel=Normal, Switch=True, Exporting=False, Energy=0.483kWh, Power=109.6W,
# Voltage=222.7V, Current=0.912A, Power Factor=0.54, Timeout=0

# https://github.com/OpenZWave/python-openzwave/blob/master/examples/api_demo.py
def set_value(network, node, value):
    try:
        # L.l.info('Louie signal: Node={} Value={}'.format(node, value))
        P.last_value_received = datetime.now()
        if value.label == "Switch":
            _set_custom_relay_state(sensor_name=node.product_name, node_id=node.node_id, state=value.data)
        elif value.label == "Power" or (value.label == "Energy" and value.units == "kWh"):
            #L.l.info("Saving power utility")
            if value.units == "W":
                units_adjusted = "watt"  # this should match Utility unit name in models definition
                value_adjusted = round(value.data, 0)
            else:
                units_adjusted = value.units
                value_adjusted = value.data

            haiot_dispatch.send(Constant.SIGNAL_UTILITY_EX, sensor_name=node.product_name,
                                value=value_adjusted, unit=units_adjusted)
        else:
            if node.node_id > 1:
                # L.l.info("Received node={}, value={}".format(node, value))
                current_record = models.Sensor.query.filter_by(sensor_name=node.product_name).first()
                if current_record is not None:
                    current_record.vad = None
                    current_record.iad = None
                    current_record.vdd = None
                    address = current_record.address
                else:
                    # first sensor read, nothing in DB
                    # L.l.info("Cannot find sensor definition in db, name=[{}]".format(node.product_name))
                    address = node.product_name
                record = models.Sensor(sensor_name=node.product_name, address=address)
                if value.label == "Voltage":
                    record.vad = round(value.data, 0)
                    record.save_changed_fields(current_record=current_record, new_record=record,
                                               notify_transport_enabled=True, save_to_graph=True, debug=False)
                elif value.label == "Current":
                    record.iad = round(value.data, 1)
                    record.save_changed_fields(current_record=current_record, new_record=record,
                                               notify_transport_enabled=True, save_to_graph=True, debug=False)
                elif value.label == "Power Factor":
                    record.vdd = round(value.data, 1)
                    record.save_changed_fields(current_record=current_record, new_record=record,
                                               notify_transport_enabled=True, save_to_graph=True, debug=False)
                if current_record is not None:
                    current_record.commit_record_to_db()
                else:
                    record.add_commit_record_to_db()
    except Exception as ex:
        L.l.error("Error in zwave value={}".format(ex), exc_info=True)


def louie_button_on(network, node):
    L.l.info('Louie signal: Button on: {}.'.format(node))


def louie_button_off(network, node):
    L.l.info('Louie signal: Button off: {}.'.format(node))


def louie_node_event(network, node, value):
    L.l.info('Louie signal: Node event: {} = {}.'.format(node, value))


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
            # options.set_logging(False)
            options.set_logging(True)
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

            L.l.info("Waiting 120 sec for network to become ready")
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
    if not P.did_inclusion and P.network is not None:
        L.l.info("!!!!!!!!!!! Listening for new node inclusion")
        res = P.network.controller.add_node()
        L.l.info("!!!!!!!!!!!! Node inclusion returned {}, waiting for 30 seconds".format(res))
        time.sleep(20)
        P.did_inclusion = True
        L.l.info("!!!!!!!!!!! Node inclusion done".format(res))


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
            P.network.nodes[node].set_switch(val,False)


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
        if P.initialised:
            for node_id in P.network.nodes:
                node = P.network.nodes[node_id]
                if node_id == 2:
                    node.request_state()
            sec = (datetime.now() - P.last_value_received).total_seconds()
            if sec > P.MAX_SILENCE_SEC:
                L.l.info("Zwave seems inactive, no value received since {} sec, reset now".format(sec))
                P.initialised = _init_controller()
    except Exception as ex:
        L.l.error("Error in zwave thread run={}".format(ex), exc_info=True)
    prctl.set_name("idle")
    threading.current_thread().name = "idle"


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
    thread_pool.add_interval_callable(thread_run, run_interval_second=P.interval)
    dispatcher.connect(_init_recovery, signal=Constant.SIGNAL_USB_DEVICE_CHANGE, sender=dispatcher.Any)
