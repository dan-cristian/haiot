#!/usr/bin/env python

# Newtifry - Python server push script.
#
# Copyright 2011 Daniel Foote & thunder
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
#
# This script sends the notification to the backend server for the given source.
# Return codes:
# 0 - Success
# 1 - HTTP error
# 2 - Backend error

import urllib
import urllib2
import json
from main.logger_helper import L
from common import Constant, utils
from main.admin import model_helper
from pydispatch import dispatcher
from main import thread_pool
import threading
import datetime
import prctl

__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

# Configuration.
BACKEND = 'https://newtifry.appspot.com/newtifry'
initialised = False
_message_queue = []
__queue_lock = threading.Lock()
_source_key = ''
_last_send_date = datetime.datetime.min


def _send_queue():
    prctl.set_name("newtifry")
    threading.current_thread().name = 'newtifry'
    global _source_key, _last_send_date, _message_queue

    if len(_message_queue) == 0:
        return

    params = {}
    params['format'] = 'json'
    params['source'] = _source_key
    if len(_message_queue) > 1:
        params['title'] = 'Multiple notifs: %s [%s]' % (_message_queue[0].title, Constant.HOST_NAME)
    else:
        params['title'] = '%s [%s]' % (_message_queue[0].title, Constant.HOST_NAME)
    global __queue_lock
    try:
        __queue_lock.acquire()
        params['message'] = ''
        params['priority'] = 0
        for item in _message_queue:
            if item.title is not None:
                params['message'] += 'Title: {}\n'.format(item.title)
            if item.message is not None:
                params['message'] += '{}\n'.format(item.message)
            params['message'] += '\n'
            if item.url is not None:
                params['url'] = item.url
            if item.priority is not None:
                params['priority'] = max(item.priority, params['priority'])
            if item.deviceid is not None:
                params['deviceid'] = item.deviceid
            if item.image_url is not None:
                params['image'] = item.image_url
        # Prepare our request
        try:
            response = urllib2.urlopen(BACKEND, urllib.urlencode(params), timeout=Constant.URL_OPEN_TIMEOUT)
            # Read the body
            body = response.read()
            # It's JSON - parse it
            contents = json.loads(body)
            if 'error' in contents.keys():
                L.l.warning("Newtifry server did not accept our message: %s" % contents['error'])
            else:
                L.l.info("Newtifry message sent OK. Size: %d." % contents['size'])
                del _message_queue[:]
                _last_send_date = utils.get_base_location_now_date()
        except urllib2.URLError, ex:
            L.l.warning("Newtifry failed to make request to the server: " + str(ex))
    finally:
        __queue_lock.release()


def send_message(title, message=None, url=None, priority=None, deviceid=None, image_url=None):
    """
    https://newtifry.appspot.com/page/api

    format	json
    Determines the format of the response.
    Only JSON is supported at the moment, so you should always send the string json.
    Required

    source	32 character hash string
    The source key, given to you by the user. They generate it when they create a source.
    You can supply up to 10 sources at a time separated by a comma, or a single source.	Required

    title	string
    The string title of this notification. Keep this short and relevant to the message.	Required

    message	string
    The body of the message. This can contain a lot more detail of the message.
    This is optional, and will be sent as an empty string if not provided.	Optional

    url	string
    An optional URL to pass along, that would give more information about the message.	Optional

    priority	integer
    An optional message priority (0-3). 0 : no priority - 1 : info - 2 : warning - 3 : alert	Optional

    image	string
    An optional bitmap URL to pass along, that would be displayed in the message detail screen (new in version 2.4.0).
    Optional
    """
    global _last_send_date, _message_queue, __queue_lock
    obj = type('obj', (object,), {'title': title, 'message': message, 'url': url, 'priority': priority,
                                  'deviceid': deviceid, 'image_url': image_url,
                                  'date': utils.get_base_location_now_date()})
    try:
        __queue_lock.acquire()
        _message_queue.append(obj)
    finally:
        __queue_lock.release()
    # avoid sending notifications too often
    if (utils.get_base_location_now_date() - _last_send_date).seconds < 30:
        L.l.info('Queuing newtifry message [%s] count %d' % (title, len(_message_queue)))
        return
    else:
        _send_queue()


def unload():
    L.l.info('Newtifry module unloading')
    #dispatcher.disconnect(dispatcher.connect(send_message, signal=Constant.SIGNAL_PUSH_NOTIFICATION,
    #                                         sender=dispatcher.Any))
    global initialised
    initialised = False


def init():
    L.l.debug('Newtifry module initialising')
    global _source_key
    _source_key = model_helper.get_param(Constant.P_NEWTIFY_KEY)
    dispatcher.connect(send_message, signal=Constant.SIGNAL_PUSH_NOTIFICATION, sender=dispatcher.Any)
    # send_message(title="Initialising", message="Module initialising", priority=1)
    # send_message(title="Initialised", message="Module initialised")
    # send_message(title="Initialised 2", message="Module initialised 2")
    thread_pool.add_interval_callable(_send_queue, run_interval_second=60)
    global initialised
    initialised = True
