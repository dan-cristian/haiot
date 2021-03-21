import sys
import time
import serial
import struct
from binascii import unhexlify


#Define RS485 serial port
ser = serial.Serial(
    port='/dev/rfcomm0',
    baudrate=9600,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout=0)

test = bytes([0xDB, 0xDB, 0x00, 0x00, 0x00, 0x00])
try:
    ser.write(test)
except Exception as ex:
    print("Unable to write, ex={}".format(ex))
    ser.close()
time.sleep(3)
Antw33 = ser.read(140)

#SoC
data = (Antw33.encode('hex')[(74*2):(75*2)])
print(data)

#Power
data = (Antw33.encode('hex')[(111*2):(114*2+2)])

if int(data, 16) > 2147483648:
    data = (-(2*2147483648)+int(data, 16))
    print(data)
else:
    data = int(data, 16)
    print(data)
