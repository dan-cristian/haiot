__author__ = 'dcristian'
import socket
import logging
import sys
from common.utils import json2obj


def on_subscribe(client, userdata, mid, granted_qos):
	logging.info('Subscribed to client {} user {} mid {} qos {}'.format(
        str(client), str(userdata), str(mid), str(granted_qos)))

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
	print("Received User["+str(userdata)+"] MsgTopic["+str(msg.topic)+"] MsgPayload["+str(msg.payload))+"]"
	try:
		#locate json string
		start=msg.payload.find('{')
		end=msg.payload.find('}')
		json=msg.payload[start:end+1]
		x = json2obj(json)
		if hasattr(x, 'command') and hasattr(x, 'command_id') and hasattr(x, 'host_target'):
			if x.host_target==socket.gethostname():
				logging.info('Executing command {}'.format(x.command))
			else:
				print "Received command {} for other host {}".format(x, x.host_target)
		#else:
			#print x.address, x.type
	except AttributeError:
		logging.warning('Unknown attribute error in msg {}'.format(json))

	except ValueError:
		logging.warning('Invalid JSON {} {}'.format(json, sys.exc_info()[0]))
	    #traceback.print_stack()