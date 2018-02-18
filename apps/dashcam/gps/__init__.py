import gpsd
import urllib2
import ssl
import time
import datetime
import json
import os
from collections import namedtuple
from main.logger_helper import L
from pydispatch import dispatcher
try:
    from common import Constant
    from main.admin import models
except Exception, ex:
    print "Exception {} on gps import".format(ex)

initialised = False
Position = namedtuple('Position', 'lat lon alt sats_valid acc bat timestamp')


class State:
    context = ssl._create_unverified_context()
    url_timeout = 10
    device_name = "skoda"
    disk_pos_buffer_file="/home/haiot/gps_positions"
    have_internet_file = '/tmp/haveinternet'
    UPLOAD_SERVER_URL = "https://www.dancristian.ro/nextcloud/index.php/apps/phonetrack/log/gpslogger/" \
                        "643fee139ee4efd90437176e88298a94/{}?lat=<lat>&lon=<lon>&sat=<sat>&alt=<alt>&acc=<acc>&" \
                        "timestamp=<time>&bat=<bat>".format(device_name)
    url_buffer = []
    pos_buffer = []
    # timestamp with moves that helps reducing gps report frequency
    #last_vibrate = None
    #last_move_inside = None
    #last_move_outside = None
    reported_no_fix = False


def _save_position():
    # persist to disk in case of outage
    with open(State.disk_pos_buffer_file, 'w') as outfile:
        try:
            json.dump(State.pos_buffer, outfile)
            L.l.info("Saved {} positions to disk".format(len(State.pos_buffer)))
        except Exception, ex:
            L.l.error("Cannot save gps positions to {}, err={}".format(State.disk_pos_buffer_file, ex))


def _load_positions():
    if os.path.isfile(State.disk_pos_buffer_file):
        try:
            if os.path.getsize(State.disk_pos_buffer_file) > 0:
                with open(State.disk_pos_buffer_file, 'r') as infile:
                    State.pos_buffer = json.load(infile)
                    i = 0
                    for pos in State.pos_buffer:
                        State.pos_buffer[i] = Position(*pos)
                        i += 1
                    L.l.info("Loaded {} positions from disk".format(len(State.pos_buffer)))
        except Exception, ex:
            L.l.error("Cannot load gps positions from {}, err={}".format(State.disk_pos_buffer_file, ex))


def _upload_pos_buffer():
    if os.path.isfile(State.have_internet_file):
        initial = len(State.pos_buffer)
        url = None
        for p in list(State.pos_buffer):
            try:
                url = State.UPLOAD_SERVER_URL.replace("<lat>", str(p.lat)).replace("<lon>", str(p.lon)).replace(
                    "<alt>", str(p.alt)).replace("<sat>", str(p.sats_valid)).replace(
                    "<acc>", str(p.acc)).replace("<bat>", str(p.bat)).replace("<time>", str(p.timestamp))
                # https://stackoverflow.com/questions/27835619/urllib-and-ssl-certificate-verify-failed-error
                f = urllib2.urlopen(url, timeout=State.url_timeout, context=State.context)
                resp = f.read()
                if resp == "null":
                    State.pos_buffer.remove(p)
                else:
                    L.l.info("Unexpected response {}".format(resp))
            except Exception, ex:
                L.l.info("Unable to upload position, err={}".format(ex))
                L.l.info("Buffer has {} elements".format(len(State.pos_buffer)))
                L.l.info("URL WAS:{}".format(url))
        if (initial > 1) and (initial - len(State.pos_buffer) > 1):
            L.l.info("Buffer catches up, now has {} elements".format(len(State.pos_buffer)))
        if len(State.pos_buffer) > 0:
            _save_position()
        else:
            if os.path.isfile(State.disk_pos_buffer_file):
                os.remove(State.disk_pos_buffer_file)


# https://github.com/MartijnBraam/gpsd-py3/blob/master/DOCS.md
def _read_gps():
    r = gpsd.get_current()
    if r.mode < 2:
        if not State.reported_no_fix:
            L.l.info("No gps fix, sats={} valid={} mode={}".format(r.sats, r.sats_valid, r.mode))
            State.reported_no_fix = True
        pass
    else:
        if State.reported_no_fix:
            L.l.info("Got gps fix, sats={} valid={} mode={}".format(r.sats, r.sats_valid, r.mode))
            State.reported_no_fix = False
        if r.mode == 2:
            alt = -1
        else:
            alt = r.alt
        pos = Position(lat=r.lat, lon=r.lon, alt=alt, sats_valid=r.sats_valid, acc=r.position_precision()[0],
                       bat=r.hspeed, timestamp=time.time())
        # use battery fields to report horizontal speed
        #Log.logger.info("Got gps position {}".format(pos))
        dispatcher.send(Constant.SIGNAL_GPS, lat=r.lat, lon=r.lon, hspeed=r.hspeed, alt=alt)
        State.pos_buffer.append(pos)
        d = models.Device
        dev = d().query_filter_first(d.name == State.device_name)
        if dev is not None:
            p = models.Position
            pos = p().query_filter_first(p.device_id == dev.id)
            if pos is not None:
                pos.latitude = r.lat
                pos.longitude = r.lon
                pos.hprecision = r.position_precision()[0]
                pos.vprecision = r.position_precision()[1]
                pos.hspeed = r.hspeed
                pos.vspeed = r.vspeed
                pos.satellite = r.sats
                pos.satellite_valid = r.sats_valid
                models.commit()

'''
def _upload_buffer():
    initial = len(State.url_buffer)
    for url in list(State.url_buffer):
        try:
            #f = urllib.urlopen(url)
            # https://stackoverflow.com/questions/27835619/urllib-and-ssl-certificate-verify-failed-error
            f = urllib2.urlopen(url, timeout=State.url_timeout, context=State.context)
            resp = f.read()
            if resp == "null":
                State.url_buffer.remove(url)
            else:
                Log.logger.info("Unexpected response {}".format(resp))
        except Exception, ex:
            Log.logger.info("Unable to upload position, err={}".format(ex))
            #State.url_buffer.append(url)
            Log.logger.info("Buffer has {} elements".format(len(State.url_buffer)))
    if initial - len(State.url_buffer) > 1:
        Log.logger.info("Buffer catches up, now has {} elements".format(len(State.url_buffer)))
'''


def unload():
    global initialised
    gpsd.gpsd_socket.close()
    initialised = False


def init():
    global initialised
    _load_positions()
    if len(State.pos_buffer) > 0:
        _upload_pos_buffer()
    try:
        gpsd.connect()
        initialised = True
    except Exception, ex:
        L.l.info("Unable to connect to gps daemon, ex={}".format(ex))
        initialised = False


def thread_run():
    if initialised:
        _read_gps()
    else:
        init()
    _upload_pos_buffer()


if __name__ == "__main__":
    p = Position(lat=1.22,lon=2.45,alt=10,sats_valid=3,acc=2,bat=5,timestamp=1000)
    print json.dumps(p)
    pass
