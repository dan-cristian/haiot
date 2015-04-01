# project/__init__.py

from flask import Flask, redirect, url_for
from flask_sqlalchemy import SQLAlchemy #workaround for resolve issue
from flask_sqlalchemy import models_committed
import logging
import threading
import common



DB_LOCATION=None
LOGGING_LEVEL=logging.INFO
app = Flask('main')
db=None

def my_import(name):
    #http://stackoverflow.com/questions/547829/how-to-dynamically-load-a-python-class
    mod = __import__(name)
    components = name.split('.')
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return mod

def init_module(module_name, module_is_active):
    dynclass = my_import(module_name)
    if module_is_active:
        print "Module {} is active".format(module_name)
        if not dynclass.initialised:
            logging.info('Module {} initialising'.format(module_name))
            dynclass.init()
        else:
            logging.info('Module {} already initialised'.format(module_name))
    else:
        print "Module {} is not active".format(module_name)
        if dynclass.initialised:
            logging.info('Module {} has been deactivated, unloading'.format(module_name))
            dynclass.unload()
            del dynclass

def init_modules():
    import admin.models
    module_list = admin.models.Module.query.order_by(admin.models.Module.start_order).all()
    for mod in module_list:
        assert isinstance(mod, admin.models.Module)
        init_module(mod.name, mod.active)


def set_db_location(location):
    global DB_LOCATION
    if location == 'disk':
        DB_LOCATION='sqlite:///../database.db'
    else:
        if location == 'mem':
            DB_LOCATION='sqlite:////tmp/database.db'
        else:
            logging.critical('No DB location set {}'.format(location))

def set_logging_level(level):
    global LOGGING_LEVEL
    if level=='debug':
        LOGGING_LEVEL = logging.DEBUG
    else:
        if level=='warning':
            LOGGING_LEVEL = logging.WARNING

#--------------------------------------------------------------------------#

def init():
    logging.basicConfig(format='%(asctime)s:%(levelname)s:%(module)s:%(funcName)s:%(threadName)s:%(message)s',
                        level=LOGGING_LEVEL)
    logging.info('Logging level is {}'.format(LOGGING_LEVEL))
    common.init()
    global app, db, DB_LOCATION
    app.config.update(DEBUG=True, SQLALCHEMY_ECHO = False, SQLALCHEMY_DATABASE_URI=DB_LOCATION)

    db = SQLAlchemy(app)

    from admin import admin, user
    app.register_blueprint(admin, url_prefix='/admin')
    app.register_blueprint(user, url_prefix='/user')
    db.session.autoflush=True
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

    app.run(debug=True, use_reloader=False, host='0.0.0.0')

#@app.route('/')
#def home():
#    return 'Main'

@models_committed.connect_via(app)
def on_models_committed(sender, changes):
    from admin import event
    logging.debug('Model commit detected sender {} change {}'.format(sender, changes))
    event.on_models_committed(sender, changes)

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)