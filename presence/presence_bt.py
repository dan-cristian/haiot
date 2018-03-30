from main.logger_helper import L
import struct
import array
import bluetooth
from pydispatch import dispatcher
from common import utils, Constant
from main.admin import models
try:
    import bluetooth._bluetooth as bt
    import fcntl
    rssi_initialised = True
except Exception:
    rssi_initialised = False

__author__ = 'Dan Cristian<dan.cristian@gmail.com>'


class BluetoothRSSI(object):
    """Object class for getting the RSSI value of a Bluetooth address.
    Reference: https://github.com/dagar/bluetooth-proximity
    """
    def __init__(self, addr):
        self.addr = addr
        self.hci_sock = bt.hci_open_dev()
        self.hci_fd = self.hci_sock.fileno()
        self.bt_sock = bluetooth.BluetoothSocket(bluetooth.L2CAP)
        self.bt_sock.settimeout(10)
        self.connected = False
        self.cmd_pkt = None

    def prep_cmd_pkt(self):
        """Prepares the command packet for requesting RSSI"""
        reqstr = struct.pack("6sB17s", bt.str2ba(self.addr), bt.ACL_LINK, "\0" * 17)
        request = array.array("c", reqstr)
        handle = fcntl.ioctl(self.hci_fd, bt.HCIGETCONNINFO, request, 1)
        handle = struct.unpack("8xH14x", request.tostring())[0]
        self.cmd_pkt = struct.pack('H', handle)

    def connect(self):
        """Connects to the Bluetooth address"""
        self.bt_sock.connect_ex((self.addr, 1))  # PSM 1 - Service Discovery
        self.connected = True

    def get_rssi(self):
        """Gets the current RSSI value.
        @return: The RSSI value (float) or None if the device connection fails
                 (i.e. the device is nowhere nearby).
        """
        try:
            # Only do connection if not already connected
            if not self.connected:
                self.connect()
            if self.cmd_pkt is None:
                self.prep_cmd_pkt()
            # Send command to request RSSI
            rssi = bt.hci_send_req(self.hci_sock, bt.OGF_STATUS_PARAM,
                                   bt.OCF_READ_RSSI, bt.EVT_CMD_COMPLETE, 4, self.cmd_pkt)
            rssi = struct.unpack('b', rssi[3])[0]
            return rssi
        except IOError:
            # Happens if connection fails (e.g. device is not in range)
            self.connected = False
            return None


def _check_presence():
    devs = models.Device().query_filter_all()
    for dev in devs:
        if dev.bt_address is not None:
            result = None
            btrssi = None
            try:
                result = bluetooth.lookup_name(dev.bt_address.upper(), timeout=2)
            except Exception, ex:
                print "BT scan error: {}".format(ex)
            if result is not None:
                try:
                    #if rssi_initialised:
                    #    btrssi = BluetoothRSSI(addr=dev.bt_address.upper())
                    dev.last_bt_active = utils.get_base_location_now_date()
                    dev.last_active = utils.get_base_location_now_date()
                    models.commit()
                    pd = models.PeopleDevice
                    peopledev = pd().query_filter_first(pd.device_id == dev.id)
                    if peopledev is not None and peopledev.give_presence:
                        p = models.People
                        people = p().query_filter_first(p.id == peopledev.people_id)
                        if people is not None:
                            dispatcher.send(Constant.SIGNAL_PRESENCE, device=dev.name, people=people.name)
                            #if btrssi is not None:
                            #    print "Rssi for {}={}".format(people.name, btrssi.get_rssi())
                except Exception, ex:
                    print "Error on bt presence".format(ex)


def _list_all():
    #result = bluetooth.lookup_name('E0:DB:10:1E:E0:8A', timeout=2)
    btrssi = BluetoothRSSI(addr='E0:DB:10:1E:E0:8A')
    nearby_devices = bluetooth.discover_devices(duration=8, lookup_names=True, flush_cache=True, lookup_class=False)
    print "A"


def thread_run():
    L.l.debug('Processing presence_run')
    _check_presence()
    return 'Processed presence_run'


if __name__ == '__main__':
    _list_all()
    thread_run()
