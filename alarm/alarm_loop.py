__author__ = 'dcristian'

# ! /usr/bin/env python
import socket
import subprocess
import select
import urllib2
import urllib

from main.logger_helper import Log
from common import Constant, utils
from main.admin import model_helper
import transport




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
        transport.send_message_obj(message)
    else:
        print ("Invalid line " + line)


def get_prefix(pinindex, value):
    prefix = '{"host_origin":"%s", "command":"alarmevent", "datetime":"%s", "pinindex":"%s", "value":"%s"' % (
    socket.gethostname(),
    urllib.quote(str(utils.get_base_location_now_date())), pinindex, value)
    return prefix


def alert(pinindex, status):
    host = model_helper.get_param(Constant.P_MZP_SERVER_URL)
    request = host + 'cmd?command=alarmevent&pinindex=' + pinindex \
              + '&status=' + status + '&datetime=' + urllib.quote(str(utils.get_base_location_now_date())) + '&action=none'
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
        Log.logger.info('Watching file ' + gpio_file)
        tailproc = subprocess.Popen(['tail', '-f', gpio_file], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if Constant.OS in Constant.OS_LINUX:
            tailpipe = select.poll()
            tailpipe.register(tailproc.stdout)
        else:
            Log.logger.critical('Publish GPIO via tail -f not available in OS ' + Constant.OS)
    except WindowsError:
        Log.logger.warning('Cannot open tail, maybe not running on Linux, os='+ Constant.OS)

def unload():
    # Blocking call that processes network traffic, dispatches callbacks and
    # handles reconnecting.
    # Other loop*() functions are available that give a threaded interface and a
    # manual interface.
    global tailpipe
    tailpipe.terminate()

def thread_run():
    if Constant.OS in Constant.OS_LINUX:
        global tailpipe, tailproc
        if tailpipe.poll(1):
            do_line(tailproc.stdout.readline())
    else:
        Log.logger.warning('Ignoring read alarm tail file in OS ' + Constant.OS)
    return 'Alarm ok'

