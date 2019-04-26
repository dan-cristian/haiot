from datetime import datetime
import collections
from main.logger_helper import L
from common import Constant, fix_module
while True:
    try:
        from pydispatch import dispatcher
        break
    except ImportError as iex:
        if not fix_module(iex):
            break


# https://stackoverflow.com/questions/4459531/how-to-read-class-attributes-in-the-same-order-as-declared
class OrderedClassMembers(type):
    @classmethod
    def __prepare__(self, name, bases):
        return collections.OrderedDict()

    def __new__(self, name, bases, classdict):
        classdict['__ordered__'] = [key for key in classdict.keys()
                if key not in ('__module__', '__qualname__')]
        return type.__new__(self, name, bases, classdict)


class DictTable:
    def __init__(self, model_class):
        self.table = {}
        self.model_class = model_class
        self.id = 0
        self.key = None

    def find(self, filter=None, sort=None, skip=None, limit=None, *args, **kwargs):
        res = []
        res_ordered = {}
        if sort is not None:
            sort_key = sort[0][0]
            sort_dir = sort[0][1]
        match_count = 0
        for rec in self.table:
            match = True
            comparison_not = False
            if filter is not None:
                for cond in filter:
                    if cond == '$not':
                        for cond_sub in filter[cond]:
                            if cond_sub not in self.table[rec]:
                                table_val = None
                            else:
                                table_val = self.table[rec][cond_sub]
                            if table_val == filter[cond][cond_sub]:
                                match = False
                                break
                    else:
                        if cond not in self.table[rec]:
                            table_val = None
                        else:
                            table_val = self.table[rec][cond]
                        if table_val != filter[cond]:
                            match = False
                            break
            if match:
                if sort is None:
                    # res[rec] = self.table[rec]
                    res.append(self.model_class({**self.table[rec]}))
                else:
                    s_rec = self.table[rec][sort_key]
                    res_ordered[s_rec] = self.table[rec]
                match_count += 1
                if limit is not None and match_count == limit:
                    break
        if sort is None:
            return res
        else:
            if sort_dir > 0:
                sort_list = sorted(res_ordered.items(), key=lambda x: x[0])
                for r in sort_list:
                    res.append(self.model_class({**r[1]}))
                return res

    def insert_one(self, key, doc, bypass_document_validation=False):
        if bypass_document_validation is False:
            if key in doc:
                if doc[key] in self.table:
                    return None
            else:
                if key != 'id':
                    L.l.error('No key [{}] for {} found in record: {}'.format(key, self.model_class.__name__, doc))
                    return None
        self.key = key
        if 'id' not in doc or doc['id'] is None:
            self.id += 1
            doc['id'] = self.id
        self.table[doc[key]] = doc
        return {'inserted_id': doc['id']}


class ModelBase(metaclass=OrderedClassMembers):
    _table_list = {}
    _column_list = ()
    _upsert_listener_list = {}
    _ignore_save_change_fields = ['updated_on']
    _is_used_in_module = False

    @classmethod
    def reset_usage(cls):
        cls._is_used_in_module = False

    @classmethod
    def find(cls, filter=None, sort=None, skip=None, limit=None, *args, **kwargs):
        if not cls._is_used_in_module:
            cls._is_used_in_module = True
        table = cls._table_list[cls.__name__]
        recs = table.find(filter=filter, sort=sort, skip=skip, limit=limit, *args, **kwargs)
        return recs

    @classmethod
    def find_one(cls, filter):
        if not cls._is_used_in_module:
            cls._is_used_in_module = True
        table = cls._table_list[cls.__name__]
        r = table.find(filter=filter, limit=1)
        if len(r) == 1:
            return r[0]
        else:
            return None

    @classmethod
    def insert_one(cls, doc, bypass_document_validation=False):
        if not cls._is_used_in_module:
            cls._is_used_in_module = True
        table = cls._table_list[cls.__name__]
        key = cls.__dict__['__ordered__'][0]
        r = table.insert_one(key=key, doc=doc, bypass_document_validation=bypass_document_validation)
        if r is not None:
            return r['inserted_id']
        else:
            return None

    @classmethod
    def add_upsert_listener(cls, func):
        if cls.__name__ in cls._upsert_listener_list:
            L.l.warning('Listener for {} already in list, overwriting!'.format(cls.__name__))
        cls._upsert_listener_list[cls.__name__] = func

    def save_changed_fields(self, current=None, broadcast=None, persist=None, listeners=True, *args, **kwargs):
        cls = self.__class__
        cls_name = cls.__name__
        if not cls._is_used_in_module:
            cls._is_used_in_module = True
            update = {}
            key = None
            for fld in cls._column_list:
                if fld not in cls._ignore_save_change_fields:
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
                    exist = cls.find_one(filter=key)
                    if exist is not None:
                        res = cls.update_one(query=key, doc={"$set": update})
                        # L.l.info('Updated key {}, {}'.format(key, self.__repr__()))
                    else:
                        res = cls.insert_one(update, bypass_document_validation=True)
                        # L.l.info('Inserted key {}, {} with eid={}'.format(key, self.__repr__(), res.eid))
                    # execute listener
                    if cls_name in cls._upsert_listener_list:
                        has_listener = True
                    else:
                        has_listener = False
                    record = cls.find_one(filter=key)
                    rec_clone = cls(copy=record)
                    change_list = list(update.keys())
                    if persist is True or broadcast is True or has_listener is True:
                        if record is None:
                            L.l.error('No record in db after insert/update for cls {} key {}'.format(cls_name, key))
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
                                cls._upsert_listener_list[cls_name](record=rec_clone, changed_fields=change_list)
                    dispatcher.send(Constant.SIGNAL_DB_CHANGE_FOR_RULES, obj=rec_clone, change=change_list)
                else:
                    L.l.error('Cannot save changed fields, key is missing for {}'.format(self))

    # save fields from remote updates
    @classmethod
    def save(cls, obj):
        # L.l.info('Saving remote record {}'.format(cls.__name__))
        new_obj = cls(copy=obj)
        new_obj.save_changed_fields()

    def __init__(self, copy=None):
        cls = self.__class__
        obj_fields = cls.__dict__['__ordered__']
        if not hasattr(cls, '_class_initialised'):
            cls._table_list[cls.__name__] = DictTable(cls)
            for attr in obj_fields:
                setattr(cls, attr, attr)
                cls._column_list = cls._column_list + (attr,)
            cls.source_host = 'source_host'
            cls._class_initialised = True

        for attr in obj_fields:
            setattr(self, attr, None)
        self.source_host = Constant.HOST_NAME

        if copy is not None:
            for fld in copy:
                if hasattr(self, fld):
                    setattr(self, fld, copy[fld])
                self._listener_executed = None
