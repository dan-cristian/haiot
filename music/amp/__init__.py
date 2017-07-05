from main.admin.model_helper import get_param, commit
from common import Constant
import socket
import time
import binascii
from main.admin import models
from main.logger_helper import Log
from pydispatch import dispatcher

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

class AMP_YMH:
    BI_AMP_ON = None
    ZONE2_ON = None
    ZONE3_ON = None


def connect_socket():
    host = get_param(Constant.P_AMP_SERIAL_HOST)
    port = int(get_param(Constant.P_AMP_SERIAL_PORT))
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    Log.logger.info("Connecting socket")
    s.settimeout(2)
    s.connect((host, port))
    s.settimeout(None)
    Log.logger.info("Connected socket")
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
    if "already in use" in data:
        msg = "Error, {}\n".format(data)
        Log.logger.warning(msg)
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
    Log.logger.info(result)
    return result


def set_amp_power(power_state, relay_name, amp_zone_index):
    Log.logger.info("step 1")
    relay = models.ZoneCustomRelay.query.filter_by(relay_pin_name=relay_name).first()
    Log.logger.info("step 2")
    power_state = bool(power_state)
    Log.logger.info("step 2.1")
    if relay is not None:
        initial_relay_state = relay.relay_is_on
        # power on main relay for amp or on/off if there is no zone
        Log.logger.info("step 2.2")
        if power_state is True or amp_zone_index == 0:
            Log.logger.info("step 3")
            relay.relay_is_on = power_state
            commit()
            Log.logger.info("step 4")
            # dispatch as UI action otherwise change actions are not triggered
            dispatcher.send(signal=Constant.SIGNAL_UI_DB_POST, model=models.ZoneCustomRelay, row=relay)
            msg = "Set relay {} to state {} zone_index={}\n".format(relay_name, power_state, amp_zone_index)
            Log.logger.info(msg)
        else:
            Log.logger.info("step 5")
            msg = "Not changed relay state for {}\n".format(relay_name)
    else:
        msg = "Could not find relay name {}\n".format(relay_name)
        Log.logger.warning(msg)
        return msg

    Log.logger.info("step 5")
    # change amp zone power
    if amp_zone_index is None or amp_zone_index == 0:
        # only main relay change is needed
        Log.logger.info("step 6")
        return msg + "Power in {} set to {}\n".format(relay_name, relay.relay_is_on)
    else:
        Log.logger.info("step 7")
        # potentially amp settings change is required to switch amp zones
        if initial_relay_state is not True and power_state is True:
            # delay to wait for amp to fully start
            Log.logger.info("step 8")
            time.sleep(5)
        Log.logger.info("step 9")
        return msg + amp_zone_power(power_state, amp_zone_index)
