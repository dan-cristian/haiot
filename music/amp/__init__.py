from common import Constant, get_json_param
import socket
import time
import binascii
from main import sqlitedb
if sqlitedb:
    from storage.sqalc.model_helper import commit
    from storage.sqalc import models
from main.logger_helper import L
from pydispatch import dispatcher
from storage.model import m

_AMP_ON = bytes("\x0207A1D\x03", 'utf-8')
_AMP_OFF = bytes("\x0207A1E\x03", 'utf-8')

_AMP_MUTE_ON = bytes("\x0207EA2\x03", 'utf-8')
_AMP_MUTE_OFF = bytes("\x0207EA3\x03", 'utf-8')

_AMP_BI_ON = bytes("\x022BB00\x03", 'utf-8')
_AMP_BI_OFF = bytes("\x022BB01\x03", 'utf-8')

_AMP_ZONE2_POWER_ON = bytes("\x0207EBA\x03", 'utf-8')
_AMP_ZONE2_POWER_OFF = bytes("\x0207EBB\x03", 'utf-8')
_AMP_ZONE3_POWER_ON = bytes("\x0207AED\x03", 'utf-8')
_AMP_ZONE3_POWER_OFF = bytes("\x0207AEE\x03", 'utf-8')


class AMP_YMH:
    BI_AMP_ON = None
    ZONE2_ON = None
    ZONE3_ON = None

    def __init__(self):
        pass


def connect_socket():
    host = get_json_param(Constant.P_AMP_SERIAL_HOST)
    port = int(get_json_param(Constant.P_AMP_SERIAL_PORT))
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    L.l.debug("Connecting socket")
    s.settimeout(2)
    s.connect((host, port))
    s.settimeout(None)
    L.l.debug("Connected socket")
    return s


def _amp_bi_set_yamaha(on, sock):
    # avoid periodic amp restarts
    if AMP_YMH.BI_AMP_ON is on:
        return

    global _AMP_BI_ON
    if on:
        sock.send(_AMP_BI_ON)
    else:
        sock.send(_AMP_BI_OFF)
    data = sock.recv(1024)
    if bytes("already in use", 'utf-8') in data:
        msg = "Error, {}\n".format(data)
        L.l.warning(msg)
        return msg
    else:
        AMP_YMH.BI_AMP_ON = on
        time.sleep(1)
        sock.send(_AMP_OFF)
        data = sock.recv(1024)
        time.sleep(1)
        sock.send(_AMP_ON)
        time.sleep(5)
        return data


def amp_zone_power(on, zone_index):
    L.l.info("Setting amp power {} for zone {}".format(on, zone_index))
    global _AMP_ZONE3_POWER_OFF, _AMP_ZONE3_POWER_ON
    sock = connect_socket()
    msg = "socket cmd ok, "
    sock.settimeout(5)
    if on:
        if zone_index == 3:
            sock.send(_AMP_ZONE3_POWER_ON)
            AMP_YMH.ZONE3_ON = on
        elif zone_index == 2:
            sock.send(_AMP_ZONE2_POWER_ON)
            AMP_YMH.ZONE2_ON = on
        elif zone_index == 1:
            msg = _amp_bi_set_yamaha(on, sock)
    else:
        if zone_index == 3:
            sock.send(_AMP_ZONE3_POWER_OFF)
            AMP_YMH.ZONE3_ON = on
        elif zone_index == 2:
            sock.send(_AMP_ZONE2_POWER_OFF)
            AMP_YMH.ZONE2_ON = on
        elif zone_index == 1:
            msg = _amp_bi_set_yamaha(on, sock)
    data = sock.recv(1024)
    result = binascii.b2a_hex(data)
    msg = "{} {}".format(msg, result)
    sock.close()
    result = "Set done amp zone {} to state {}, result={}\n".format(zone_index, on, msg)
    # L.l.info(result)
    return result


def set_amp_power(power_state, relay_name, amp_zone_index):
    try:
        relay = m.ZoneCustomRelay.find_one({m.ZoneCustomRelay.relay_pin_name: relay_name})
        power_state = bool(power_state)
        if relay is not None:
            initial_relay_state = relay.relay_is_on
            # power on main relay for amp or on/off if there is no zone
            if power_state is True or amp_zone_index == 0:
                relay.relay_is_on = power_state
                relay.save_changed_fields()
                # fixme: set amp
                # L.l.error('check if fix me set amp relay')
                msg = "Set relay {} to state {} zone_index={}\n".format(relay_name, power_state, amp_zone_index)
            else:
                msg = "Not changed relay state for {}\n".format(relay_name)
        else:
            msg = "Could not find relay name {}\n".format(relay_name)
            L.l.warning(msg)
            return msg

        # change amp zone power
        if amp_zone_index is None or amp_zone_index == 0:
            # only main relay change is needed
            return msg + "Power in {} set to {}\n".format(relay_name, relay.relay_is_on)
        else:
            # potentially amp settings change is required to switch amp zones
            if initial_relay_state is not True and power_state is True:
                # delay to wait for amp to fully start
                time.sleep(5)
                result_amp = amp_zone_power(power_state, amp_zone_index)
                return msg + result_amp
            else:
                msg += 'Power state is {} so no amp action'.format(power_state)
                return msg
    except Exception as ex:
        L.l.error("Error set_amp_power {}".format(ex), exc_info=True)
        return "Error set_amp_power {}".format(ex)
