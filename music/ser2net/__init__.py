from main.logger_helper import Log
from main.admin.model_helper import get_param
from common import Constant
import socket
import time
import binascii

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
    return 'power on={} result={}'.format(on, result)