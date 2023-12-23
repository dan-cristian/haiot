import os
import uuid
import json
import re
import datetime
import time
import calendar
import math
import importlib
import subprocess
import ipaddress
import socket
from collections import namedtuple
from common import fix_module, Constant
import _strptime #  workaround to fix this issue: https://www.raspberrypi.org/forums/viewtopic.php?t=166912
from main.logger_helper import L

while True:
    try:
        import pytz
        import urllib.request
        import urllib.parse
        break
    except ImportError as iex:
        if not fix_module(iex):
            break

__author__ = 'dcristian'


# http://stackoverflow.com/questions/6578986/how-to-convert-json-data-into-a-python-object
def _json_object_hook(d):
    return namedtuple('X', d.keys())(*d.values())


def is_date_string(date_str):
    return re.search("....-..-..T..:..:..\.......", date_str)


def date_deserialiser(json_str):
    if is_date_string(json_str):
        new_json = json_str.replace("T", " ")
        return datetime.datetime.strptime(new_json, "%Y-%m-%d %H:%M:%S.%f")
    else:
        return json_str


def date_serialised(obj):
    return obj.isoformat() if hasattr(obj, 'isoformat') else obj


def json2obj(data):
    try:
        # return json.loads(data, object_pairs_hook=date_deserialiser)
        return json.loads(data)
    except Exception as ex:
        L.l.error('json2obj error, ex={} data={}'.format(ex, data), exc_info=True)
        return None


# this function takes objects that can be safely serialised
def safeobj2json(obj):
    return json.dumps(obj, default=date_serialised)


def unsafeobj2json(obj):
    safe_obj = {}
    for attr in dir(obj):
        if not attr.startswith('_') and '(' not in attr \
                and attr != 'query' and not callable(getattr(obj, attr))\
                and attr != 'metadata':
            value = getattr(obj, attr)
            # only convert to json simple primitives
            if value is not None and not hasattr(value, '_sa_class_manager'):
                safe_obj[attr] = value
    return safeobj2json(safe_obj)


def get_object_name(obj):
    return str(obj._sa_class_manager.itervalues().next()).split('.')[0]


def get_object_field_value(obj=None, field_name=None):
    # field_name = str(field_obj).split('.')[1]
    if not obj:
        obj = {}
    #if obj.has_key(field_name):
    if field_name in obj:
        return obj[field_name]
    else:
        return None


#
def get_model_field_name(field_obj):
    val = str(property(field_obj).fget)
    words = val.split('.')
    if len(words) > 1:
        return words[1]
    else:
        L.l.critical('Unexpected words count in get_model_field_name={}'.format(field_obj))
        return None


def parse_to_date(strdate):
    if re.search("....-..-..T..:..:..\.......", strdate) or \
            re.search("....-..-.. ..:..:..\.......", strdate):
            strdate = strdate.replace('T', ' ')
            strdate = datetime.datetime.strptime(strdate, "%Y-%m-%d %H:%M:%S.%f")
    else:
        L.l.warning('Warning, unexpected date format in parse []'.format(strdate))
    return strdate


def get_table_name(model_obj):
    parts = str(model_obj).split('.')
    table = parts[len(parts)-1].split('\'')
    return table[0]


def round_sensor_value(val):
    return math.ceil(float(val)*10)/10


# http://pytz.sourceforge.net/, get date in a naive format
# http://stackoverflow.com/questions/12691081/from-a-timezone-and-a-utc-time-get-the-difference-in-seconds-vs-local-time-at-t
def get_base_location_now_date():
    tz_base_name = pytz.country_timezones['ro'][0]
    tz = pytz.timezone(tz_base_name)
    utc = pytz.timezone('UTC')
    now = datetime.datetime.utcnow()
    utc.localize(datetime.datetime.now())
    delta = utc.localize(now) - tz.localize(now)
    local_date_as_base = now + delta
    return local_date_as_base


# http://stackoverflow.com/questions/1176136/convert-string-to-python-class-object
def class_for_name(module_name, class_name):
    # load the module, will raise ImportError if module cannot be loaded
    m = importlib.import_module(module_name)
    # get the class, will raise AttributeError if class cannot be found
    c = getattr(m, class_name)
    return c


def add_months(sourcedate, months):
    month = sourcedate.month - 1 + months
    year = int(sourcedate.year + month / 12)
    month = month % 12 + 1
    day = min(sourcedate.day, calendar.monthrange(year, month)[1])
    return datetime.date(year, month, day)


def json_to_record(table, json_object):
    for field in json_object:
        if hasattr(table, field):
            # fixme: really bad performance
            if is_date_string(str(json_object[field])):
                value = date_deserialiser(str(json_object[field]))
            else:
                value = json_object[field]
            setattr(table, field, value)
    return table


def parse_text(text, start_key, end_key, start_index=0, end_first=False, return_end_index=False):
    try:
        if end_first:
            end = text.find(end_key, start_index)
            start = text.rfind(start_key, 0, end)
        else:
            start = text.find(start_key, start_index)
            end = text.find(end_key, start)
        if start != -1 and end != -1:
            val_start = start + len(start_key)
            value_str = text[val_start:end]
            if return_end_index:
                return value_str, val_start + len(value_str) + len(end_key)
            else:
                return value_str
    except Exception as ex:
        L.l.error('Unable to parse text {}, err={}'.format(text, ex))
    if return_end_index:
        return None, 0
    else:
        return None


