import common
import os
import threading
import time
from datetime import datetime
from main.flask_app import app, admin
from main.logger_helper import L

from common import fix_module
while True:
    try:
        from tinydb import TinyDB, Query, where
        from tinydb.storages import MemoryStorage
        from tinyrecord import transaction
        import pymongo
        from flask_admin.contrib.pymongo import ModelView, filters
        from flask_admin.form import Select2Widget
        from flask_admin.model.fields import InlineFieldList, InlineFormField
        from wtforms import fields, form
        from tinymongo import TinyMongoClient
        from tinymongo.serializers import DateTimeSerializer, Serializer
        from tinydb_serialization import SerializationMiddleware
        break
    except ImportError as iex:
        if not fix_module(iex):
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


class CustomFileTinyMongoClient(TinyMongoClient):
    @property
    def _storage(self):
        serialization = SerializationMiddleware()
        serialization.register_serializer(DateTimeSerializer(), 'TinyDate')
        # register other custom serializers
        return serialization


class CustomMemoryTinyMongoClient(TinyMongoClient):
    @property
    def _storage(self):
        serialization = SerializationMiddleware(MemoryStorage)
        # serialization = SerializationMiddleware()
        serialization.register_serializer(DateTimeSerializer(), 'TinyDate')
        # register other custom serializers
        return serialization


def _init_tinydb():
    global db
    data_file = common.get_json_param(common.Constant.P_DB_PATH)
    data_path = os.path.dirname(data_file)
    # conn = CustomFileTinyMongoClient(foldername=data_path)
    conn = CustomMemoryTinyMongoClient()
    db = conn.haiot


def _populate_db(cls, obj):
    # rec_list = common.get_table(cls_name)
    rec_list = common.get_table(cls.__name__)
    i = 0
    if rec_list is not None:
        # Q = Query()
        res = None
        for rec in rec_list:
            # exist = obj.coll.find({'id': rec['id']})
            if 'id' not in rec:
                # L.l.info('No id in class {}, record {}'.format(cls.__name__, rec))
                first = next(iter(rec))
                key = {first: rec[first]}
            else:
                key = {cls.id: rec['id']}
            # exist = obj.coll.table.contains(Q.id == rec['id'])
            exist = cls.find_one(key)
            if exist is None:  # .count() == 0:
                res = obj.coll.insert_one(rec)
            else:
                res = None
                # res = obj.coll.update
            if res is not None:
                i += 1
    L.l.info('Loaded {} rows in {}'.format(i, cls.__name__))


def _init_flask_admin():
    from main import tinydb_model
    from main.tinydb_helper import TinyBase
    cls_dict = dict([(name, cls) for name, cls in tinydb_model.__dict__.items() if isinstance(cls, type)])
    for cls_name in cls_dict:
        cls = tinydb_model.__dict__[cls_name]
        if cls_name is not 'TinyBase' and issubclass(cls, TinyBase):
            obj = cls()
            admin.add_view(obj)
            # _populate_db(cls_name, obj)
            _populate_db(cls, obj)

    # app.run(debug=False)


def init(arg_list):
    _init_tinydb()
    _init_flask_admin()