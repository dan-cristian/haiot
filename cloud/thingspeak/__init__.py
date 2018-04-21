from main.admin import model_helper
import json
from common import Constant
from main.logger_helper import L
from main import thread_pool
from pydispatch import dispatcher
import thingspeak
import datetime
import traceback
import tzlocal
import urllib2
import threading
import logging

initialised = False
_channel_lock = threading.Lock()

class P:
    key_separator = ':'
    key_model = 'model' #  meta should contain: model=Tablename,key=fieldname
    key_key = 'key'
    fields = {} #  key = model name
    keys = {}
    channels = {}  # channel cloud object list for uploads, key = model name
    # fields definition as unique id to detect settings changes in cloud and reload
    # {'model_name':{'channel_id1':'signature1', 'channel_id2':'signature2'}}
    signatures = {}
    profile_channels = {}  # all channels defined on cloud
    last_upload_ok = datetime.datetime.now()
    timezone = tzlocal.get_localzone().zone
    record_list = []


def _upload_field(model, fields, ch_index):
    upload = P.channels[model].values()[ch_index]
    fields['timezone'] = P.timezone
    err = False
    for i in range(1, 3):
        try:
            res = upload.update(fields)
            if res == 0:
                delta = (datetime.datetime.now() - P.last_upload_ok).total_seconds()
                L.l.warning("Failed to upload data, last request ok was {} seconds ago".format(delta))
            else:
                P.last_upload_ok = datetime.datetime.now()
                if err:
                    L.l.info("Error recovered in attempt {}".format(i))
                break
        except Exception, ex:
            L.l.warning("Error when uploading things, ex={}".format(ex))
            err = True
    # L.l.info("res={}".format(res))


def _handle_record(new_record=None, current_record=None):
    global _channel_lock
    cls = str(type(new_record))
    key = 'models.'
    start = cls.find(key)
    model = None
    if start >= 0:
        start += len(key)
        end = cls.find("'>", start)
        if end >= 0:
            model = cls[start:end]
        else:
            L.l.warning("Something is wrong in class name, does not contain expected termination")
    if model is not None:
        try:
            _channel_lock.acquire()
            if model in P.fields:
                ch_index = 0
                for cloud_fields in P.fields[model].values():
                    #cloud_fields = P.fields[model]  # only one instance supported for now
                    #cloud_keys = P.keys[model]
                    field_index = 1
                    fields = {}
                    for cloud_field in cloud_fields:
                        cloud_field_name = cloud_field[0]
                        # only save changed value fields
                        if hasattr(new_record, cloud_field_name) and (current_record is None or cloud_field_name
                                                                      in current_record.last_commit_field_changed_list):
                            cloud_key_val = cloud_field[1]
                            if cloud_key_val is not None:
                                record_key_name = getattr(new_record, cloud_field[2])
                            if (cloud_key_val is not None and record_key_name == cloud_key_val) or cloud_key_val is None:
                                if hasattr(new_record, cloud_field_name):
                                    fields['field' + str(field_index)] = getattr(new_record, cloud_field_name)
                                else:
                                    L.l.warning("Attribute [{}] not found in record {}".format(
                                        cloud_field_name, new_record))
                        field_index += 1
                    if len(fields) > 0:
                        if hasattr(new_record, Constant.DB_FIELD_UPDATE):
                            created_at = getattr(new_record, Constant.DB_FIELD_UPDATE)
                        else:
                            created_at = None
                        fields['created_at'] = created_at
                    _upload_field(model, fields, ch_index)
                    ch_index += 1
        except Exception, ex:
            L.l.error("Unable to handle record, ex={}, record={}".format(ex, new_record))
        finally:
            _channel_lock.release()