def parse_text_ex(text, start_key, end_key):
    try:
        start = text.find(start_key)
        if start != -1:
            end = text.find(end_key, start)
            if end != -1:
                val_start = start + len(start_key)
                value_str = text[val_start:end]
                return value_str
    except Exception as ex:
        L.l.error('Unable to parse text {}, err={}'.format(text, ex))
    return None


def get_url_content(url, timeout=None, silent=False):
    try:
        if timeout is None:
            return str(urllib.request.urlopen(url).read())
        else:
            return str(urllib.request.urlopen(url, timeout=timeout).read())
    except Exception as ex:
        if not silent:
            L.l.error("Failed to get url content {}, ex={}".format(url, ex))
        return None


def encode_url_request(request):
    return urllib.parse.quote_plus(request)


def parse_http(url, start_key, end_key, end_first=False, timeout=None, silent=False):
    try:
        text = get_url_content(url=url, timeout=timeout, silent=silent)
        if text is not None:
            return parse_text(text, start_key, end_key, end_first)
    except Exception as ex:
        L.l.error('Unable to open url {}, err={}'.format(url, ex))
        pass
    return None


def sleep(secs):
    time.sleep(secs)


def dump_primitives_as_text(obj):
    res = ''
    attr_list = [a for a in dir(obj) if not a.startswith('_') and not callable(getattr(obj, a))
                 and not hasattr(getattr(obj, a), '__dict__')]
    for item in attr_list:
        value = getattr(obj, item)
        res = '{}{}={}, '.format(res, item, value)
    return res


def get_primitives(obj):
    attr_list = [a for a in dir(obj) if not a.startswith('_') and not callable(getattr(obj, a))
                 and not hasattr(getattr(obj, a), '__dict__')]
    return attr_list


def is_primitive(name, obj):
    return not name.startswith('_') and not callable(obj) and not hasattr(obj, '__dict__')


def _json_object_hook(d):
    return namedtuple('X', d.keys())(*d.values())


def json2obj_v2(data):
    return json.loads(data, object_hook=_json_object_hook)


# https://stackoverflow.com/questions/1305532/convert-nested-python-dict-to-object
class Struct:
    def __init__(self, **entries):
        self.__dict__.update(entries)


def multikeysort(items, columns):
    from operator import itemgetter
    comparers = [((itemgetter(col[1:].strip()), -1) if col.startswith('-') else (itemgetter(col.strip()), 1))
                 for col in columns]

    def cmp_x(a, b):
        return (a > b) - (a < b)

    def comparer(left, right):
        for fn, mult in comparers:
            result = cmp_x(fn(left), fn(right))
            if result:
                return mult * result
            else:
                return 0
    return sorted(items, cmp=comparer)


def get_my_network_ip_list():
    # get my ip
    ip = ([l for l in ([ip for ip in socket.gethostbyname_ex(socket.gethostname())[2]
                        if not ip.startswith("127.")][:1], [[(s.connect(('8.8.8.8', 53)),
                                                              s.getsockname()[0], s.close()) for s in
                                                             [socket.socket(socket.AF_INET,
                                                                            socket.SOCK_DGRAM)]][0][1]]) if l][0][0])
    ip_ar = ip.split('.')
    net_addr = ip.replace(ip_ar[len(ip_ar) - 1], "0/24")
    net_addr = net_addr.replace('10/', '').repplace('/24', '')
    # pings all hosts in my network
    try:
        ip_net = ipaddress.ip_network(net_addr)
        all_hosts = list(ip_net.hosts())
    except ipaddress.AddressValueError as ex:
        L.l.error("Unable to get IP address from string {}, ex={}".format(net_addr, ex))
    return all_hosts


def ping_my_network():

    # Configure subprocess to hide the console window
    # info = subprocess.STARTUPINFO()
    # info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    # info.wShowWindow = subprocess.SW_HIDE

    # For each IP address in the subnet,
    # run the ping command with subprocess.popen interface
    for i in range(len(all_hosts)):
        output = subprocess.Popen(['ping', '-c', '1', '-w', '1', '-s', '1', str(all_hosts[i])], stdout=subprocess.PIPE,
                                  # startupinfo=info
                                  ).communicate()[0]
        L.l.info("Pinged {}".format(all_hosts[i]))


def init_debug():
    try:
        import ptvsd
        ptvsd.enable_attach(address=('0.0.0.0', 5678), redirect_output=True)
        print('Enabled remote debugging, waiting 15 seconds for client to attach')
        ptvsd.wait_for_attach(timeout=15)
        breakpoint()
    except Exception as ex:
        print("Error in remote debug: {}".format(ex))


def moving_average(number_list, window_size):
    i = 0
    moving_averages = []
    while i < len(number_list) - window_size + 1:
        this_window = number_list[i: i + window_size]
        window_average = sum(this_window) / window_size
        moving_averages.append(window_average)
        i += 1
    return moving_averages


def split_average(number_list):
    first_count = int(len(number_list) / 2)
    first_list = number_list[:first_count]
    first_avg = sum(first_list) / len(first_list)
    second_count = len(number_list) - first_count
    second_list = number_list[-second_count:]
    second_avg = sum(second_list) / len(second_list)
    return [first_avg, second_avg]
