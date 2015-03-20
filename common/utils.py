__author__ = 'dcristian'
import sys
import os
import json
from collections import namedtuple

#http://stackoverflow.com/questions/6578986/how-to-convert-json-data-into-a-python-object
def _json_object_hook(d):
    return namedtuple('X', d.keys())(*d.values())
def json2obj(data):
    return json.loads(data, object_hook=_json_object_hook)
def obj2json(obj):
    return json.dumps(obj)

def restart_program():
    """Restarts the current program.
    Note: this function does not return. Any cleanup action (like
    saving data) must be done before calling this function."""

    python = sys.executable
    os.execl(python, python, * sys.argv)

