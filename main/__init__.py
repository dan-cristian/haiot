# project/__init__.py

from flask import Flask
from flask_sqlalchemy import SQLAlchemy #workaround for resolve issue

#from flask.ext.sqlalchemy import SQLAlchemy
import logging

def my_import(name):
    #http://stackoverflow.com/questions/547829/how-to-dynamically-load-a-python-class
    mod = __import__(name)
    components = name.split('.')
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return mod

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

import admin.models
module_list = admin.models.Module.query.order_by(admin.models.Module.start_order).all()
for mod in module_list:
    assert isinstance(mod, admin.models.Module)
    if mod.active:
        print "Module {} is active".format(mod.name)
        dynclass = my_import(mod.name)
        dynclass.init()
    else:
        print "Module {} is not active".format(mod.name)

from admin import event
event.init()

from admin import thread_pool
import threading
t = threading.Thread(target=thread_pool.main)
t.daemon = True
t.start()
#thread_pool.main()

#a = Blog('my first post', 'some looooong body')
#db.session.add(a)
#db.session.commit()

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)

@app.route('/')
def home():
    return 'Blog be here'

