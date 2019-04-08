import common
import os
from main import logger_helper
from common import utils
while True:
    try:
        from tinydb import TinyDB, Query, where
        from tinyrecord import transaction
        from tinymongo import TinyMongoClient
        import flask_admin
        from flask import Flask
        from flask_admin.contrib.pymongo import ModelView, filters
        from flask_admin.form import Select2Widget
        from flask_admin.model.fields import InlineFieldList, InlineFormField
        from wtforms import fields, form
        break
    except ImportError as iex:
        if not common.fix_module(iex.message):
            break


class TinyBase:
    def __str__(self):
        return '{}'.format(self.__dict__)

    def dict(self):
        return self.__dict__

    def __init__(self):
        pass


class Pwm(TinyBase):

    def __init__(self):
        self.id = None
        self.name = None
        self.frequency = None
        self.duty_cycle = None
        self.gpio_pin_code = None
        self.host_name = None


def _init_tinydb(db_path):
    global tinydb
    tinydb = TinyDB(db_path)
    pwm_table = tinydb.table('pwm')
    pwm = Pwm()
    pwm.id = 3
    pwm.name = 'boiler'
    pwm.frequency = 55
    pwm.duty_cycle = 100000
    pwm.gpio_pin_code = 18
    pwm.host_name = 'pizero1'
    try:
        with transaction(pwm_table) as tr:
            # tr.insert({"id": 3, "name": "boiler", "frequency": 55, "duty_cycle": 100000, "gpio_pin_code": 18, "host_name": "pizero1"})
            tr.insert(pwm.dict())
    except Exception as ex:
        print ex


def _init_flask(data_path):
    app = Flask(__name__)

    # Flask views
    @app.route('/')
    def index():
        return '<a href="/admin/">Click me to get to Admin!</a>'

    app.config['SECRET_KEY'] = '123456790'
    # Create models in a JSON file localted at
    #DATAFOLDER = '/tmp/flask_admin_test'
    conn = TinyMongoClient(foldername=data_path)
    db = conn.test
    # Create admin
    admin = flask_admin.Admin(app, name='Example: TinyMongo - TinyDB')
    app.run(debug=True)





def init(arg_list):
    common.init_simple()
    data_file = common.get_json_param(common.Constant.P_DB_PATH)
    _init_tinydb(data_file)
    _init_flask(os.path.dirname(data_file))

