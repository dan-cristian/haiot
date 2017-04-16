from main.admin.model_helper import get_param, commit
from common import Constant
import socket
import time
import binascii
from main.admin import models
from main.logger_helper import Log

_AMP_ON = "\x0207A1D\x03"
_AMP_OFF = "\x0207A1E\x03"

_AMP_MUTE_ON = "\x0207EA2\x03"
_AMP_MUTE_OFF = "\x0207EA3\x03"

_AMP_BI_ON = "\x022BB00\x03"
_AMP_BI_OFF = "\x022BB01\x03"

_AMP_ZONE2_POWER_ON = "\x0207EBA\x03"
_AMP_ZONE2_POWER_OFF = "\x0207EBB\x03"
_AMP_ZONE3_POWER_ON = "\x0207AED\x03"
_AMP_ZONE3_POWER_OFF = "\x0207AEE\x03"


def connect_socket():
    host = get_param(Constant.P_AMP_SERIAL_HOST)
    port = int(get_param(Constant.P_AMP_SERIAL_PORT))
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))
    return s


def amp_bi_set_yamaha(on):
    global _AMP_BI_ON
    sock = connect_socket()
    if on:
        sock.send(_AMP_BI_ON)
    else:
        sock.send(_AMP_BI_OFF)
    data = sock.recv(1024)
    time.sleep(1)
    sock.send(_AMP_OFF)
    data = sock.recv(1024)
    time.sleep(1)
    sock.send(_AMP_ON)
    sock.close()
    return data


def amp_zone_power(on, zone_index):
    global _AMP_ZONE3_POWER_OFF, _AMP_ZONE3_POWER_ON
    sock = connect_socket()
    if on:
        if zone_index == 3:
            sock.send(_AMP_ZONE3_POWER_ON)
        elif zone_index == 2:
            sock.send(_AMP_ZONE2_POWER_ON)
    else:
        if zone_index == 3:
            sock.send(_AMP_ZONE3_POWER_OFF)
        elif zone_index == 2:
            sock.send(_AMP_ZONE2_POWER_OFF)
    data = sock.recv(1024)
    result = binascii.b2a_hex(data)
    sock.close()
    Log.logger.info("Set amp zone {} to state {}".format(zone_index, on))
    return 'power on={} zone_index={} result={}\n'.format(on, zone_index, result)


def set_amp_power(power_state, relay_name, amp_zone_index):
    relay = models.ZoneCustomRelay.query.filter_by(relay_pin_name=relay_name).first()
    if relay is not None:
        initial_relay_state = relay.relay_is_on
        relay.relay_is_on = power_state
        commit()
        Log.logger.info("Set relay {} to state {}".format(relay_name, power_state))
    else:
        msg = "Could not find relay name {}\n".format(relay_name)
        Log.logger.warning(msg)
        return msg

    if amp_zone_index is None or amp_zone_index == "0":
        # only relay change is needed
        return "Power in {} set to {}\n".format(relay_name, relay.relay_is_on)
    else:
        # potentially amp settings change is required to switch amp zones
        if initial_relay_state is not power_state:
                # delay to wait for amp to fully start
                time.sleep(5)
        return amp_zone_power(power_state, int(amp_zone_index))
