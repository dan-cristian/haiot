from main.admin import model_helper
import json
from common import Constant
from main.logger_helper import L
from pydispatch import dispatcher
import thingspeak
import datetime
import traceback
import tzlocal
initialised = False


class P:
    key_separator = ':'
    fields = {}
    keys = {}
    channels = {}
    last_upload_ok = datetime.datetime.now()
    timezone = tzlocal.get_localzone().zone


def _upload_field(model, fields):
    upload = P.channels[model]
    fields['timezone'] = P.timezone
    for i in range(1, 3):
        try:
            res = upload.update(fields)
            if res == 0:
                delta = (datetime.datetime.now() - P.last_upload_ok).total_seconds()
                L.l.warning("Failed to upload data, last request ok was {} seconds ago".format(delta))
            else:
                P.last_upload_ok = datetime.datetime.now()
        except Exception, ex:
            L.l.warning("Error when uploading things, ex={}".format(ex))
    # L.l.info("res={}".format(res))


def _handle_record(record=None):
    cls = str(type(record))
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
    try:
        if model is not None:
            if model in P.fields:
                cloud_fields = P.fields[model]  # only one instance supported for now
                #cloud_keys = P.keys[model]
                field_index = 1
                fields = {}
                for cloud_field in cloud_fields:
                    cloud_field_name = cloud_field[0]
                    if hasattr(record, cloud_field_name):
                        cloud_key_val = cloud_field[1]
                        record_key_val = getattr(record, cloud_field[2])
                        if record_key_val == cloud_key_val:
                            fields['field' + str(field_index)] = getattr(record, cloud_field_name)
                            #_upload_field(model, field_index, getattr(record, cloud_field), created_at)
                    field_index += 1
                if len(fields) > 0:
                    if hasattr(record, Constant.DB_FIELD_UPDATE):
                        created_at = getattr(record, Constant.DB_FIELD_UPDATE)
                    else:
                        created_at = None
                    fields['created_at'] = created_at
                _upload_field(model, fields)
    except Exception, ex:
        L.l.error("Unable to upload record, ex={}".format(ex))


def init():
    global initialised
    try:
        config_file = model_helper.get_param(Constant.P_THINGSPEAK_API_FILE)
        with open(config_file, 'r') as f:
            channel_list = json.load(f)
            for chid in channel_list:
                read_api = channel_list[chid]['read_api']
                write_api = channel_list[chid]['write_api']
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
                    initialised = False
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
                        pair = atom.split('=')
                        if len(pair) == 2:
                            kname = pair[0]
                            kval = pair[1]
                            if kname == 'model':
                                model = kval
                            elif kname == "key":
                                key = kval
                        else:
                            L.l.warning("Wrong meta format, <key=value> expected, got instead {}".format(atom))
                    if model is None:
                        L.l.warning("Expected model=TableName not found in metadata {}".format(setup['metadata']))
                    else:
                        P.channels[model] = ch
                        if key is not None:
                            P.keys[model] = key
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
                        if model in P.fields:
                            # fixme: add support for
                            # P.channels[model].append(fields)
                            L.l.error("Multiple channels with same field not yet supported")
                        P.fields[model] = fields
                        initialised = True
        if initialised:
            dispatcher.connect(_handle_record, signal=Constant.SIGNAL_STORABLE_RECORD, sender=dispatcher.Any)
    except Exception, ex:
        L.l.warning("Unable to read config or init thingspeak, stack={}".format(traceback.print_exc()))
