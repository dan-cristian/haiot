__author__ = 'dcristian'
import sys
import os
import json
import re
import datetime
from collections import namedtuple

#http://stackoverflow.com/questions/6578986/how-to-convert-json-data-into-a-python-object
def _json_object_hook(d):
    return namedtuple('X', d.keys())(*d.values())
def date_deserialiser(json):
    if re.search("....-..-..T..:..:..\.......", json):
        return datetime.datetime.strptime(json, "%Y-%m-%d %H:%M:%S.%f")
    else:
        return json
def date_serialised(obj):
    return obj.isoformat() if hasattr(obj, 'isoformat') else obj
def json2obj(data):
    #return json.loads(data, object_pairs_hook=date_deserialiser)
    return json.loads(data)
def obj2json(obj):
    return json.dumps(obj, default=date_serialised)

def parse_to_date(strdate):
    if re.search("....-..-..T..:..:..\.......",  strdate):
        strdate= strdate.replace('T',' ')
        strdate = datetime.datetime.strptime(strdate, "%Y-%m-%d %H:%M:%S.%f")
    return strdate

def restart_program():
    """Restarts the current program.
    Note: this function does not return. Any cleanup action (like
    saving data) must be done before calling this function."""

    python = sys.executable
    os.execl(python, python, * sys.argv)

