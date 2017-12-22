import gpsd
import urllib2
import urllib
import time
initialised = False


class State:
    url_timeout = 5
    device_name = "skoda"
    UPLOAD_SERVER_URL = "https://www.dancristian.ro/nextcloud/index.php/apps/phonetrack/log/gpslogger/" \
                        "643fee139ee4efd90437176e88298a94/{}?lat=<lat>&lon=<lon>&sat=<sat>&alt=<alt>&acc=<acc>&" \
                        "timestamp=<time>&bat=<bat>".format(device_name)
    last = None
    url_buffer = []


# https://github.com/MartijnBraam/gpsd-py3/blob/master/DOCS.md
def _read_gps():
    r = gpsd.get_current()
    if r.mode < 2:
        print "No gps fix, sats={} valid={}".format(r.sats, r.sats_valid)
    else:
        if r.mode == 2:
            alt = -9999
        else:
            alt = r.alt
        # use battery fields to report horizontal speed
        url = State.UPLOAD_SERVER_URL.replace("<lat>", str(r.lat)).replace("<lon>", str(r.lon)).replace(
            "<alt>", str(alt)).replace("<sat>", str(r.sats_valid)).replace(
            "<acc>", str(r.position_precision()[0])).replace("<bat>", str(r.hspeed)).replace("<time>", str(time.time()))
        State.url_buffer.insert(0, url)


def _upload_buffer():
    for url in list(State.url_buffer):
        try:
            f = urllib.urlopen(url)
            #f = urllib2.urlopen(url, timeout=State.url_timeout, cadefault=True)
            resp = f.read()
            print "Response was {}".format(resp)
            State.url_buffer.remove(url)
        except Exception, ex:
            print ex
            State.url_buffer.append(url)
            print "Buffer has {} elements".format(len(State.url_buffer))


def init():
    global initialised
    gpsd.connect()
    initialised = True


def thread_run():
    _read_gps()
    _upload_buffer()


if __name__ == "__main__":
    init()
    while True:
        thread_run()
        time.sleep(10)
