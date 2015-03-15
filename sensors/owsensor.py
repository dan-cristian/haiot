'''
Created on Mar 9, 2015

@author: dcristian
'''
import pyownet.protocol
import time
import datetime
import socket
import threading
from pydispatch import dispatcher
import common.constant

class Sensor(object):
    '''
    classdocs
    '''
    list = {}
    
    def __init__(self, address, type):
        '''
        Constructor
        '''
        self.address = address
        self.type = type
        self.temperature = None
        self.humidity = None
        self.iad = None
        self.vdd = None
        self.vad = None
        self.counters_A = None
        self.counters_B = None
        self.pio_A = None
        self.pio_B = None
        self.sensed_A = None
        self.sensed_B = None

    def __str__(self):
        return str(self.address) + "-" + str(self.type)
    def __repr__(self):
        return str(self.address) + "-" + str(self.type)

def loop_read():
    print ("Started owssensor loop")
    try:
        owproxy = pyownet.protocol.proxy(host="192.168.0.113", port=4304)
        while True:
            do_device(owproxy)
            time.sleep(1)
    except:
        print "Unexpected error:", sys.exc_info()[0]
    print ("Exit while loop")


def do_device (owproxy):
    sensors = owproxy.dir('/', slash=True, bus=False)
    for sensor in sensors:
            sensortype = owproxy.read(sensor+'type')
            if sensortype == 'DS2423':
                    dev = get_counter(sensor, owproxy)
            elif sensortype == 'DS2413':
                    dev=get_io(sensor, owproxy)
            elif sensortype == 'DS18B20':
                    dev=get_temperature(sensor, owproxy)
            elif sensortype == 'DS2438':
                    dev=get_temperature(sensor, owproxy)
                    dev=get_voltage(sensor, owproxy)
                    dev=get_humidity(sensor, owproxy)
            elif sensortype=='DS2401':
                    dev=get_bus(sensor, owproxy)
            else:
                    dev=get_unknown(sensor, owproxy)
            dispatcher.send(signal=common.constant.SIGNAL_SENSOR, sender=dev)
            Sensor.list.update({str(dev.address):dev})
            time.sleep(1)
            print ("Sensor count is " + str(len(Sensor.list)) + " on thread " + threading.current_thread().name)

def get_prefix(sensor, owproxy):
        #prefix =  '{"host_origin":"%s", "command":"sensorupdate", "datetime":"%s", "sensor_address":"%s", "type":"%s"' % (socket.gethostname(),
        #        str(datetime.datetime.now()), owproxy.read(sensor+'r_address'), owproxy.read(sensor+'type'))
        dev = Sensor(str(owproxy.read(sensor+'r_address')), str(owproxy.read(sensor+'type')))
        return dev


def get_bus( sensor , owproxy):
        dev = get_prefix(sensor, owproxy)# + '}'
        #message = '{"address":"%s","type":"%s"}' % ((sensor.r_address), (sensor.type))
        #client.publish(topic, message)
        return dev

def get_temperature( sensor , owproxy):
        #message = get_prefix(sensor, owproxy) + ', "temperature":"%s"}' % (owproxy.read(sensor+'temperature').strip())
        dev = get_prefix(sensor, owproxy)
        dev.temperature = owproxy.read(sensor+'temperature').strip()
        #client.publish(topic, message)
        return dev

def get_humidity( sensor , owproxy):
        #message = get_prefix(sensor, owproxy)+', "humidity":"%s"}' % (owproxy.read(sensor+'humidity').strip())
        #client.publish(topic, message)
        dev = get_prefix(sensor, owproxy)
        dev.humidity = owproxy.read(sensor+'humidity').strip()
        return dev

def get_voltage(sensor, owproxy):
        #message = get_prefix(sensor, owproxy)+', "iad":"%s", "vad":"%s", "vdd":"%s"}' % (owproxy.read(sensor+'IAD').strip(),
        #        owproxy.read(sensor+'VAD').strip(), owproxy.read(sensor+'VDD').strip())
        #client.publish(topic, message)
        dev = get_prefix(sensor, owproxy)
        dev.iad = owproxy.read(sensor+'IAD').strip()
        dev.vad= owproxy.read(sensor+'VAD').strip()
        dev.vdd = owproxy.read(sensor+'VDD').strip()
        return dev

def get_counter( sensor , owproxy):
        #message = get_prefix(sensor, owproxy)+', "counter_a":"%s", "counter_b":"%s"}' % (owproxy.read(sensor+'counters.A').strip(),
        #        owproxy.read(sensor+'counters.B').strip())
        #client.publish(topic, message)
        dev = get_prefix(sensor, owproxy)
        dev.counters_A = str(owproxy.read(sensor+'counters.A').strip())
        dev.counters_B = str(owproxy.read(sensor+'counters.B').strip())
        return dev

def get_io( sensor , owproxy):
        #IMPORTANT: do not use . in field names as it throws error on JSON, only use _
        #message = get_prefix(sensor, owproxy)+', "pio_a":"%s", "pio_b":"%s", "sensed_a":"%s", "sensed_b":"%s"}' % (owproxy.read(sensor+'PIO.A').strip(),
        #        owproxy.read(sensor+'PIO.B').strip(), owproxy.read(sensor+'sensed.A'), owproxy.read(sensor+'sensed.B'))
        #print message
        #client.publish(topic, message)
        dev = get_prefix(sensor, owproxy)
        dev.pio_A = owproxy.read(sensor+'PIO.A').strip()
        dev.pio_B = owproxy.read(sensor+'PIO.B').strip()
        dev.sensed_A = owproxy.read(sensor+'sensed.A').strip()
        dev.sensed_B = owproxy.read(sensor+'sensed.B').strip()
        return dev

def get_unknown (sensor, owproxy):
        #print sensor.entryList()
        dev = get_prefix(sensor, owproxy)
        #client.publish(topic, message)
        return dev

if __name__ == '__main__':
    pass