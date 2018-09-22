import threading
import prctl
from main.logger_helper import L
from common import Constant
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
    init_fail_count = 0
    device = "/dev/ttyACM0"
    log_file = "OZW_Log.log"


try:
    import openzwave
    from openzwave.node import ZWaveNode
    from openzwave.value import ZWaveValue
    from openzwave.scene import ZWaveScene
    from openzwave.controller import ZWaveController
    from openzwave.network import ZWaveNetwork
    from openzwave.option import ZWaveOption
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
    dispatcher.connect(louie_value, ZWaveNetwork.SIGNAL_VALUE)
    dispatcher.connect(louie_value_update, ZWaveNetwork.SIGNAL_VALUE_REFRESHED)
    dispatcher.connect(louie_value_added, ZWaveNetwork.SIGNAL_VALUE_ADDED)
    #dispatcher.connect(louie_value_changed, ZWaveNetwork.SIGNAL_VALUE_CHANGED)
    dispatcher.connect(louie_value_removed, ZWaveNetwork.SIGNAL_VALUE_REMOVED)
    dispatcher.connect(louie_ctrl_message, ZWaveController.SIGNAL_CONTROLLER)


def louie_network_stopped(network):
    L.l.info('Louie signal: OpenZWave network stopped.')


def louie_network_awaked(network):
    L.l.info('Louie signal: OpenZWave network awaked.')


def louie_node_update(network, node):
    # L.l.info('Louie signal: Node update : {}.'.format(node))
    pass



# Qubino Meter Values
# Powerlevel (Normal), Energy (kWh),  Energy (kVAh), Power (W), Voltage (V), Current (A), Power Factor, Unknown
# Exporting=False, Unknown=-70.5

# TMBK Switch values
# Switch All=On and Off Enabled, Powerlevel=Normal, Switch=True, Exporting=False, Energy=0.483kWh, Power=109.6W,
# Voltage=222.7V, Current=0.912A, Power Factor=0.54, Timeout=0
def louie_value(network, node, value):
    try:
        # L.l.info('Louie signal: Node={} Value={}'.format(node, value))
        if value.label == "Switch":
            if value.data is True:
                L.l.info("Switch is ON".format(node, value))

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
            # L.l.info("Received node={}, value={}".format(node, value))
            current_record = models.Sensor.query.filter_by(sensor_name=node.product_name).first()
            if current_record is not None:
                current_record.vad = None
                current_record.iad = None
                current_record.vdd = None
                address = current_record.address
            else:
                L.l.info("Cannot find sensor definition in db, name=[{}]".format(node.product_name))
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
    except Exception as ex:
        L.l.error("Error in zwave value={}".format(ex), exc_info=True)


def louie_value_update(network, node, value):
    L.l.info('Louie signal: Value update: {} = {}.'.format(node, value))


def louie_value_changed(network, node, value):
    L.l.info('Louie signal: Value changed for {}={} {}'.format(value.label, value.data, value.units))


def louie_value_added(network, node, value):
    L.l.info('Louie signal: Value added: {} = {}.'.format(node, value))
    louie_value(network, node, value)


def louie_value_removed(network, node, value):
    L.l.info('Louie signal: Value removed: {} = {}.'.format(node, value))


def louie_ctrl_message(state, message, network, controller):
    L.l.info('Louie signal : Controller message : {}.'.format(message))


def unload():
    L.l.info("Unloading zwave")
    if P.network is not None:
        P.network.stop()
    thread_pool.remove_callable(thread_run)


# http://openzwave.github.io/python-openzwave/network.html
def init():
    if P.module_imported:
        L.l.info('Zwave initialising on {}'.format(P.device))
        # Define some manager options
        options = ZWaveOption(P.device, config_path="../openzwave/config", user_path=".", cmd_line="")
        options.set_log_file(P.log_file)
        options.set_append_log_file(True)
        options.set_console_output(False)
        # options.set_save_log_level("Debug")
        options.set_save_log_level('Info')
        #options.set_save_log_level('Error')
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

        L.l.info("Waiting for network to become ready")
        for i in range(0, 120):
            if P.network.state >= P.network.STATE_READY:
                break
            else:
                time.sleep(0.3)
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
            L.l.info("Node {}={}".format(node_id, node))
        # not working
        # P.network.set_poll_interval(milliseconds=3000, bIntervalBetweenPolls=False)
        # P.network.test(1)
        return True
    else:
        # L.l.info("Zwave init skipped")
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


def thread_run():
    prctl.set_name("zwave")
    threading.current_thread().name = "zwave"
    #L.l.info("State is {}".format(P.network.state))
    try:
        if not P.initialised:
            P.initialised = init()
            if not P.initialised:
                P.init_fail_count += 1
                if P.init_fail_count > 10:
                    unload()
        if P.initialised:
            for node_id in P.network.nodes:
                node = P.network.nodes[node_id]
                if node_id > 1:
                    node.request_state()
    except Exception as ex:
        L.l.error("Error in zwave thread run={}".format(ex), exc_info=True)
    prctl.set_name("idle")
    threading.current_thread().name = "idle"

