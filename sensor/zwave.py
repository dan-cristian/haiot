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


def louie_network_started(network):
    print('//////////// ZWave network is started ////////////')
    print(
        'Louie signal : OpenZWave network is started : homeid {:08x} - {} nodes were found.'.format(network.home_id,
                                                                                                    network.nodes_count))


def louie_network_failed(network):
    L.l.info('Louie signal : OpenZWave network failed.')


def louie_network_resetted(network):
    L.l.info('Louie signal : OpenZWave network is resetted.')


def louie_network_ready(network):
    L.l.info('//////////// ZWave network is ready ////////////')
    L.l.info('Louie signal : ZWave network is ready : {} nodes were found.'.format(network.nodes_count))
    L.l.info('Louie signal : Controller : {}'.format(network.controller))
    dispatcher.connect(louie_node_update, signal=ZWaveNetwork.SIGNAL_NODE, sender=dispatcher.Any)
    dispatcher.connect(louie_value_update, signal=ZWaveNetwork.SIGNAL_VALUE, sender=dispatcher.Any)
    dispatcher.connect(louie_ctrl_message, signal=ZWaveController.SIGNAL_CONTROLLER, sender=dispatcher.Any)


def louie_node_update(network, node):
    L.l.info('Louie signal : Node update : {}.'.format(node))


def louie_value_update(network, node, value):
    L.l.info('Louie signal : Value update : {}.'.format(value))


def louie_ctrl_message(state, message, network, controller):
    L.l.info('Louie signal : Controller message : {}.'.format(message))


def init():
    L.l.debug('Zwave initialising')
    device = "/dev/ttyACM0"
    # Define some manager options
    options = ZWaveOption(device, config_path="../openzwave/config", user_path=".", cmd_line="")
    options.set_log_file("OZW_Log.log")
    options.set_append_log_file(False)
    options.set_console_output(False)
    options.set_save_log_level("Debug")
    # options.set_save_log_level('Info')
    options.set_logging(True)
    options.lock()

    # Create a network object
    network = ZWaveNetwork(options, log=None, autostart=False)
    dispatcher.connect(louie_network_started, ZWaveNetwork.SIGNAL_NETWORK_STARTED)
    dispatcher.connect(louie_network_failed, ZWaveNetwork.SIGNAL_NETWORK_FAILED)
    dispatcher.connect(louie_network_resetted, ZWaveNetwork.SIGNAL_NETWORK_RESETTED)
    dispatcher.connect(louie_network_ready, ZWaveNetwork.SIGNAL_NETWORK_READY)

    network.start()

    L.l.info("Waiting for zwave driver")
    for i in range(0, 60):
        if network.state >= network.STATE_STARTED:
            L.l.info("Zwave driver started")
            break
        else:
            time.sleep(1.0)
    if network.state < network.STATE_STARTED:
        L.l.info("Can't initialise zwave driver. Look at the logs in OZW_Log.log")
        return False
    L.l.info("Home id : {}, Nodes in network : {}".format(network.home_id_str, network.nodes_count))
    L.l.info("Waiting for network to become ready")
    for i in range(0, 60):
        if network.state >= network.STATE_READY:
            break
        else:
            time.sleep(1.0)
            L.l.info("state = {}".format(network.state))
    if not network.is_ready:
        L.l.info("Can't start network! Look at the logs in OZW_Log.log")
        return False
    else:
        L.l.info("Network is started!")

    for i in range(0, 60):
        time.sleep(1.0)

    try:
        pass
    except Exception as ex:
        pass

    return True
