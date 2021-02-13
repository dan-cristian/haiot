from datetime import datetime
import collections
from main.logger_helper import L
from common import Constant, utils, fix_module, get_json_param
import transport
while True:
    try:
        from pydispatch import dispatcher
        break
    except ImportError as iex:
        if not fix_module(iex):
            break


class P:
    # mqtt_pub_topic_field = "mqtt_pub_topic"
    host_type_field = "host_type"  # determine if this device needs special topic for broadcast (e.g. micro-python)
    HOST_TYPE_MICRO = "micro"


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
    id = 0
    # key = None

    def __init__(self, model_class):
        self.table = {}
        self.index = {}
        self.model_class = model_class
        self.id = 0
        # self.key = None

    def _add_index(self, new_key):
        L.l.info('Adding index for {} on {}'.format(new_key, self.model_class.__name__))
        newlist = sorted(self.table.items(), key=lambda k: new_key)
        # if self.model_class._column_type_list[new_key] == int:
        self.index[new_key] = {}
        for rec in newlist:
            key = rec[1][self.model_class._main_key]
            if new_key in rec[1]:
                key_val = rec[1][new_key]
                self.index[new_key][key_val] = key
            else:
                L.l.error('New key {} not in index {}'.format(new_key, rec[1]))

    def find(self, filter=None, sort=None, skip=None, limit=None, *args, **kwargs):
        res = []
        res_ordered = {}
        if sort is not None:
            sort_key = sort[0][0]
            sort_dir = sort[0][1]
        match_count = 0
        # fixme: lock self.table during iteration
        for rec in dict(self.table):
            match = True
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
                    rec_obj = self.model_class({**self.table[rec]})  # duplicate orig record for change track
                    rec_obj.reference = self.table[rec]
                    res.append(rec_obj)
                else:
                    if sort_key in self.table[rec]:
                        s_rec = self.table[rec][sort_key]
                        res_ordered[s_rec] = self.table[rec]
                    else:
                        L.l.error('Sort key {} is missing from record {}'.format(sort_key, self.table[rec]))
                match_count += 1
                if limit is not None and match_count == limit:
                    break
        if sort is None:
            return res
        else:
            if sort_dir > 0:
                sort_list = sorted(res_ordered.items(), key=lambda x: x[0])
                for r in sort_list:
                    rec_obj = self.model_class({**r[1]})  # duplicate orig rec for change track
                    rec_obj.reference = r[1]
                    res.append(rec_obj)
                return res

    def insert_one(self, key, doc, bypass_document_validation=False):
        if bypass_document_validation is False:
            if key in doc:
                if doc[key] in self.table:
                    L.l.error('Cannot insert {}, record exist, key={}'.format(doc, key))
                    return None
            else:
                if key != 'id':
                    L.l.error('No key [{}] for {} found in record: {}'.format(key, self.model_class.__name__, doc))
                    return None
        cls = self.model_class
        # self.key = key
        if 'id' not in doc or doc['id'] is None:
            self.id += 1
            doc['id'] = self.id
        if len(self.index) > 0:
            L.l.info('Invalidating all indexes {} on insert'.format(self.model_class.__name__))
            self.index.clear()  # delete key from index
        self.table[doc[key]] = doc
        res = self.model_class({**doc})  # duplicate
        res.reference = self.table[doc[key]]
        return res

    def not_used_update_one(self, key, key_val, updated_record):
        cls_name = self.model_class.__name__
        try:
            if key == self.model_class._column_list[0]:
                good_key_val = updated_record[key]
            else:
                if key not in self.index:
                    self._add_index(new_key=key)
                if key in self.index:
                    indexed_recs = self.index[key]
                    if updated_record[key] in indexed_recs:
                        good_key_val = indexed_recs[updated_record[key]]
                    else:
                        L.l.error('Key {} not in index {}'.format(key, cls_name))
                        return None
                else:
                    new_key = list(updated_record)[0]
                    good_key_val = None
                    for rec in self.table:
                        if new_key in self.table[rec] and self.table[rec][new_key] == updated_record[new_key]:
                            good_key_val = rec
                            break
                    if good_key_val is None:
                        L.l.error('Failed to find record for update by key {}'.format(key))
                        return None

            for fld in updated_record:
                if fld not in self.model_class._column_list:
                    L.l.warning('Unexpected new field {} on updating {}'.format(fld, cls_name))
                # if good_key_val in self.table:
                if fld in self.table[good_key_val]:
                    if self.table[good_key_val][fld] != updated_record[fld]:
                        if fld in self.index:
                            L.l.info('Invalidating index {}:{} on update'.format(cls_name, fld))
                            self.index[fld].clear()  # delete key from index
                        self.table[good_key_val][fld] = updated_record[fld]
                elif fld in self.model_class._column_list:
                    self.table[good_key_val][fld] = updated_record[fld]
                else:
                    L.l.error('Trying to update an alien field {} for {}'.format(fld, cls_name))
            if self.model_class._main_key in updated_record:
                return updated_record[self.model_class._main_key]
            else:
                return None
        except KeyError as ke:
            L.l.error('Key error {}'.format(ke), exc_info=True)
            return None


