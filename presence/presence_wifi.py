import subprocess
from main.logger_helper import L
from main.admin import models
from pydispatch import dispatcher
from common import utils, Constant


def _get_wlan():
    wlan = subprocess.check_output(['ifconfig | grep wlan'], shell=True).split(':')
    if len(wlan) >= 1:
        return wlan[0]
    else:
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
                d = models.Device
                dev = d().query_filter_first(d.wifi_address == ssid)
                if dev is not None:
                    dev.last_wifi_active = utils.get_base_location_now_date()
                    dev.last_active = utils.get_base_location_now_date()
                    dev.wifi_signal = signal
                    models.commit()
                    pd = models.PeopleDevice
                    peopledev = pd().query_filter_first(pd.device_id == dev.id)
                    if peopledev is not None and peopledev.give_presence:
                        dispatcher.send(Constant.SIGNAL_PRESENCE, device=dev.name)


def thread_run():
    L.l.debug('Processing presence_run')
    _check_wifi()


if __name__ == '__main__':
    _check_wifi(test=True)