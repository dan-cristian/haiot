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
from main.logger_helper import Log
from common import Constant
from pydispatch import dispatcher

__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

# Configuration.
BACKEND = 'https://newtifry.appspot.com/newtifry'
initialised = False


def send_message(source_key=None, title='', message=None,
                 url=None, priority=None, deviceid=None, image_url=None):
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
    source_key = '6bb91f3f03f11871f4f895eb6a13b8c8'
    params = {}
    params['format'] = 'json'
    params['source'] = source_key
    params['title'] = title
    if message is not None:
        params['message'] = message
    if url is not None:
        params['url'] = url
    if priority is not None:
        params['priority'] = priority
    if deviceid is not None:
        params['deviceid'] = deviceid
    if image_url is not None:
        params['image'] = image_url

    # Prepare our request.
    try:
        response = urllib2.urlopen(BACKEND, urllib.urlencode(params))
        # Read the body.
        body = response.read()
        # It's JSON - parse it.
        contents = json.loads(body)
        if contents.has_key('error'):
            Log.logger.warning("Newtifry server did not accept our message: %s" % contents['error'])
        else:
            Log.logger.info("Newtifry message sent OK. Size: %d." % contents['size'])
    except urllib2.URLError, ex:
        Log.logger.warning("Newtifry failed to make request to the server: " + str(ex))


def unload():
    Log.logger.info('Newtifry module unloading')
    dispatcher.disconnect(dispatcher.connect(send_message, signal=Constant.SIGNAL_PUSH_NOTIFICATION,
                                             sender=dispatcher.Any))
    global initialised
    initialised = False


def init():
    Log.logger.info('Newtifry module initialising')
    dispatcher.connect(send_message, signal=Constant.SIGNAL_PUSH_NOTIFICATION, sender=dispatcher.Any)
    send_message(title="Initialising", message="Module initialising")
    global initialised
    initialised = True
