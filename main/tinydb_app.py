import common
import os
import threading
import time
from datetime import datetime
from tinydb_serialization import Serializer
from main import logger_helper
from common import utils
import random
while True:
    try:
        from tinydb import TinyDB, Query, where
        from tinydb.storages import MemoryStorage
        from tinyrecord import transaction
        from flask_admin import Admin
        from flask import Flask
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
        serialization = SerializationMiddleware()
        serialization.register_serializer(DateTimeSerializer(), 'TinyDate')
        # register other custom serializers
        return serialization


class TinyBase(ModelView):
    column_list = ()
    column_sortable_list = ()
    form = None
    page_size = 20
    can_set_page_size = True

    def __str__(self):
        return '{}'.format(self.__dict__)

    def dictx(self):
        attr_dict = {}
        for column in self.column_list:
            attr_dict[column] = getattr(self, column)
        return attr_dict

    def __init__(self, obj_fields):
        attr_dict = {}
        for attr in obj_fields:
            attr_type = type(getattr(self, attr))
            if attr_type is int:
                fld = fields.IntegerField(attr)
            elif attr_type is str:
                fld = fields.StringField(attr)
            elif attr_type is bool:
                fld = fields.BooleanField(attr)
            elif attr_type is datetime:
                fld = fields.DateTimeField(attr)
            else:
                fld = fields.StringField(attr)
            attr_dict[attr] = fld
            self.column_list = self.column_list + (attr,)
            self.column_sortable_list = self.column_sortable_list + (attr,)
        # http://jelly.codes/articles/python-dynamically-creating-classes/
        self.form = type(type(self).__name__ + 'Form', (form.Form,), attr_dict)

        ModelView.__init__(self, getattr(db, type(self).__name__.lower()), type(self).__name__)



class Pwm(TinyBase):
    def __init__(self):
        self.id = None
        self.name = ''
        self.frequency = 0
        self.duty_cycle = 0
        self.gpio_pin_code = 0
        self.host_name = ''
        self.update_on = datetime.now()

        TinyBase.__init__(self, dict(self.__dict__))





class UserForm(form.Form):
    foo = fields.StringField('foo')
    name = fields.StringField('Name')
    email = fields.StringField('Email')
    password = fields.StringField('Password')


class UserView(ModelView):
    column_list = ('name', 'email', 'password', 'foo')
    column_sortable_list = ('name', 'email', 'password')
    form = UserForm
    page_size = 20
    can_set_page_size = True


app = Flask(__name__)
admin = None
threadLock = threading.Lock()
globalCounter = 0

# Flask views
@app.route('/')
def index():
    return '<a href="/admin/">Click me to get to Admin!</a>'


def insertfew():
    global globalCounter, threadLock
    time.sleep(3)
    i = random.randint(1, 100)
    while True:
        # pwm_table = db.tinydb.table('pwm')
        pwm = Pwm()
        i = i + 1
        pwm.id = i
        # pwm_table = pwm.coll.table
        pwm.name = 'boiler {}'.format(random.randint(1, 100))
        pwm.frequency = random.randint(10, 800)
        pwm.duty_cycle = random.randint(1, 1000000)
        pwm.gpio_pin_code = random.randint(1, 40)
        pwm.host_name = 'pizero1'
        try:
            # with transaction(pwm_table) as tr:
            #    res = tr.insert(pwm.dictx())
            #    print res
            with transaction(pwm.coll.table):
                res = pwm.coll.insert_one(pwm.dictx(), bypass_document_validation=True)
                # print res.inserted_id
            with threadLock:
                globalCounter += 1
            print globalCounter
        except Exception as ex:
            print ex


def _init_tinydb(data_file):
    global db
    data_path = os.path.dirname(data_file)
    conn = CustomTinyMongoClient(foldername=data_path)
    #conn = CustomTinyMongoClient(storage=MemoryStorage)
    db = conn.haiot


def _init_flask(data_path):
    app.config['SECRET_KEY'] = '123456790'
    global admin
    admin = Admin(app, name='Haiot')
    app.config.update(DEBUG=False, SQLALCHEMY_ECHO=False)
    u = UserView(db.user, 'User')
    p = Pwm()
    admin.add_view(u)
    admin.add_view(p)

    threading.Thread(target=insertfew).start()
    #threading.Thread(target=insertfew).start()
    #threading.Thread(target=insertfew).start()

    app.run(debug=False)


def init(arg_list):
    common.init_simple()
    data_file = common.get_json_param(common.Constant.P_DB_PATH)
    _init_tinydb(data_file)
    _init_flask(os.path.dirname(data_file))


