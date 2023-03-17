from datetime import datetime
import time
import threading
import random
import collections
from common import Constant, utils, fix_module
from storage.tiny.tinydb_app import db
from main.logger_helper import L
import transport

while True:
    try:
        from pydispatch import dispatcher
        from flask_admin.contrib.pymongo import ModelView
        from wtforms import fields, form
        from tinyrecord import transaction
        break
    except ImportError as iex:
        if not fix_module(iex):
            break


# https://stackoverflow.com/questions/4459531/how-to-read-class-attributes-in-the-same-order-as-declared
class OrderedClassMembers(type(ModelView)):
    @classmethod
    def __prepare__(self, name, bases):
        return collections.OrderedDict()

    def __new__(self, name, bases, classdict):
        classdict['__ordered__'] = [key for key in classdict.keys()
                if key not in ('__module__', '__qualname__')]
        return type.__new__(self, name, bases, classdict)


class TinyBase(ModelView, metaclass=OrderedClassMembers):
    column_list = ()
    column_sortable_list = ()
    upsert_listener_list = {}
    form = None
    page_size = 20
    can_set_page_size = True
    ignore_save_change_fields = ['updated_on']
    is_used_in_module = False

    def __str__(self):
        return '{}'.format(self.__dict__)

    def dictx(self):
        attr_dict = {}
        for column in self.__class__.column_list:
            attr_dict[column] = getattr(self, column)
        return attr_dict

    #@classmethod
    #def to_dictx(cls, ):

    def t(self):
        return self.coll.table

    # def to_obj(self, **entries):
    #    return self.__dict__.update(entries)
    @classmethod
    def find(cls, filter=None, sort=None, skip=None, limit=None, *args, **kwargs):
        if not cls.is_used_in_module:
            cls.is_used_in_module = True
        recs = cls.coll.find(filter=filter, sort=sort, skip=skip, limit=limit, *args, **kwargs)
        ret = []
        for r in recs:
            ret.append(cls({**r}))
        return ret

    @classmethod
    def find_one(cls, filter=None):
        if not cls.is_used_in_module:
            cls.is_used_in_module = True
        r = cls.coll.find_one(filter=filter)
        if r is not None:
            return cls({**r})
        else:
            return None

    @classmethod
    def insert_one(cls, doc, bypass_document_validation=False):
        if not cls.is_used_in_module:
            cls.is_used_in_module = True
        r = cls.coll.insert_one(doc=doc, bypass_document_validation=bypass_document_validation)
        if r is not None:
            return r.inserted_id
        else:
            return None

    @classmethod
    def reset_usage(cls):
        cls.is_used_in_module = False

    @staticmethod
    def _persist(record, update, class_name):
        record[Constant.JSON_PUBLISH_TABLE] = class_name
        dispatcher.send(signal=Constant.SIGNAL_STORABLE_RECORD, new_record=record)
        # persistence.save_to_history_db(record)

    @staticmethod
    def _broadcast(record, update, class_name):
        try:
            record[Constant.JSON_PUBLISH_SOURCE_HOST] = str(Constant.HOST_NAME)
            record[Constant.JSON_PUBLISH_TABLE] = class_name
            record[Constant.JSON_PUBLISH_FIELDS_CHANGED] = list(update.keys())
            record['_sent_on'] = utils.get_base_location_now_date()
            js = utils.safeobj2json(record)
            transport.send_message_json(json=js)
        except Exception as ex:
            L.l.error('Unable to broadcast {} rec={}'.format(class_name, record))

    def save_changed_fields(self, current=None, broadcast=None, persist=None, listeners=True, *args, **kwargs):
        cls = self.__class__
        cls_name = cls.__name__
        if not cls.is_used_in_module:
            cls.is_used_in_module = True
        potential_recursion = hasattr(self, '_id')
        try:
            if current is None and 'current_record' in kwargs:
                current = kwargs['current_record']
            if broadcast is None and 'notify_transport_enabled' in kwargs:
                broadcast = kwargs['notify_transport_enabled']
            if persist is None and 'save_to_graph' in kwargs:
                persist = kwargs['save_to_graph']
            update = {}
            key = None
            for fld in cls.column_list:
                if fld not in cls.ignore_save_change_fields:
                    if fld == 'updated_on' and self.updated_on is None:
                        self.updated_on = datetime.now()
                    if hasattr(self, fld):
                        new_val = getattr(self, fld)
                    else:
                        new_val = None
                    if current is not None and hasattr(current, fld):
                        curr_val = getattr(current, fld)
                    else:
                        curr_val = None
                    if curr_val != new_val:
                        if new_val is not None:
                            update[fld] = new_val
                        elif curr_val is not None:
                            update[fld] = curr_val
                        else:
                            L.l.info('what?')
                    # set key as the first field in the new record that is not none
                    if key is None and new_val is not None:
                        key = {fld: new_val}

            if len(update) > 0:
                if key is not None:
                    exist = cls.coll.find_one(filter=key)
                    if exist is not None:
                        res = cls.coll.update_one(query=key, updated_record={"$set": update})
                        # L.l.info('Updated key {}, {}'.format(key, self.__repr__()))
                    else:
                        res = cls.coll.insert_one(update, bypass_document_validation=True)
                        # L.l.info('Inserted key {}, {} with eid={}'.format(key, self.__repr__(), res.eid))
                    # execute listener
                    if cls_name in cls.upsert_listener_list:
                        has_listener = True
                    else:
                        has_listener = False
                        if listeners:
                            L.l.warning("Listener triggered but none are attached to class {}".format(cls_name))
                    record = None
                    i = 0
                    while record is None and i < 10:
                        record = cls.coll.find_one(filter=key)
                        if record is None:
                            time.sleep(0.1)  # fixme!!!!
                            i += 1
                    if i > 0 and record is not None:
                        L.l.error('Found record {} with key {} after {} tries'.format(cls_name, key, i))
                    rec_clone = cls(copy=record)
                    change_list = list(update.keys())
                    if persist is True or broadcast is True or has_listener is True:
                        if record is None:
                            L.l.error('No record in db after insert/update for cls {} key {}'.format(cls_name, key))
                            L.l.info('Error self is {}'.format(self))
                            L.l.info('Error update was {}, rec={}'.format(update, record))
                            L.l.info('Error col list is {}'.format(cls.column_list))
                            return
                        if persist is True:
                            self._persist(record=record, update=update, class_name=cls_name)
                        if broadcast is True:
                            self._broadcast(record=record, update=update, class_name=cls_name)
                        if listeners and has_listener:
                            if hasattr(self, '_listener_executed') and self._listener_executed is True:
                                pass
                            elif hasattr(self, 'is_device_event') and self.is_device_event is True:
                                # L.l.info('No listener on device events for {}'.format(cls_name))
                                pass
                            else:
                                rec_clone._listener_executed = True
                                cls.upsert_listener_list[cls_name](record=rec_clone, changed_fields=change_list)
                    dispatcher.send(Constant.SIGNAL_DB_CHANGE_FOR_RULES, obj=rec_clone, change=change_list)
                else:
                    L.l.error('Cannot save changed fields, key is missing for {}'.format(self))
        except Exception as ex:
            L.l.info('Exception saving fields, class {} ex={}'.format(cls_name, ex), exc_info=True)

    # save fields from remote updates
    @classmethod
    def save(cls, obj):
        # L.l.info('Saving remote record {}'.format(cls.__name__))
        new_obj = cls(copy=obj)
        new_obj.save_changed_fields()

    @classmethod
    def add_upsert_listener(cls, func):
        if cls.__name__ in cls.upsert_listener_list:
            L.l.warning('Listener for {} already in list, overwriting!'.format(cls.__name__))
        cls.upsert_listener_list[cls.__name__] = func

    def __repr__(self):
        cls = self.__class__
        if cls.column_list is not None:
            rep = '[{}] '.format(cls.__name__)
            i = 0
            for fld in cls.column_list:
                rep = '{}{}:{} '.format(rep, fld, getattr(self, fld))
                i += 1
                if i > 3:
                    break
            return rep
        else:
            return '(obj)' + cls.__name__

    def __init__(self, copy=None):
        cls = self.__class__
        obj_fields = list(cls.__dict__['__ordered__'])
        if not hasattr(cls, '_tinydb_initialised'):
            attr_dict = {}
            cls.column_list = ()
            cls.column_sortable_list = ()
            obj_fields.append('source_host')  # add this field to all instances
            cls.source_host = Constant.HOST_NAME
            first_check = True
            for attr in obj_fields:
                if utils.is_primitive(attr, getattr(cls, attr)):
                    if first_check:
                        if attr != 'id':
                            L.l.error('First key is not id, but {}. list is {}'.format(attr, cls.__dict__))
                            L.l.info('dicts={}'.format(dict(cls.__dict__)))
                            L.l.info('ordered={}'.format(collections.OrderedDict(cls.__dict__)))
                        first_check = False
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
                    # self.column_list = self.column_list + (attr,)
                    # self.column_sortable_list = self.column_sortable_list + (attr,)
                    cls.column_list = cls.column_list + (attr,)
                    setattr(cls, attr, attr)  # set class field values to equal names, for ORM autocompletion
            # http://jelly.codes/articles/python-dynamically-creating-classes/
            self.form = type(type(self).__name__ + 'Form', (form.Form,), attr_dict)
            collx = getattr(db, type(self).__name__.lower())
            ModelView.__init__(self, collx, type(self).__name__)
            cls.t = self.coll.table
            cls.coll = self.coll
            cls._tinydb_initialised = True
        else:
            for attr in obj_fields:
                setattr(self, attr, None)
            self.source_host = Constant.HOST_NAME
        if copy is not None:
            for fld in copy:
                if hasattr(self, fld):
                    setattr(self, fld, copy[fld])
                self._listener_executed = None


threadLock = threading.Lock()
globalCounter = 0


def insertfew():
    from storage.tiny import tinydb_model
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
                # res = pwm.coll.insert_one(pwm.dictx(), bypass_document_validation=True)
                # print res.inserted_id
                pass
            with threadLock:
                globalCounter += 1
            print(globalCounter)
        except Exception as ex:
            print(ex)

def init():
    threading.Thread(target=insertfew).start()
    threading.Thread(target=insertfew).start()
    threading.Thread(target=insertfew).start()