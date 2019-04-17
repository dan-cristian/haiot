from datetime import datetime
import time
import threading
import random
import common
from common import utils
from main.tinydb_app import db
from main.logger_helper import L

while True:
    try:
        from flask_admin.contrib.pymongo import ModelView
        from wtforms import fields, form
        from tinyrecord import transaction
        break
    except ImportError as iex:
        if not common.fix_module(iex):
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

    # def to_obj(self, **entries):
    #    return self.__dict__.update(entries)
    @classmethod
    def find(cls, filter=None, sort=None, skip=None, limit=None, *args, **kwargs):
        recs = cls.coll.find(filter=filter, sort=sort, skip=skip, limit=limit, *args, **kwargs)
        ret = []
        for r in recs:
            ret.append(cls({**r}))
        return ret

    @classmethod
    def find_one(cls, filter=None):
        r = cls.coll.find_one(filter=filter)
        if r is not None:
            return cls({**r})
        else:
            return None

    @classmethod
    def insert_one(cls, doc):
        r = cls.coll.insert_one(doc=doc)
        if r is not None:
            return cls({**r})
        else:
            return None

    def save_changed_fields(self, current=None, broadcast=False, persist=False, *args, **kwargs):
        if current is None:
            current = kwargs['current_record']
        if broadcast is None:
            broadcast = kwargs['notify_transport_enabled']
        if persist is None:
            persist = kwargs['save_to_graph']
        update = {}
        key = None
        for fld in self.__class__.column_list:
            if current is not None and hasattr(current, fld):
                curr_val = getattr(current, fld)
            else:
                curr_val = None
            if hasattr(self, fld):
                new_val = getattr(self, fld)
            else:
                new_val = None
            if curr_val != new_val:
                if new_val is not None:
                    update[fld] = new_val
                else:
                    update[fld] = curr_val
            # set key as the first field in the new record that is not none
            if key is None and new_val is not None:
                if fld == 'voltage':
                    L.l.info('debug')
                key = {fld: new_val}

        if len(update) > 0:
            if key is not None:
                exist = self.__class__.coll.find_one(filter=key)
                if exist is not None:
                    res = self.__class__.coll.update_one(query=key, doc={"$set": update})
                    L.l.info('Updated key {}={} with content {}'.format(key, res.raw_result[0], update))
                else:
                    res = self.__class__.coll.insert_one(update)
                    if 'vad' in key:
                        L.l.info('debug')
                    L.l.info('Inserted key {} with eid={}/{} content={}'.format(key, res.eid, res.inserted_id, update))
            else:
                L.l.error('Cannot save changed fields, key is missing for {}'.format(self))

    def __init__(self, cls, copy=None):
        obj_fields = dict(cls.__dict__)
        if not hasattr(cls, 'tinydb_initialised'):
            attr_dict = {}
            for attr in obj_fields:
                if utils.is_primitive(attr, obj_fields[attr]):
                    attr_type = type(getattr(self, attr))
                    if attr_type is int:
                        fld = fields.IntegerField(attr)
                    elif attr_type is float:
                        fld = fields.FloatField(attr)
                    elif attr_type is bool:
                        fld = fields.BooleanField(attr)
                    elif attr_type is datetime:
                        fld = fields.DateTimeField(attr)
                    elif attr_type is str:
                        fld = fields.StringField(attr)
                    else:
                        fld = fields.StringField(attr)
                    attr_dict[attr] = fld
                    self.column_list = self.column_list + (attr,)
                    self.column_sortable_list = self.column_sortable_list + (attr,)
                    cls.column_list = cls.column_list + (attr,)
                    setattr(cls, attr, attr)
            # http://jelly.codes/articles/python-dynamically-creating-classes/
            self.form = type(type(self).__name__ + 'Form', (form.Form,), attr_dict)
            collx = getattr(db, type(self).__name__.lower())
            ModelView.__init__(self, collx, type(self).__name__)
            cls.t = self.coll.table
            cls.coll = self.coll
            cls.tinydb_initialised = True
        else:
            for attr in obj_fields:
                setattr(self, attr, None)
        if copy is not None:
            for fld in copy:
                setattr(self, fld, copy[fld])


threadLock = threading.Lock()
globalCounter = 0


def insertfew():
    from main import tinydb_model
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
            print(globalCounter)
        except Exception as ex:
            print(ex)

def init():
    threading.Thread(target=insertfew).start()
    threading.Thread(target=insertfew).start()
    threading.Thread(target=insertfew).start()