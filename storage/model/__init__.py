# DB = 'TINY'
DB = 'DICTS'

if DB == 'TINY':
    from storage.tiny.tinydb_app import load_db
elif DB == 'DICTS':
    from storage.dicts import load_db
load_db()

if DB == 'TINY':
    from storage.tiny import tinydb_model as model
elif DB == 'DICTS':
    from storage.dicts import model
m = model


def init(arg_list):
    pass
