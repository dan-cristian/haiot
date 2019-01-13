from main.logger_helper import L


class P:
    pcf = None
    i2c_port_num = 1
    pcf_address = 0x24
    import_module_exist = None

    def __init__(self):
        pass


try:
    from pcf8574 import PCF8574
    P.import_module_exist = True
except ImportError:
    L.l.info('Module PCF8574 is not installed, module will not be initialised')


def init():
    P.pcf = PCF8574(P.i2c_port_num, P.pcf_address)

pcf.port[0] = False
print pcf.port