def _get_channel(chid, read_api, write_api):
    ch = thingspeak.Channel(chid, api_key=read_api)
    ch.write_key = write_api
    params = None
    for i in range(1, 3):
        try:
            params = ch.get({'results': 0, 'metadata': 'true'})
            break
        except Exception, ex:
            L.l.warning("Error while getting cloud data, ex={}".format(ex))
    if params is None:
        L.l.error('Unable to read cloud data')
        ret = False
    else:
        setup = json.loads(params)['channel']
        meta = setup['metadata']
        if ',' not in meta:
            meta = meta + ','
        atoms = meta.split(',')
        model = None
        key = None
        fields = []
        for atom in atoms:
            if atom != '':
                pair = atom.split('=')
                if len(pair) == 2:
                    kname = pair[0]
                    kval = pair[1]
                    if kname == P.key_model:
                        model = kval
                    elif kname == P.key_key:
                        key = kval
                else:
                    L.l.warning("Wrong meta format, <key=value> expected, got instead [{}]".format(atom))
        if model is None:
            L.l.warning("Expected model=TableName not found in metadata {}".format(setup['metadata']))
        else:
            end = params.find('"created_at":')
            if end >= 0:
                # check if channel is already loaded and not changed
                signature = params[:end]
                if model in P.signatures and chid in P.signatures[model] and signature == P.signatures[model][chid]:
                    # channel loaded already and is not changed
                    pass
                else:
                    # channel not found or def changed, reload
                    L.l.info("Loading channel definition for model {} channel {}".format(model, chid))
                    if model not in P.signatures:
                        P.signatures[model] = {}
                    P.signatures[model][chid] = signature
                    if model not in P.channels:
                        P.channels[model] = {}
                    P.channels[model][chid] = ch
                    if model not in P.keys:
                        P.keys[model] = {}
                    if key is not None:
                        P.keys[model][chid] = key
                        # setup['model'] = model
                    for f in range(1, 8):
                        field = 'field' + str(f)
                        key_val = None
                        if field in setup:
                            fname = setup[field]
                            if key is not None and P.key_separator in fname:
                                fpair = fname.split(P.key_separator)
                                fname = fpair[0]
                                key_val = fpair[1]
                            fields.append([fname, key_val, key])
                        else:
                            break
                    if model not in P.fields:
                        P.fields[model] = {}
                    P.fields[model][chid] = fields


def _check_def_change():
    global _channel_lock
    try:
        _channel_lock.acquire()
        config_file = model_helper.get_param(Constant.P_THINGSPEAK_API_FILE)
        read_api = None
        with open(config_file, 'r') as f:
            profile = json.load(f)
            read_api = profile['0']['read_api']
        if read_api is not None:
            get = urllib2.urlopen("https://api.thingspeak.com/channels.json?api_key={}".format(read_api), timeout=10)
            response = get.read()
            channel_list = json.loads(response)
            for ch in channel_list:
                if P.key_model in ch['metadata']:
                    #L.l.info("Found uploadable channel {}".format(ch['name']))
                    P.profile_channels[ch['id']] = ch
                    for key in ch['api_keys']:
                        if key['write_flag']:
                            ch['api_write'] = key['api_key']
                        else:
                            ch['api_read'] = key['api_key']
                    _get_channel(chid=ch['id'], read_api=ch['api_read'], write_api=ch['api_write'])
                else:
                    L.l.info("Found non-uploadable channel {}, ignoring".format(ch['name']))
    except Exception, ex:
        L.l.error("Unable to get channels definitions, ex={}".format(ex))
    finally:
        _channel_lock.release()


def _store_record(new_record=None, current_record=None):
    P.record_list.append([new_record, current_record])


def _upload_bulk():
    try:
        for record in list(P.record_list):
            _handle_record(record[0], record[1])
            P.record_list.remove(record)
    except Exception, ex:
        L.l.warning("Unable to upload bulk, itemcount={}, item=P{}, err={}".format(len(P.record_list), record, ex))


def thread_run():
    _check_def_change()
    _upload_bulk()


def unload():
    thread_pool.remove_callable(thread_run)


def init():
    global initialised
    try:
        # https://stackoverflow.com/questions/11029717/how-do-i-disable-log-messages-from-the-requests-library
        logging.getLogger("requests").setLevel(logging.WARNING)
        _check_def_change()
        initialised = True
        dispatcher.connect(_store_record, signal=Constant.SIGNAL_STORABLE_RECORD, sender=dispatcher.Any)
        thread_pool.add_interval_callable(thread_run, run_interval_second=60)
    except Exception, ex:
        L.l.warning("Unable to read config or init thingspeak, stack={}".format(traceback.print_exc()))
