import common
import os
import threading
import time
from datetime import datetime
from tinydb_serialization import Serializer
from flask_app import app, admin
from main.logger_helper import L


while True:
    try:
        from tinydb import TinyDB, Query, where
        from tinydb.storages import MemoryStorage
        from tinyrecord import transaction
        from flask_admin.contrib.pymongo import ModelView, filters
        from flask_admin.form import Select2Widget
        from flask_admin.model.fields import InlineFieldList, InlineFormField
        from wtforms import fields, form
        from tinymongo import TinyMongoClient
        from tinymongo.serializers import DateTimeSerializer
        from tinydb_serialization import SerializationMiddleware
        break
    except ImportError as iex:
        if not common.fix_module(iex.message):
            break

db = None


class DatetimeSerializer(Serializer):
    OBJ_CLASS = datetime

    def __init__(self, format='%Y-%m-%dT%H:%M:%S', *args, **kwargs):
        super(DatetimeSerializer, self).__init__(*args, **kwargs)
        self._format = format

    def encode(self, obj):
        return obj.strftime(self._format)

    def decode(self, s):
        return datetime.strptime(s, self._format)


class CustomTinyMongoClient(TinyMongoClient):
    @property
    def _storage(self):
        # serialization = SerializationMiddleware(MemoryStorage)
        serialization = SerializationMiddleware()
        serialization.register_serializer(DateTimeSerializer(), 'TinyDate')
        # register other custom serializers
        return serialization


def _init_tinydb():
    global db
    data_file = common.get_json_param(common.Constant.P_DB_PATH)
    data_path = os.path.dirname(data_file)
    # TinyDB.DEFAULT_STORAGE = MemoryStorage
    conn = CustomTinyMongoClient(foldername=data_path)
    # conn = CustomTinyMongoClient(storage=MemoryStorage)
    db = conn.haiot


def _populate_db(cls_name, obj):
    rec_list = common.get_table(cls_name)
    i = 0
    Q = Query()
    res = None
    for rec in rec_list:
        # exist = obj.coll.find({'id': rec['id']})
        exist = obj.coll.table.contains(Q.id == rec['id'])
        if not exist: #.count() == 0:
            res = obj.coll.insert_one(rec)
        else:
            res = None
            # res = obj.coll.update
        if res is not None:
            i += 1
    L.l.info('Loaded {} rows in {}'.format(i, cls_name))


def _init_flask_admin():
    import tinydb_model
    from tinydb_helper import TinyBase
    cls_dict = dict([(name, cls) for name, cls in tinydb_model.__dict__.items() if isinstance(cls, type)])
    for cls_name in cls_dict:
        cls = tinydb_model.__dict__[cls_name]
        if cls_name is not 'TinyBase' and issubclass(cls, TinyBase):
            obj = cls()
            admin.add_view(obj)
            _populate_db(cls_name, obj)

    # app.run(debug=False)


def init(arg_list):
    _init_tinydb()
    _init_flask_admin()
