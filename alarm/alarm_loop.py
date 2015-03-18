__author__ = 'dcristian'

# ! /usr/bin/env python
import paho.mqtt.client as mqtt
import time
import json
import socket
from collections import namedtuple
import subprocess
import datetime, logging
import select
import urllib2, urllib
from common import constant
from main.admin import model_helper

#http://owfs.sourceforge.net/owpython.html
topic = "mzp/iot/alarm"
gpio_file = "/tmp/gpio_input.txt"
client = None
client_connected = False
tailproc = None
tailpipe = None
#http://stackoverflow.com/questions/6578986/how-to-convert-json-data-into-a-python-object
def _json_object_hook(d): return namedtuple('X', d.keys())(*d.values())


def json2obj(data): return json.loads(data, object_hook=_json_object_hook)


# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    logging.info("Connected to mqtt with result code " + str(rc))
    client_connected = True

def on_disconnect(client, userdata, rc):
    if rc != 0:
        logging.warning("Unexpected disconnection from mqtt")
    logging.warning("Disconnected from mqtt")
    client_connected = False


def do_line(line):
    atoms = line.split(",")
    if len(atoms) >= 4:
        pinindex = atoms[0]
        gpio = atoms[1]
        value = atoms[2]
        oppresult = atoms[3]
        print ("Processing pin " + pinindex + " gpio " + gpio + " value " + value)
        message = get_prefix(pinindex, value) + '}'
        if value == "1":
            status = "opened"
        else:
            status = "closed"
        alert(pinindex, status, )
        if client_connected:
            client.publish(topic, message)
    else:
        print ("Invalid line " + line)


def get_prefix(pinindex, value):
    prefix = '{"host_origin":"%s", "command":"alarmevent", "datetime":"%s", "pinindex":"%s", "value":"%s"' % (
    socket.gethostname(),
    urllib.quote(str(datetime.datetime.now())), pinindex, value)
    return prefix


def alert(pinindex, status):
    host = model_helper.get_param(constant.PARAM_MZP_SERVER_URL)
    request = host + 'cmd?command=alarmevent&pinindex=' + pinindex \
              + '&status=' + status + '&datetime=' + urllib.quote(str(datetime.datetime.now())) + '&action=none'
    #request=urllib.quote(request)
    print (request)
    try:
        print (urllib2.urlopen(request, timeout=1).read())
    except urllib2.URLError, e:
        print e
    except socket.error, e:
        print e


def init():
    global client
    client = mqtt.Client()
    global client_connected
    client_connected=False
    retry_count=0
    while (not client_connected) and (retry_count < constant.ERROR_CONNECT_MAX_RETRY_COUNT):
        try:
            client.on_connect = on_connect
            client.connect(model_helper.get_param(constant.PARAM_MQTT_HOST), 1883, 60)
            client_connected = True
            #client.on_message = on_message
            client.on_disconnect = on_disconnect
            #client.on_subscribe = on_subscribe
            client.username_pw_set(socket.gethostname())
            client.user_data_set(socket.gethostname() + " userdata")
            client.will_set(socket.gethostname() + " DIE")
            client.loop_start()
        except socket.error:
            logging.error('mqtt client not connected, pause and retry')
            retry_count += 1
            time.sleep(constant.ERROR_CONNECT_PAUSE_SECOND)
    try:
        global tailproc, tailpipe
        logging.info('Watching file ' + gpio_file)
        tailproc = subprocess.Popen(['tail', '-f', gpio_file], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if constant.OS in constant.OS_LINUX:
            tailpipe = select.poll()
            tailpipe.register(tailproc.stdout)
        else:
            logging.critical('Publish GPIO via tail -f not available in OS ' + constant.OS)

    except WindowsError:
        logging.warning('Cannot open tail, maybe not running on Linux, os='+ constant.OS)

def unload():
    # Blocking call that processes network traffic, dispatches callbacks and
    # handles reconnecting.
    # Other loop*() functions are available that give a threaded interface and a
    # manual interface.
    global client, tailpipe
    client.loop_stop()
    tailpipe.terminate()

def thread_run():
    if constant.OS in constant.OS_LINUX:
        global tailpipe, tailproc
        if tailpipe.poll(1):
            do_line(tailproc.stdout.readline())
    else:
        logging.warning('Ignoring read alarm tail file in OS ' + constant.OS)
    return 'Alarm ok'

