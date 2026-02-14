from storage.dicts import model
from storage.dicts.model_helper import ModelBase
import common
from main.logger_helper import L


def _populate_db(cls, obj):
    rec_list = common.get_table(cls.__name__)
    i = 0
    if rec_list is not None:
        for rec in rec_list:
            res = cls.insert_one(rec)
            if res is not None:
                i += 1
    L.l.info('Loaded {} rows in {}'.format(i, cls.__name__))


def load_db():
    cls_dict = dict([(name, cls) for name, cls in model.__dict__.items() if isinstance(cls, type)])
    sorted_keys = sorted(cls_dict)
    for cls_name in sorted_keys:
        cls = model.__dict__[cls_name]
        if (cls_name is not 'ModelBase') and (cls_name is not 'HADiscoverableDevice') and issubclass(cls, ModelBase):
            obj = cls()
            _populate_db(cls, obj)
            cls.reset_usage()

