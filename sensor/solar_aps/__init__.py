__author__ = 'Dan Cristian <dan.cristian@gmail.com>'

import urllib.request
from main.logger_helper import L
from common import Constant, utils, get_json_param
from main import thread_pool
from storage.model import m


class P:
    initialised = False
    interval = 60
    start_keyword_ecu = {}
    end_keyword_ecu = {}
    start_keyword_now_ecu = {}
    end_keyword_now_ecu = {}
    start_first_panel = {}
    end_panel = {}
    start_next_panel = {}

    # APS SOLAR ECU OLD LINK: http://192.168.0.10/cgi-bin/home
    # type 1
    start_keyword_ecu[0] = 'Lifetime generation</td><td align=center>'
    end_keyword_ecu[0] = ' kWh</td>'
    start_keyword_now_ecu[0] = 'Last System Power</td><td align=center>'
    end_keyword_now_ecu[0] = ' W</td>'

    # APS ECU OLD Temperature params: 192.168.0.10/cgi-bin/parameters
    start_key_temp_ecu_old = '<td align=center> '
    end_key_temp_ecu_old = '&nbsp;<sup>o</sup>C'
    start_key_panel_ecu_old = '<td align=center>'
    end_key_panel_ecu_old = '-A</td>'

    # APS SOLAR ECU NEW LINK: http://192.168.0.40/index.php/home
    start_keyword_ecu[1] = 'Lifetime generation</th>\\r\\n        <td>'
    end_keyword_ecu[1] = ' kWh </td>'
    start_keyword_now_ecu[1] = 'Last System Power</th>\\r\\n        <td>'
    end_keyword_now_ecu[1] = ' W </td>'

    start_first_panel[1] = "Reporting Time</th>\\r\\n      </tr>\\r\\n    </thead>\\r\\n    <tbody>\\r\\n        <div>\\r\\n            <tr class=\\'active\\'>\\r\\n        <td>"
    end_panel[1] = " </td>"
    start_next_panel[1] = "<tr class=\\'active\\'>\\r\\n        <td>"


    APS_TIMEOUT = 10

    def __init__(self):
        pass


def parse_general(inverter):
    index = inverter.type
    try:
        aps_text = str(urllib.request.urlopen(inverter.general_url).read())
        last_power = utils.parse_text(aps_text, P.start_keyword_now_ecu[index], P.end_keyword_now_ecu[index])
        production = utils.parse_text(aps_text, P.start_keyword_ecu[index], P.end_keyword_ecu[index])
    except Exception as ex:
        L.l.error("Exception on inverter {} general run, ex={}".format(inverter.name, ex), exc_info=True)


def parse_panels(inverter):
    index = inverter.type
    try:
        aps_text = str(urllib.request.urlopen(inverter.panels_url).read())
        found_panel = True
        end_index = 0
        while found_panel:
            next_panel, end_index = utils.parse_text(
                aps_text, P.start_next_panel[index], P.end_panel[index], start_index=end_index, return_end_index=True)
            found_panel = next_panel is not None
            if found_panel:
                watts, ind = utils.parse_text(aps_text, "<td>", " </td>",
                                              start_index=end_index, return_end_index=True)
                if watts == "-":
                    watts = None
                hertz, ind = utils.parse_text(aps_text, "middle;\\'>", " </td>",
                                             start_index=ind, return_end_index=True)
                if hertz == "-":
                    hertz = None
                else:
                    hertz = hertz.split(" ")[0]
                volt, ind = utils.parse_text(aps_text, "<td>", " </td>",
                                             start_index=ind, return_end_index=True)
                if volt == "-":
                    volt = None
                else:
                    volt = volt.split(" ")[0]
                temp, ind = utils.parse_text(aps_text, "middle;\\'>", " </td>",
                                             start_index=ind, return_end_index=True)
                if temp == "-":
                    temp = None
                else:
                    temp = temp.split(" ")[0]
                panel = m.SolarPanel.find_one({"id": next_panel})
                if panel is None:
                    panel = m.SolarPanel()
                    panel.id = next_panel
                if watts is not None:
                    panel.power = watts
                if volt is not None:
                    panel.voltage = volt
                if hertz is not None:
                    panel.grid_frequency = hertz
                if temp is not None:
                    panel.temperature = temp
                if watts or volt or hertz or temp:
                    panel.save_changed_fields(persist=True)
    except Exception as ex:
        L.l.error("Exception on inverter {} panels run, ex={}".format(inverter.name, ex), exc_info=True)


def thread_run():
    inverters = m.Inverter.find({"enabled": True})
    for inv in inverters:
        parse_general(inv)
        parse_panels(inv)


def unload():
    thread_pool.remove_callable(thread_run)
    P.initialised = False


def init():
    L.l.info("Starting solar_aps module")
    thread_pool.add_interval_callable(thread_run, run_interval_second=P.interval)
