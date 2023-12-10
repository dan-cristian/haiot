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

    start_keyword_ecu[2] = 'Lifetime generation</th>\\r\\n        <td>'
    end_keyword_ecu[2] = ' kWh </td>'
    start_keyword_now_ecu[2] = 'Last System Power</th>\\r\\n        <td>'
    end_keyword_now_ecu[2] = ' W </td>'

    start_first_panel[1] = "Reporting Time</th>\\r\\n      </tr>\\r\\n    </thead>\\r\\n    <tbody>\\r\\n        <div>\\r\\n            <tr class=\\'active\\'>\\r\\n        <td>"
    end_panel[1] = " </td>"
    start_next_panel[1] = "<tr class=\\'active\\'>\\r\\n        <td>"

    start_first_panel[2] = "Reporting Time</th>\\r\\n      </tr>\\r\\n    </thead>\\r\\n    <tbody>\\r\\n        <div>\\r\\n            <tr class=\\'active\\'>\\r\\n        <td>"
    end_panel[2] = " </td>"
    start_next_panel[2] = "<tr class=\\'active\\'>\\r\\n        <td>"

    APS_TIMEOUT = 10

    def __init__(self):
        pass


def parse_general(inverter):
    index = inverter.type
    try:
        aps_text = str(urllib.request.urlopen(inverter.general_url).read())
        last_power = utils.parse_text(aps_text, P.start_keyword_now_ecu[index], P.end_keyword_now_ecu[index])
        production = utils.parse_text(aps_text, P.start_keyword_ecu[index], P.end_keyword_ecu[index])
        if production is not None:
            production = production.replace(",", "")
        inverter.last_power = int(last_power)
        inverter.lifetime_generation = float(production)
        inverter.save_changed_fields()
    except Exception as ex:
        L.l.error("Exception on inverter {} general run, ex={}".format(inverter.name, ex))


def parse_panels(inverter):
    index = inverter.type
    try:
        aps_text = str(urllib.request.urlopen(inverter.panels_url).read())
        found_panel = True
        end_index = 0
        row_count = 0
        # use exact start pattern for first row
        next_panel, end_index = utils.parse_text(
            aps_text, P.start_next_panel[index], P.end_panel[index], start_index=end_index, return_end_index=True)
        found_panel = next_panel is not None
        while found_panel:
            if found_panel:
                row_count += 1
            panel = m.SolarPanel.find_one({"id": next_panel})
            if found_panel and panel is not None:
                watts, ind = utils.parse_text(aps_text, "<td>", " </td>",
                                              start_index=end_index, return_end_index=True)
                if watts != "-":
                    panel.power = int(watts.replace("W", "").strip())

                if inverter.type == 2:
                    # additional column with DC voltage
                    dc_volt, ind = utils.parse_text(aps_text, "<td>", " </td>",
                                                 start_index=ind, return_end_index=True)
                    if dc_volt != "-":
                        panel.panel_voltage = int(dc_volt.replace("V", "").strip())

                if row_count%2 != 0:
                    hertz, ind = utils.parse_text(aps_text, ">", " </td>",
                                                 start_index=ind, return_end_index=True)
                    if hertz != "-" and hertz is not None:
                        panel.grid_frequency = float(hertz.replace("Hz", "").strip())

                grid_volt, ind = utils.parse_text(aps_text, "<td>", " </td>",
                                             start_index=ind, return_end_index=True)
                if grid_volt != "-":
                    panel.grid_voltage = int(grid_volt.replace("V", "").strip())

                if row_count % 2 != 0:
                    temp, ind = utils.parse_text(aps_text, ">", " </td>",
                                                 start_index=ind, return_end_index=True)
                    if temp != "-":
                        panel.temperature = temp.replace("&#176;C", "").strip()

                    # not used, but needed to parse correctly
                    rep_time, ind = utils.parse_text(aps_text, ">", " </td>",
                                                     start_index=ind, return_end_index=True)
                end_index = ind
                panel.save_changed_fields(persist=True)
                # use different start pattern for row 2nd onwards
                next_panel, end_index = utils.parse_text(aps_text, "<td>", " </td>",
                                                         start_index=end_index, return_end_index=True)
                found_panel = next_panel is not None
            if panel is None:
                L.l.warning("No panel found in config with id {}".format(next_panel))
    except Exception as ex:
        L.l.error("Exception on inverter {} panels run, ex={}".format(inverter.name, ex))


def thread_run():
    inverters = m.MicroInverter.find({"enabled": True})
    for inv in inverters:
        parse_general(inv)
        parse_panels(inv)


def unload():
    thread_pool.remove_callable(thread_run)
    P.initialised = False


def init():
    L.l.info("Starting solar_aps module")
    thread_pool.add_interval_callable(thread_run, run_interval_second=P.interval)
