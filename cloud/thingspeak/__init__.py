from main.admin import model_helper
import json
from common import Constant
from main.logger_helper import L
from pydispatch import dispatcher
import thingspeak
initialised = False


class P:
    upload_prefix = "upload_"
    channels = {}
    upload = {}


def _upload_field(model, fields):
    upload = P.channels[P.upload_prefix + model]
    res = upload.update(fields)
    L.l.info("res={}".format(res))


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
            if model in P.channels:
                cloud_model = P.channels[model][0]  # only one instance supported for now
                field_index = 1
                fields = {}
                for cloud_field in cloud_model:
                    if hasattr(record, cloud_field):
                        if hasattr(record, Constant.DB_FIELD_UPDATE):
                            created_at = getattr(record, Constant.DB_FIELD_UPDATE)
                        else:
                            created_at = None
                        fields['field' + str(field_index)] =  getattr(record, cloud_field)
                        #_upload_field(model, field_index, getattr(record, cloud_field), created_at)
                    field_index += 1
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
            for id in channel_list:
                read_api = channel_list[id]['read_api']
                write_api = channel_list[id]['write_api']
                ch = thingspeak.Channel(id, api_key=read_api)
                ch.write_key = write_api
                params = ch.get({'results': 0, 'metadata': 'true'})
                setup = json.loads(params)['channel']
                atoms = setup['metadata'].split('=')
                if atoms[0] == 'model':
                    model = atoms[1]
                    # setup['model'] = model
                    fields = []
                    for f in range(1, 8):
                        field = 'field' + str(f)
                        if field in setup:
                            fields.append(setup[field])
                        else:
                            break
                    if model in P.channels:
                        #fixme: add support for
                        #P.channels[model].append(fields)
                        L.l.error("Multiple channels with same field not yet supported")
                    else:
                        P.channels[model] = [fields]
                        P.channels[P.upload_prefix + model] = ch
                else:
                    model = None
                    L.l.warning("Expected model=TableName not found in metadata {}".format(setup['metadata']))
        initialised = True
        dispatcher.connect(_handle_record, signal=Constant.SIGNAL_STORABLE_RECORD, sender=dispatcher.Any)
    except Exception, ex:
        L.l.warning("Unable to read config or init thingspeak")
