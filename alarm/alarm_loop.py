__author__ = 'dcristian'

# ! /usr/bin/env python
import json
import socket
from collections import namedtuple
import subprocess
import datetime, logging
import select
import urllib2, urllib
from common import constant
from main.admin import model_helper
from mqtt_publisher import mqtt_client

#http://owfs.sourceforge.net/owpython.html
topic = "mzp/iot/alarm"
gpio_file = "/tmp/gpio_input.txt"

tailproc = None
tailpipe = None


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
        if mqtt_client.client_connected:
            mqtt_client.publish(topic, message)
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
    global tailpipe
    tailpipe.terminate()

def thread_run():
    if constant.OS in constant.OS_LINUX:
        global tailpipe, tailproc
        if tailpipe.poll(1):
            do_line(tailproc.stdout.readline())
    else:
        logging.warning('Ignoring read alarm tail file in OS ' + constant.OS)
    return 'Alarm ok'

