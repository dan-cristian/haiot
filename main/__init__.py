# project/__init__.py

from flask import Flask
from flask_sqlalchemy import SQLAlchemy #workaround for resolve issue
from flask_sqlalchemy import models_committed
import logging
import sys

def my_import(name):
    #http://stackoverflow.com/questions/547829/how-to-dynamically-load-a-python-class
    mod = __import__(name)
    components = name.split('.')
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return mod

def init_modules():
    import admin.models
    module_list = admin.models.Module.query.order_by(admin.models.Module.start_order).all()
    for mod in module_list:
        assert isinstance(mod, admin.models.Module)
        dynclass = my_import(mod.name)
        if mod.active:
            print "Module {} is active".format(mod.name)
            if not dynclass.initialised:
                logging.info('Module {} initialising'.format(mod.name))
                dynclass.init()
            else:
                logging.info('Module {} already initialised'.format(mod.name))
        else:
            print "Module {} is not active".format(mod.name)
            if dynclass.initialised:
                logging.info('Module {} has been deactivated, unloading'.format(mod.name))
                dynclass.unload()
                del dynclass

logging.basicConfig(format='%(levelname)s:%(module)s:%(funcName)s:%(threadName)s:%(message)s', level=logging.DEBUG)
import common
common.init()

app = Flask('main')
app.config.update(DEBUG=True, SQLALCHEMY_DATABASE_URI='sqlite:///../database.db')
db = SQLAlchemy(app)

from admin import admin, user
app.register_blueprint(admin, url_prefix='/admin')
app.register_blueprint(user, url_prefix='/user')
db.create_all()

import admin.model_helper
admin.model_helper.populate_tables()

from admin import event
event.init()
init_modules()

from admin import thread_pool
import threading
t = threading.Thread(target=thread_pool.main)
t.daemon = True
t.start()

@app.route('/')
def home():
    return 'Blog be here'

@models_committed.connect_via(app)
def on_models_committed(sender, changes):
    logging.info('Model commit detected sender {} change {}'.format(sender, changes))
    event.on_models_committed(sender, changes)

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)