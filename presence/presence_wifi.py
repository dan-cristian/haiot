import subprocess
import threading
import prctl
from main.logger_helper import L
from main import sqlitedb
if sqlitedb:
    from storage.sqalc import models
from pydispatch import dispatcher
from common import utils, Constant
from storage.model import m


def _get_wlan():
    try:
        wlan = subprocess.check_output(['ifconfig | grep wlan'], shell=True).split(':')
        if len(wlan) >= 1:
            return wlan[0]
    except Exception as ex:
        pass
    return None


def _check_wifi(test=False):
    if test:
        wlist = "bssid / frequency / signal level / flags / ssid\n"
        wlist = wlist + "a4:2b:b0:fe:8c:2e       2462    -52     [WPA2-PSK-CCMP][ESS]    home2"
        wlist = wlist.split('\n')
        wl = 'wlan0'
    else:
        wl = _get_wlan()
        if wl is not None:
            wlist = subprocess.check_output(['wpa_cli', '-i', wl, 'scan_results']).split('\n')
        else:
            wlist = []
    if len(wlist) >= 1:
        for line in wlist:
            line = " ".join(line.split())
            atoms = line.split(' ')
            if len(atoms) > 4 and atoms[0] != 'bssid':
                ssid = atoms[0].upper()
                freq = atoms[1]
                signal = atoms[2]
                flags = atoms[3]
                name = atoms[4]
                if sqlitedb:
                    d = models.Device
                    dev = d().query_filter_first(d.wifi_address == ssid)
                else:
                    dev = m.Device.find_one({m.Device.wifi_address: ssid})
                if dev is not None:
                    dev.last_wifi_active = utils.get_base_location_now_date()
                    dev.last_active = utils.get_base_location_now_date()
                    dev.wifi_signal = signal
                    if sqlitedb:
                        models.commit()
                    else:
                        dev.save_changed_fields()
                    if sqlitedb:
                        pd = models.PeopleDevice
                        peopledev = pd().query_filter_first(pd.device_id == dev.id)
                    else:
                        peopledev = m.PeopleDevice.find_one({m.PeopleDevice.device_id: dev.id})
                    if peopledev is not None and peopledev.give_presence:
                        dispatcher.send(Constant.SIGNAL_PRESENCE, device=dev.name)


def thread_run():
    prctl.set_name("presence_wifi")
    threading.current_thread().name = "presence_wifi"
    L.l.debug('Processing presence_run')
    if Constant.is_os_linux():
        _check_wifi()
    prctl.set_name("idle_presence_wifi")
    threading.current_thread().name = "idle_presence_wifi"

