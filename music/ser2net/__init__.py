from main.logger_helper import Log
from main.admin.model_helper import get_param
from common import Constant
import socket

_AMP_OFF = "\x0207A1E\x03"
_AMP_ON = "\x0207A1D\x03"
_AMP_BI_ON = "\x022BB00\x03"
_AMP_BI_OFF = "\x022BB01\x03"


def connect_socket():
    host = get_param(Constant.P_AMP_SERIAL_HOST)
    port = get_param(Constant.P_AMP_SERIAL_PORT)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))
    return s


def amp_on_yamaha():
    global _AMP_BI_ON
    sock = connect_socket()
    sock.send(_AMP_BI_ON)
    data = sock.recv(1)
    sock.close()
    return data
