from main.logger_helper import L
import six
if six.PY3:
    from pydispatch import dispatcher
else:
    from louie import dispatcher
import time

try:
    import openzwave
    from openzwave.node import ZWaveNode
    from openzwave.value import ZWaveValue
    from openzwave.scene import ZWaveScene
    from openzwave.controller import ZWaveController
    from openzwave.network import ZWaveNetwork
    from openzwave.option import ZWaveOption
except Exception, e:
    L.l.info("Cannot import openzwave")


class P:
    network = None


def louie_network_started(network):
    print('Louie signal: OpenZWave network started: homeid {:08x} - {} nodes found.'.format(
        network.home_id, network.nodes_count))


def louie_network_failed(network):
    L.l.info('Louie signal: OpenZWave network failed.')


def louie_network_resetted(network):
    L.l.info('Louie signal: OpenZWave network is resetted.')


def louie_network_ready(network):
    L.l.info('Louie signal: ZWave network is ready : {} nodes were found.'.format(network.nodes_count))
    L.l.info('Louie signal: Controller : {}'.format(network.controller))
    dispatcher.connect(louie_node_update, ZWaveNetwork.SIGNAL_NODE)
    dispatcher.connect(louie_value, ZWaveNetwork.SIGNAL_VALUE)
    dispatcher.connect(louie_value_update, ZWaveNetwork.SIGNAL_VALUE_REFRESHED)
    dispatcher.connect(louie_value_added, ZWaveNetwork.SIGNAL_VALUE_ADDED)
    dispatcher.connect(louie_value_changed, ZWaveNetwork.SIGNAL_VALUE_CHANGED)
    dispatcher.connect(louie_value_removed, ZWaveNetwork.SIGNAL_VALUE_REMOVED)
    dispatcher.connect(louie_ctrl_message, ZWaveController.SIGNAL_CONTROLLER)


def louie_node_update(network, node):
    L.l.info('Louie signal: Node update : {}.'.format(node))


def louie_value(network, node, value):
    L.l.info('Louie signal: Value : {} = {}.'.format(node, value))


def louie_value_update(network, node, value):
    L.l.info('Louie signal: Value update: {} = {}.'.format(node, value))


def louie_value_changed(network, node, value):
    L.l.info('Louie signal: Value changed for {}, {}={}.'.format(node, value.label, value.data))


def louie_value_added(network, node, value):
    L.l.info('Louie signal: Value added: {} = {}.'.format(node, value))


def louie_value_removed(network, node, value):
    L.l.info('Louie signal: Value removed: {} = {}.'.format(node, value))


def louie_ctrl_message(state, message, network, controller):
    L.l.info('Louie signal : Controller message : {}.'.format(message))


def unload():
    if P.network is not None:
        P.network.stop()


# http://openzwave.github.io/python-openzwave/network.html
def init():
    device = "/dev/ttyACM0"
    L.l.info('Zwave initialising on {}'.format(device))
    # Define some manager options
    options = ZWaveOption(device, config_path="../openzwave/config", user_path=".", cmd_line="")
    options.set_log_file("OZW_Log.log")
    options.set_append_log_file(False)
    options.set_console_output(False)
    options.set_save_log_level("Debug")
    options.set_poll_interval(10)
    # options.set_save_log_level('Info')
    options.set_logging(True)
    options.set_save_configuration(True)
    options.lock()

    # Create a network object
    P.network = ZWaveNetwork(options, log=None, autostart=False)
    dispatcher.connect(louie_network_started, ZWaveNetwork.SIGNAL_NETWORK_STARTED)
    dispatcher.connect(louie_network_failed, ZWaveNetwork.SIGNAL_NETWORK_FAILED)
    dispatcher.connect(louie_network_resetted, ZWaveNetwork.SIGNAL_NETWORK_RESETTED)
    dispatcher.connect(louie_network_ready, ZWaveNetwork.SIGNAL_NETWORK_READY)

    P.network.start()

    L.l.info("Waiting for zwave driver")
    for i in range(0, 60):
        if P.network.state >= P.network.STATE_STARTED:
            L.l.info("Zwave driver started")
            break
        else:
            time.sleep(1.0)
    if P.network.state < P.network.STATE_STARTED:
        L.l.info("Can't initialise zwave driver. Look at the logs in OZW_Log.log")
        return False
    L.l.info("Home id : {}, Nodes in network : {}".format(P.network.home_id_str, P.network.nodes_count))
    L.l.info("Waiting for network to become ready")
    for i in range(0, 60):
        if P.network.state >= P.network.STATE_READY:
            break
        else:
            time.sleep(1.0)
            L.l.info("state = {}".format(P.network.state))
    if not P.network.is_ready:
        L.l.info("Can't start network! Look at the logs in OZW_Log.log")
        return False
    else:
        L.l.info("Network is started!")

    #P.network.set_poll_interval(milliseconds=3000, bIntervalBetweenPolls=False)
    #P.network.test(1)

    try:
        pass
    except Exception as ex:
        pass
    return True


def thread_run():
    L.l.info("State is {}".format(P.network.state))
    for node_id in P.network.nodes:
        node = P.network.nodes[node_id]
        L.l.info("Node {}".format(node))
        node.request_state()
