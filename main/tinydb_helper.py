from datetime import datetime
import time
import threading
import random
import common
from tinydb_app import db

while True:
    try:
        from flask_admin.contrib.pymongo import ModelView
        from wtforms import fields, form
        from tinyrecord import transaction
        break
    except ImportError as iex:
        if not common.fix_module(iex.message):
            break


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

    def t(self):
        return self.coll.table

    def __init__(self, obj_fields):
        attr_dict = {}
        for attr in obj_fields:
            attr_type = type(getattr(self, attr))
            if attr_type is int:
                fld = fields.IntegerField(attr)
            elif attr_type is float:
                fld = fields.FloatField(attr)
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
        collx = getattr(db, type(self).__name__.lower())
        ModelView.__init__(self, collx, type(self).__name__)
        TinyBase.t = self.coll.table


threadLock = threading.Lock()
globalCounter = 0


def insertfew():
    import tinydb_model
    global globalCounter, threadLock
    time.sleep(3)
    while True:
        # pwm_table = db.tinydb.table('pwm')
        pwm = tinydb_model.Pwm()
        pwm.id = globalCounter
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

def init():
    threading.Thread(target=insertfew).start()
    threading.Thread(target=insertfew).start()
    threading.Thread(target=insertfew).start()