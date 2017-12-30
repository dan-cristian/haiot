import gpsd
import urllib2
import ssl
import time
import json
import os
from main.admin import models

initialised = False


class State:
    context = ssl._create_unverified_context()
    url_timeout = 5
    device_name = "skoda"
    disk_pos_buffer_file="/home/haiot/gps_positions"
    UPLOAD_SERVER_URL = "https://www.dancristian.ro/nextcloud/index.php/apps/phonetrack/log/gpslogger/" \
                        "643fee139ee4efd90437176e88298a94/{}?lat=<lat>&lon=<lon>&sat=<sat>&alt=<alt>&acc=<acc>&" \
                        "timestamp=<time>&bat=<bat>".format(device_name)
    last = None
    url_buffer = []
    pos_buffer = []
    # timestamp with moves that helps reducing gps report frequency
    last_vibrate = None
    last_move_inside = None
    last_move_outside = None
    reported_no_fix = False


class Position:
    def __init__(self, lat, lon, alt, sats_valid, acc, bat, timestamp):
        self.lat, self.lon, self.alt, self.sats_valid =lat, lon, alt, sats_valid
        self.acc, self.bat, self.timestamp = acc, bat, timestamp


def _save_position():
    # persist to disk in case of outage
    #with open(State.disk_pos_buffer_file, 'w') as outfile:
    #    json.dump(State.pos_buffer, outfile)
    pass


def _upload_pos_buffer():
    initial = len(State.pos_buffer)
    for p in list(State.pos_buffer):
        try:
            url = State.UPLOAD_SERVER_URL.replace("<lat>", str(p.lat)).replace("<lon>", str(p.lon)).replace(
                "<alt>", str(p.alt)).replace("<sat>", str(p.sats_valid)).replace(
                "<acc>", str(p.acc).replace("<bat>", str(p.bat)).replace("<time>", str(p.timestamp)))
            # https://stackoverflow.com/questions/27835619/urllib-and-ssl-certificate-verify-failed-error
            f = urllib2.urlopen(url, timeout=State.url_timeout, context=State.context)
            resp = f.read()
            if resp == "null":
                State.pos_buffer.remove(url)
            else:
                print("Unexpected response {}".format(resp))
        except Exception, ex:
            print("Unable to upload position, err={}".format(ex))
            print("Buffer has {} elements".format(len(State.pos_buffer)))
            print("URL WAS:{}".format(url))
    if initial - len(State.pos_buffer) > 1:
        print("Buffer catches up, now has {} elements".format(len(State.pos_buffer)))
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
            print("No gps fix, sats={} valid={} mode={}".format(r.sats, r.sats_valid, r.mode))
            State.reported_no_fix = True
        pass
    else:
        if State.reported_no_fix:
            print("Got gps fix, sats={} valid={} mode={}".format(r.sats, r.sats_valid, r.mode))
            State.reported_no_fix = False
        if r.mode == 2:
            alt = -9999
        else:
            alt = r.alt
        pos=Position(lat=r.lat, lon=r.lon, alt=alt, sats_valid=r.sats_valid, acc=r.position_precision()[0],
                     bat=r.hspeed, timestamp=time.time())
        State.pos_buffer.append(pos)
        # use battery fields to report horizontal speed
        #url = State.UPLOAD_SERVER_URL.replace("<lat>", str(r.lat)).replace("<lon>", str(r.lon)).replace(
        #    "<alt>", str(alt)).replace("<sat>", str(r.sats_valid)).replace(
        #    "<acc>", str(r.position_precision()[0])).replace("<bat>", str(r.hspeed)).replace("<time>", str(time.time()))
        # put this first, but might not work
        #State.url_buffer.insert(1, url)
        #State.url_buffer.append(url)
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
                print("Unexpected response {}".format(resp))
        except Exception, ex:
            print("Unable to upload position, err={}".format(ex))
            #State.url_buffer.append(url)
            print("Buffer has {} elements".format(len(State.url_buffer)))
    if initial - len(State.url_buffer) > 1:
        print("Buffer catches up, now has {} elements".format(len(State.url_buffer)))
'''

def unload():
    global initialised
    gpsd.gpsd_socket.close()
    initialised = False


def init():
    global initialised
    try:
        gpsd.connect()
        initialised = True
    except Exception, ex:
        print("Unable to connect to gps daemon, ex={}".format(ex))
        initialised = False


def thread_run():
    if initialised:
        _read_gps()
    else:
        init()
    _upload_pos_buffer()


if __name__ == "__main__":
    init()
    while True:
        thread_run()
        time.sleep(10)
