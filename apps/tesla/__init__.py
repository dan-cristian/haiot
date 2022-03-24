import threading
import prctl
from main.logger_helper import L
from main import thread_pool

from apps.tesla.TeslaPy.teslapy import Tesla
#from apps.tesla.TeslaPy import menu

__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

class P:
    initialised = False

    def __init__(self):
        pass


def thread_run():
    prctl.set_name("")
    threading.current_thread().name = ""
    #
    prctl.set_name("idle_")
    threading.current_thread().name = "idle_"
    return 'Processed tesla'


def unload():
    L.l.info('Tesla module unloading')
    thread_pool.remove_callable(thread_run)
    P.initialised = False


def init():
    L.l.info('Tesla module initialising')
    thread_pool.add_interval_callable(thread_run, run_interval_second=60)

    email = 'dan.cristian@gmail.com'
    with Tesla(email) as tesla:
        #if (webdriver and args.web is not None) or webview:
        #    tesla.authenticator = custom_auth
        #if args.timeout:
        #    tesla.timeout = args.timeout
        vehicles = tesla.vehicle_list()
        print('-' * 80)
        fmt = '{:2} {:25} {:25} {:25}'
        print(fmt.format('ID', 'Display name', 'VIN', 'State'))
        for i, vehicle in enumerate(vehicles):
            print(fmt.format(i, vehicle['display_name'], vehicle['vin'],
                             vehicle['state']))
        print('-' * 80)
        idx = 0 #  int(raw_input("Select vehicle: "))
        print('-' * 80)
        print('VIN decode:', ', '.join(vehicles[idx].decode_vin().values()))
        print('Option codes:', ', '.join(vehicles[idx].option_code_list()))
        print('-' * 80)
        # menu(vehicles[idx])

    P.initialised = True
