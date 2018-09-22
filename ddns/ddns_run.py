__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

from main.logger_helper import L

try:
    import dateutil.parser
except ImportError:
    L.l.info('Module dateutil.parser cannot be imported')
import pytz
import threading
import prctl
import json
import socket
import requests
from main.admin import model_helper
from common import Constant, utils

cache = {}


# record_id can be found on rackspace with a trick. select multiple records and click on Actions / Edit TTL
# then with chrome right click on the list, inspect elements. you will find the A record id in a div
# if above is not easy try:
# https://developer.rackspace.com/docs/cloud-dns/v1/developer-guide/#getting-started

def __update_ddns_rackspace():
    try:
        ConfigFile = model_helper.get_param(Constant.P_DDNS_RACKSPACE_CONFIG_FILE)
        with open(ConfigFile, 'r') as f:
            config_list = json.load(f)
        global cache
        if cache == {} or cache is None:
            cache = {}
            cache['auth'] = {}
            cache['auth']['expires'] = str(utils.get_base_location_now_date())
        config = {}
        ip_json_test = ''
        try:
            #ip_json_test = requests.get('http://ip-api.com/json').text
            ip_json_test = requests.get('http://ipinfo.io').text
            ip_json_obj = utils.json2obj(ip_json_test)
            #public_ip = ip_json_obj['query']
            #public_isp = ip_json_obj['isp']
            public_ip = ip_json_obj['ip']
            public_isp = ip_json_obj['org']
        except Exception, ex:
            L.l.warning('Unable to get my ip, err={} text={}'.format(ex, ip_json_test))
            return

        for config in config_list.values():
            # check if public address is for this config dns entry
            isp = config['isp']
            if isp != public_isp:
                continue

            # get IP address
            try:
                cache['ip:'+isp] = socket.gethostbyname(config['record_name'])
            except Exception, ex:
                cache['ip:'+isp] = None
                L.l.warning('Unable to get ip for host {}, err={}'.format(config['record_name'], ex))

            if public_ip == '' or public_ip is None or public_ip == cache['ip:'+isp]:
                L.l.debug('IP address for ' + isp + ' is still ' + public_ip + '; nothing to update.')
                return
            else:
                L.l.info('IP address was changed for {}, old was {} new is {}'.format(
                    isp, cache['ip:'+isp], public_ip))

            cache['ip:'+isp] = public_ip
            now = utils.get_base_location_now_date()
            expires = dateutil.parser.parse(cache['auth']['expires'])
            now = pytz.utc.localize(now)
            expires = pytz.utc.localize(expires)
            if expires <= now:
                L.l.info('Expired rackspace authentication token; reauthenticating...')
                # authenticate with Rackspace
                authUrl = 'https://identity.api.rackspacecloud.com/v2.0/tokens'
                authData = {'auth': {'RAX-KSKEY:apiKeyCredentials': {'username': config['username'],
                                                                     'apiKey': config['api_key']}}}
                authHeaders = {'Accept': 'application/json','Content-type': 'application/json'}
                auth = requests.post(authUrl, data=json.dumps(authData), headers=authHeaders)
                auth = utils.json2obj(auth.text)
                cache['auth']['expires'] = auth['access']['token']['expires']
                cache['auth']['token'] = auth['access']['token']['id']

            # update DNS record
            url = 'https://dns.api.rackspacecloud.com/v1.0/' + config['account_id'] + \
                  '/domains/' + config['domain_id'] + '/records/' + config['record_id']
            data = {'ttl': config['record_ttl'], 'name': config['record_name'], 'data': public_ip}
            headers = {'Accept': 'application/json', 'Content-type': 'application/json',
                       'X-Auth-Token': cache['auth']['token']}
            result = requests.put(url, data=json.dumps(data), headers=headers)
            if result.ok:
                L.l.info('Updated IP address for {} to {}'.format(config['record_name'], public_ip))
            else:
                L.l.warning('Unable to update IP, response={}'.format(result))
    except Exception, ex:
        L.l.warning('Unable to check and update dns, err={}'.format(ex))


def thread_run():
    prctl.set_name("ddns")
    threading.current_thread().name = "ddns"
    L.l.debug('Processing ddns_run')
    __update_ddns_rackspace()
    prctl.set_name("idle")
    threading.current_thread().name = "idle"
    return 'Processed ddns_run'
