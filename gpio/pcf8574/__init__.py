from pcf8574 import PCF8574

def init():
    i2c_port_num = 1
    pcf_address = 0x24
    pcf = PCF8574(i2c_port_num, pcf_address)
    pcf.port[0] = False
    print pcf.port
