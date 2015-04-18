__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

import logging
import datetime
import dateutil.parser
import json
import requests
from main.admin import model_helper
from common import constant, utils

cache = {}
#record_id can be found on rackspace with a trick. select multiple records and click on Actions / Edit TTL
#then with chrome right click on the list, inspect elements. you will find the A record id in a div

def __update_ddns_rackspace():
    ConfigFile = model_helper.get_param(constant.P_DDNS_RACKSPACE_CONFIG_FILE)
    with open(ConfigFile, 'r') as f:
        config = json.load(f)
    global cache
    if cache == {} or cache == None:
        cache = {}
        cache['ip']=''
        cache['auth']={}
        cache['auth']['expires']=str(datetime.datetime.now())

    # get IP address
    ip = requests.get('http://icanhazip.com').text.strip()
    if ip == '' or ip is None or ip == cache['ip']:
        logging.debug('IP address is still ' + ip + '; nothing to update.')
        exit()
    else:
        logging.info('IP address was changed, old was {} new is {}'.format(cache['ip'], ip))

    cache['ip'] = ip
    now = datetime.datetime.now()
    expires = dateutil.parser.parse(cache['auth']['expires'])
    if expires <= now:
        logging.info('Expired rackspace authentication token; reauthenticating...')
        # authenticate with Rackspace
        authUrl = 'https://identity.api.rackspacecloud.com/v2.0/tokens'
        authData = {
            'auth': {
                'RAX-KSKEY:apiKeyCredentials': {
                    'username': config['username'],
                    'apiKey': config['api_key']
                }
            }
        }
        authHeaders = {
            'Accept': 'application/json',
            'Content-type': 'application/json'
        }
        auth = requests.post(authUrl, data=json.dumps(authData), headers=authHeaders)
        auth = utils.json2obj(auth.text)
        cache['auth']['expires'] = auth['access']['token']['expires']
        cache['auth']['token'] = auth['access']['token']['id']

    # update DNS record
    url = 'https://dns.api.rackspacecloud.com/v1.0/' + config['account_id'] + \
        '/domains/' + config['domain_id'] + '/records/' + config['record_id']

    data = {
        'ttl': config['record_ttl'],
        'name': config['record_name'],
        'data': cache['ip']
    }
    headers = {
        'Accept': 'application/json',
        'Content-type': 'application/json',
        'X-Auth-Token': cache['auth']['token']
    }

    result = requests.put(url, data=json.dumps(data), headers=headers)
    if result.ok:
        logging.info('Updated IP address to ' + cache['ip'])
    else:
        logging.warning('Unable to update IP, response={}'.format(result))


def thread_run():
    logging.debug('Processing ddns_run')
    __update_ddns_rackspace()
    return 'Processed ddns_run'