class ModelBase(metaclass=OrderedClassMembers):
    _table_list = {}
    _column_list = ()
    _main_key = None
    _column_type_list = {}
    _upsert_listener_list = {}
    _ignore_save_change_fields = ['updated_on']
    _is_used_in_module = False
    _history_enabled_field_name = {}
    _history_enabled_values = {}

    def __repr__(self):
        # cls = self.__class__
        # tbl = cls._table_list[cls.__name__]
        # rec_key = getattr(self, tbl.key)
        return str(self.__dict__)

    def get_mqtt_topic(self):
        return self._broadcast_mqtt_topic

    def set_mqtt_topic(self, mqtt_topic):
        self._broadcast_mqtt_topic = mqtt_topic

    @classmethod
    def reset_usage(cls):
        cls._is_used_in_module = False

    @classmethod
    def dup(cls, target, copy):
        try:
            for fld in copy:
                if hasattr(target, fld):
                    setattr(target, fld, copy[fld])
                if '_listener_executed' in target.__dict__:
                    target._listener_executed = None
                target.reference = None
        except Exception as ex:
            L.l.error('Duplicate error er={}'.format(ex), exc_info=True)

    @classmethod
    def get_key(cls, record):
        try:
            key = cls._main_key
            if key not in record:
                L.l.warning('Main {} key={} not in record={}'.format(cls.__name__, key, record))
                key = cls.__dict__['__ordered__'][1]
                if key not in record:
                    key = list(record)[0]
                    L.l.warning('Using record 1st field as key={}'.format(key))
                else:
                    L.l.warning('Using model 2nd field as key={}'.format(key))
        except TypeError as ex:
            L.l.error('Key error {}, ex={}'.format(cls.__name__, ex), exc_info=True)
            key = None
        return key

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
        if len(r) >= 1:
            rec = r[0]
            if len(r) > 1:
                L.l.warning('Multiple records exists on find_one {} {}'.format(cls, filter))
        else:
            rec = None
        return rec

    @classmethod
    def insert_one(cls, doc, bypass_document_validation=False):
        if not cls._is_used_in_module:
            cls._is_used_in_module = True
        table = cls._table_list[cls.__name__]
        key = cls._main_key
        rec = table.insert_one(key=key, doc=doc, bypass_document_validation=bypass_document_validation)
        if rec is not None:
            return rec
        else:
            return None

    # @classmethod
    # def update_one(cls, query, updated_record, existing_record):
    #    if not cls._is_used_in_module:
    #        cls._is_used_in_module = True
    #    table = cls._table_list[cls.__name__]
    #    if u"$set" in updated_record:
    #        updated_record = updated_record[u"$set"]
    #    key = cls.get_key(existing_record)
    #    if hasattr(existing_record, key):
    #        key_val = getattr(existing_record, key)
    #    else:
    #        key_val = getattr(updated_record, key)
    #    r = table.update_one(key=key, key_val=key_val, updated_record=updated_record)
    #    return r

    @classmethod
    def add_upsert_listener(cls, func):
        if cls.__name__ in cls._upsert_listener_list:
            L.l.warning('Listener for {} already in list, overwriting!'.format(cls.__name__))
        cls._upsert_listener_list[cls.__name__] = func

    @staticmethod
    def _persist(record, update, class_name):
        # record[Constant.JSON_PUBLISH_TABLE] = class_name
        dispatcher.send(signal=Constant.SIGNAL_STORABLE_RECORD, new_record=record)
        # persistence.save_to_history_db(record)

    @classmethod
    def set_broadcast_topic(cls, mqtt_topic):
        cls._broadcast_mqtt_topic = mqtt_topic

    @classmethod
    def enable_history(cls, field_name, value_count):
        cls._history_enabled_field_name[(cls.__name__, field_name)] = value_count

    @classmethod
    def add_history_value(cls, field_name, key, field_value):
        history_key = (cls.__name__, key, field_name)
        field_key = (cls.__name__, field_name)
        if history_key not in cls._history_enabled_values.keys():
            val_list = []
        else:
            val_list = cls._history_enabled_values[history_key]
        val_list.append(field_value)
        history_count = cls._history_enabled_field_name[field_key]
        cls._history_enabled_values[history_key] = val_list[:history_count]

    @staticmethod
    def _broadcast(record, update, class_name):
        out_rec = None
        try:
            out_rec = record.__dict__
            out_rec[Constant.JSON_PUBLISH_TABLE] = class_name
            out_rec[Constant.JSON_PUBLISH_FIELDS_CHANGED] = list(update.keys())
            out_rec[Constant.JSON_PUBLISH_SRC_HOST] = Constant.HOST_NAME
            out_rec['_sent_on'] = utils.get_base_location_now_date()
            js = utils.safeobj2json(out_rec)
            # if P.mqtt_pub_topic_field in out_rec:
            if P.host_type_field in out_rec and out_rec[P.host_type_field] is not None:
                host_type = out_rec[P.host_type_field]
                mqtt_topic = None
                if host_type == P.HOST_TYPE_MICRO:
                    if "host_name" in out_rec:
                        host_name = out_rec["host_name"]
                        mqtt_topic = get_json_param(Constant.P_MQTT_TOPIC_MICRO) + "/" + host_name
                    else:
                        L.l.error("Missing host_name field for mqtt topic creation: {}".format(host_type))
                else:
                    L.l.error("Unexpected host type {}".format(host_type))
                # mqtt_topic = out_rec[P.mqtt_pub_topic_field]
                L.l.info("Mqtt broadcast {} on non-default topic {}".format(class_name, mqtt_topic))
                # send to limited traffic topic for low cpu devices etc
                transport.send_message_topic(json=js, topic=mqtt_topic)
            else:
                # send to main topic
                transport.send_message_json(json=js)
        except Exception as ex:
            L.l.error('Unable to broadcast {} rec={} ex={}'.format(class_name, out_rec, ex), exc_info=True)

    # silent is used for debug
    def save_changed_fields(self, broadcast=None, persist=None, listeners=True, silent=True):  # , *args, **kwargs):
        cls = self.__class__
        cls_name = cls.__name__
        if not cls._is_used_in_module:
            cls._is_used_in_module = True
        k = cls.get_key(record=self.__dict__)
        key = {k: self.__dict__[k]}
        update = {}  # holder of changed fields/values
        current = self.reference  # holder of original record
        for fld in cls._column_list:
            if fld == 'updated_on':  # and self.updated_on is None:
                # fixme: not sure if working well
                update[fld] = datetime.now()
                if current is not None:
                    current[fld] = datetime.now()
            if fld not in cls._ignore_save_change_fields:
                # moved save upate_on above
                if hasattr(self, fld):
                    new_val = getattr(self, fld)
                else:
                    new_val = None
                if current is not None and fld in current:
                    curr_val = current[fld]
                else:
                    curr_val = None
                if curr_val != new_val:
                    if new_val is not None:
                        update[fld] = new_val
                    elif curr_val is not None:
                        update[fld] = curr_val
                    else:
                        L.l.warning('what?')
                    if current is not None:
                        # update storage fields
                        self.reference[fld] = new_val
                    # save history fields
                    if (cls_name, fld) in self._history_enabled_field_name:
                        self.add_history_value(fld, key[cls._main_key], new_val)
                else:
                    # field value not changed
                    pass

        if len(update) > 0:
            if key is not None:
                if current is not None:
                    # res = cls.update_one(query=key, updated_record={"$set": update}, existing_record=self)
                    if not silent:
                        L.l.info('Updated {} key {}, {}'.format(cls_name, key, update))
                else:
                    res = cls.insert_one(update, bypass_document_validation=True)
                    if not silent:
                        L.l.info('Inserted key {}, {} with eid={}'.format(key, self.__repr__(), res.eid))
                # execute listener
                has_listener = cls_name in cls._upsert_listener_list
                record = cls.find_one(filter=key)
                if record is None:
                    L.l.error('No record in db after insert/update for cls {} key {}'.format(cls_name, key))
                    return
                rec_clone = cls(copy=record.__dict__)
                change_list = list(update.keys())
                if persist is True or broadcast is True or has_listener is True:
                    if persist is True:
                        self._persist(record=rec_clone, update=update, class_name=cls_name)
                    if broadcast is True:
                        if not silent:
                            L.l.info('Broadcasting event for {} record {}'.format(cls_name, rec_clone))
                        self._broadcast(record=rec_clone, update=update, class_name=cls_name)
                    if listeners and has_listener:
                        if hasattr(self, '_listener_executed') and self._listener_executed is True:
                            if not silent:
                                L.l.info('Already executed listener on device events for {}'.format(cls_name))
                        elif hasattr(self, 'is_device_event') and self.is_device_event is True:
                            if not silent:
                                L.l.info('No listener on device events for {}'.format(cls_name))
                        else:
                            if not silent:
                                L.l.info('Executing listener on device events for {}'.format(cls_name))
                            rec_clone._listener_executed = True
                            func = cls._upsert_listener_list[cls_name]
                            if func is not None:
                                func(record=rec_clone, changed_fields=change_list)
                dispatcher.send(Constant.SIGNAL_DB_CHANGE_FOR_RULES, obj=rec_clone, change=change_list)
            else:
                L.l.error('Cannot save changed fields, key is missing for {}'.format(self))

    # save fields from remote updates
    @classmethod
    def save(cls, obj):
        # L.l.info('Saving remote record {}'.format(cls.__name__))
        key = cls.get_key(obj)
        rec = cls.find_one(filter={key: obj[key]})
        new_obj = cls(copy=obj)
        if rec is not None:
            new_obj.reference = rec.reference
        new_obj.save_changed_fields(silent=True)

    def __init__(self, copy=None):
        cls = self.__class__
        obj_fields = cls.__dict__['__ordered__']
        if not hasattr(cls, '_class_initialised'):
            cls._table_list[cls.__name__] = DictTable(cls)
            for attr in obj_fields:
                if attr is not '__doc__':
                    cls._column_type_list[attr] = type(getattr(cls, attr))
                    setattr(cls, attr, attr)
                    cls._column_list += (attr,)
            cls.source_host = 'source_host'
            # add manually to column list
            cls._column_list += ('source_host',)
            cls._class_initialised = True
            cls.reference = None
            if cls.__doc__ is not None:
                for line in cls.__doc__.split("\n"):
                    strip = line.replace(' ', '')
                    if 'key=' in strip:
                        cls._main_key = strip.split('key=')[1]
                    elif 'history=' in strip:
                        fields = strip.split('history=')[1]
                        for pair in fields.split(','):
                            atoms = pair.split(':')
                            cls.enable_history(atoms[0], int(atoms[1]))
            else:
                cls._main_key = obj_fields[0]

        for attr in obj_fields:
            if attr is not '__doc__':
                setattr(self, attr, None)
        # self.source_host = Constant.HOST_NAME

        if copy is not None:
            cls.dup(target=self, copy=copy)

