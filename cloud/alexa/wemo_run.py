#!/usr/bin/env python

"""
The MIT License (MIT)

Copyright (c) 2015 Maker Musings

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

# For a complete discussion, see http://www.makermusings.com

import email.utils
import select
import socket
import struct
import time
import uuid
import threading
import prctl
from inspect import getmembers, isfunction
from main.logger_helper import L
from main import thread_pool
from main.admin.model_helper import get_param
from common import Constant
import rule
import rule.alexa

_FAUXMOS = []
_pooler = None

# This XML is the minimum needed to define one of our virtual switches
# to the Amazon Echo

SETUP_XML = """<?xml version="1.0"?>
<root>
  <device>
    <deviceType>urn:MakerMusings:device:controllee:1</deviceType>
    <friendlyName>%(device_name)s</friendlyName>
    <manufacturer>Belkin International Inc.</manufacturer>
    <modelName>Emulated Socket</modelName>
    <modelNumber>3.1415</modelNumber>
    <UDN>uuid:Socket-1_0-%(device_serial)s</UDN>
  </device>
</root>
"""


# A simple utility class to wait for incoming data to be
# ready on a socket.

class poller:
    def __init__(self):
        if 'poll' in dir(select):
            self.use_poll = True
            self.poller = select.poll()
        else:
            self.use_poll = False
        self.targets = {}

    def add(self, target, fileno=None):
        if not fileno:
            fileno = target.fileno()
        if self.use_poll:
            self.poller.register(fileno, select.POLLIN)
        self.targets[fileno] = target

    def remove(self, target, fileno=None):
        if not fileno:
            fileno = target.fileno()
        if self.use_poll:
            self.poller.unregister(fileno)
        del (self.targets[fileno])

    def poll(self):
        prctl.set_name("alexa_wemo")
        threading.current_thread().name = "alexa_wemo"
        try:
            timeout = 100
            if self.use_poll:
                ready = self.poller.poll(timeout)
            else:
                ready = []
                if len(self.targets) > 0:
                    (rlist, wlist, xlist) = select.select(self.targets.keys(), [], [], timeout)
                    ready = [(x, None) for x in rlist]
            for one_ready in ready:
                target = self.targets.get(one_ready[0], None)
                if target:
                    target.do_read(one_ready[0])
        except Exception as ex:
            L.l.error("Error in wemo poll: {}".format(ex))
        prctl.set_name("idle")
        threading.current_thread().name = "idle"


# Base class for a generic UPnP device. This is far from complete
# but it supports either specified or automatic IP address and port
# selection.

class upnp_device(object):
    this_host_ip = None

    @staticmethod
    def local_ip_address():
        if not upnp_device.this_host_ip:
            temp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                temp_socket.connect(('8.8.8.8', 53))
                upnp_device.this_host_ip = temp_socket.getsockname()[0]
            except:
                upnp_device.this_host_ip = '127.0.0.1'
            del (temp_socket)
            L.l.info("got local address of %s" % upnp_device.this_host_ip)
        return upnp_device.this_host_ip

    def __init__(self, listener, pooller, port, index, root_url, server_version, persistent_uuid, other_headers=None,
                 ip_address=None):
        self.listener = listener
        self.poller = pooller
        self.port = port
        self.root_url = root_url
        self.server_version = server_version
        self.persistent_uuid = persistent_uuid
        self.uuid = uuid.uuid4()
        self.other_headers = other_headers

        if ip_address:
            self.ip_address = ip_address
        else:
            self.ip_address = upnp_device.local_ip_address()

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if self.port == 0:
            self.port = (int)(get_param(Constant.P_ALEXA_WEMO_LISTEN_PORT)) + index
            #self.port = self.socket.getsockname()[1]
        self.socket.bind((self.ip_address, self.port))
        self.socket.listen(5)
        self.poller.add(self)
        self.client_sockets = {}
        self.listener.add_device(self)

    def fileno(self):
        return self.socket.fileno()

    def do_read(self, fileno):
        if fileno == self.socket.fileno():
            (client_socket, client_address) = self.socket.accept()
            self.poller.add(self, client_socket.fileno())
            self.client_sockets[client_socket.fileno()] = client_socket
        else:
            data, sender = self.client_sockets[fileno].recvfrom(4096)
            if not data:
                self.poller.remove(self, fileno)
                del (self.client_sockets[fileno])
            else:
                self.handle_request(data, sender, self.client_sockets[fileno])

    def handle_request(self, data, sender, socket):
        pass

    def get_name(self):
        return "unknown"

    def respond_to_search(self, destination, search_target):
        L.l.info("Responding to search for %s" % self.get_name())
        date_str = email.utils.formatdate(timeval=None, localtime=False, usegmt=True)
        location_url = self.root_url % {'ip_address': self.ip_address, 'port': self.port}
        message = ("HTTP/1.1 200 OK\r\n"
                   "CACHE-CONTROL: max-age=86400\r\n"
                   "DATE: %s\r\n"
                   "EXT:\r\n"
                   "LOCATION: %s\r\n"
                   "OPT: \"http://schemas.upnp.org/upnp/1/0/\"; ns=01\r\n"
                   "01-NLS: %s\r\n"
                   "SERVER: %s\r\n"
                   "ST: %s\r\n"
                   "USN: uuid:%s::%s\r\n" % (
                   date_str, location_url, self.uuid, self.server_version, search_target, self.persistent_uuid,
                   search_target))
        if self.other_headers:
            for header in self.other_headers:
                message += "%s\r\n" % header
        message += "\r\n"
        temp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        temp_socket.sendto(message, destination)


# This subclass does the bulk of the work to mimic a WeMo switch on the network.

class fauxmo(upnp_device):
    @staticmethod
    def make_uuid(name):
        return ''.join(["%x" % sum([ord(c) for c in name])] + ["%x" % ord(c) for c in "%sfauxmo!" % name])[:14]

    def __init__(self, dev_name, listener, pooller, ip_address, port, index,
                 action_handler_on=None, action_handler_off=None):
        self.serial = self.make_uuid(dev_name)
        self.name = dev_name
        self.ip_address = ip_address
        persistent_uuid = "Socket-1_0-" + self.serial
        other_headers = ['X-User-Agent: redsonic']
        upnp_device.__init__(self, listener, pooller, port, index, "http://%(ip_address)s:%(port)s/setup.xml",
                             "Unspecified, UPnP/1.0, Unspecified", persistent_uuid, other_headers=other_headers,
                             ip_address=ip_address)
        if action_handler_on:
            self.action_handler_on = action_handler_on
        if action_handler_off:
            self.action_handler_off = action_handler_off
        #else:
        #    self.action_handler_on = self
        L.l.info("WeMo device '%s' ready on %s:%s" % (self.name, self.ip_address, self.port))

    def get_name(self):
        return self.name

    def handle_request(self, data, sender, socket):
        if data.find('GET /setup.xml HTTP/1.1') == 0:
            L.l.info("Responding to setup.xml for %s" % self.name)
            xml = SETUP_XML % {'device_name': self.name, 'device_serial': self.serial}
            date_str = email.utils.formatdate(timeval=None, localtime=False, usegmt=True)
            message = ("HTTP/1.1 200 OK\r\n"
                       "CONTENT-LENGTH: %d\r\n"
                       "CONTENT-TYPE: text/xml\r\n"
                       "DATE: %s\r\n"
                       "LAST-MODIFIED: Sat, 01 Jan 2000 00:01:15 GMT\r\n"
                       "SERVER: Unspecified, UPnP/1.0, Unspecified\r\n"
                       "X-User-Agent: redsonic\r\n"
                       "CONNECTION: close\r\n"
                       "\r\n"
                       "%s" % (len(xml), date_str, xml))
            socket.send(message)
        elif data.find('SOAPACTION: "urn:Belkin:service:basicevent:1#SetBinaryState"') != -1:
            success = False
            if data.find('<BinaryState>1</BinaryState>') != -1:
                # on
                L.l.info("Responding to ON for {} function={}".format(self.name, self.action_handler_on))
                # success = rule.execute_rule(self.action_handler_on)
                success = getattr(rule.alexa, self.action_handler_on)()
                # success = self.action_handler_on()
            elif data.find('<BinaryState>0</BinaryState>') != -1:
                # off
                L.l.info("Responding to OFF for {} function={}".format(self.name, self.action_handler_off))
                # success = rule.execute_rule(self.action_handler_off)
                success = getattr(rule.alexa, self.action_handler_off)()
                # success = self.action_handler_off()
            else:
                L.l.info("Unknown Binary State request:")
                L.l.info(data)
            if success:
                # The echo is happy with the 200 status code and doesn't
                # appear to care about the SOAP response body
                soap = ""
                date_str = email.utils.formatdate(timeval=None, localtime=False, usegmt=True)
                message = ("HTTP/1.1 200 OK\r\n"
                           "CONTENT-LENGTH: %d\r\n"
                           "CONTENT-TYPE: text/xml charset=\"utf-8\"\r\n"
                           "DATE: %s\r\n"
                           "EXT:\r\n"
                           "SERVER: Unspecified, UPnP/1.0, Unspecified\r\n"
                           "X-User-Agent: redsonic\r\n"
                           "CONNECTION: close\r\n"
                           "\r\n"
                           "%s" % (len(soap), date_str, soap))
                socket.send(message)
        else:
            L.l.info(data)

    def on(self):
        return False

    def off(self):
        return True


# Since we have a single process managing several virtual UPnP devices,
# we only need a single listener for UPnP broadcasts. When a matching
# search is received, it causes each device instance to respond.
#
# Note that this is currently hard-coded to recognize only the search
# from the Amazon Echo for WeMo devices. In particular, it does not
# support the more common root device general search. The Echo
# doesn't search for root devices.

class upnp_broadcast_responder(object):
    TIMEOUT = 0

    def __init__(self):
        self.devices = []

    def init_socket(self):
        ok = True
        self.ip = '239.255.255.250'
        self.port = 1900
        try:
            # This is needed to join a multicast group
            self.mreq = struct.pack("4sl", socket.inet_aton(self.ip), socket.INADDR_ANY)

            # Set up server socket
            self.ssock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            self.ssock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            try:
                self.ssock.bind(('', self.port))
            except Exception as e:
                L.l.warning("WARNING: Failed to bind %s:%d: %s", (self.ip, self.port, e))
                ok = False

            try:
                self.ssock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, self.mreq)
            except Exception as e:
                L.l.warning('WARNING: Failed to join multicast group:', e)
                ok = False

        except Exception as e:
            L.l.warning("Failed to initialize UPnP sockets:", e)
            return False
        if ok:
            L.l.info("Listening for UPnP broadcasts")

    def fileno(self):
        return self.ssock.fileno()

    def do_read(self, fileno):
        data, sender = self.recvfrom(1024)
        if data:
            if data.find('M-SEARCH') == 0 and data.find('urn:Belkin:device:**') != -1:
                for device in self.devices:
                    time.sleep(0.1)
                    device.respond_to_search(sender, 'urn:Belkin:device:**')
            else:
                pass

    # Receive network data
    def recvfrom(self, size):
        if self.TIMEOUT:
            self.ssock.setblocking(0)
            ready = select.select([self.ssock], [], [], self.TIMEOUT)[0]
        else:
            self.ssock.setblocking(1)
            ready = True

        try:
            if ready:
                return self.ssock.recvfrom(size)
            else:
                return False, False
        except Exception as e:
            L.l.warning(e)
            return False, False

    def add_device(self, device):
        self.devices.append(device)
        L.l.info("UPnP broadcast listener: new device registered")


def get_alexawemo_rules():
    ALEXA_RULE_PREFIX = 'alexawemo_'
    alexa_rules = {}
    # parse rules to find alexawemo specific ones
    func_list = getmembers(rule.alexa, isfunction)
    if func_list:
        for func in func_list:
            if not func[1].func_defaults and not func[1].func_name.startswith('_'):
                # add this to DB
                func_name = func[0]
                if func_name.startswith(ALEXA_RULE_PREFIX):
                    # cmd = func_name.split(ALEXA_RULE_PREFIX)[1]
                    name_list = func_name.split('_on')
                    if len(name_list) == 2:
                        dev_name = name_list[0].split(ALEXA_RULE_PREFIX)[1]
                        if dev_name in alexa_rules.keys():
                            # alexa_rules[dev_name][0] = func[1]
                            alexa_rules[dev_name][0] = func_name
                        else:
                            # alexa_rules[dev_name] = [func[1], 0]
                            alexa_rules[dev_name] = [func_name, None]
                    else:
                        name_list = func_name.split('_off')
                        if len(name_list) == 2:
                            dev_name = name_list[0].split(ALEXA_RULE_PREFIX)[1]
                            if dev_name in alexa_rules.keys():
                                # alexa_rules[dev_name][1] = func[1]
                                alexa_rules[dev_name][1] = func_name
                            else:
                                # alexa_rules[dev_name] = [None, func[1]]
                                alexa_rules[dev_name] = [None, func_name]
    return alexa_rules


def unload():
    global _pooler
    thread_pool.remove_callable(_pooler.poll)


def init():
    L.l.info('Wemo module initialising')
    global _pooler

    # Set up our singleton for polling the sockets for data read
    _pooler = poller()

    # Set up our singleton listener for UPnP broadcasts
    u = upnp_broadcast_responder()
    u.init_socket()

    # Add the UPnP broadcast listener to the poller so we can respond
    # when a broadcast is received.
    _pooler.add(u)

    # NOTE: As of 2015-08-17, the Echo appears to have a hard-coded limit of
    # 16 switches it can control. Only the first 16 elements of the FAUXMOS
    # list will be used.
    alexa_list = get_alexawemo_rules()
    index = 0
    for rule_entry in alexa_list.keys():
        # a fixed port wasn't specified, use a dynamic one
        dev_name = rule_entry.replace('_', ' ')
        switch = fauxmo(dev_name=dev_name, listener=u, pooller=_pooler, ip_address=None, port=0, index=index,
                        action_handler_on=alexa_list[rule_entry][0], action_handler_off=alexa_list[rule_entry][1])
        index += 1

    thread_pool.add_interval_callable(_pooler.poll, run_interval_second=0.5)
