import gpsd
import urllib2
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
        url = State.UPLOAD_SERVER_URL.replace("<lat>", r.lat).replace("<lon>", r.lon).replace("<alt>", alt).replace(
            "<sat>", r.sats_valid).replace("<acc>", r.position_precision()[0]).replace("<bat>", r.hspeed).replace(
            "<time>", time.time())
        State.url_buffer.insert(0, url)


def _upload_buffer():
    for url in list(State.url_buffer):
        try:
            response = urllib2.urlopen(url, timeout=State.url_timeout)
            # Read the body
            body = response.read()
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
