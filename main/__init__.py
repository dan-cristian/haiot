# project/__init__.py

from flask import Flask, render_template, request, session
from flask.ext.sqlalchemy import SQLAlchemy


app = Flask('main')
app.config.update(
        DEBUG=True,
        SQLALCHEMY_DATABASE_URI='sqlite:///../database.db',
    )
db = SQLAlchemy(app)

from admin import admin, user
app.register_blueprint(admin, url_prefix='/admin')
app.register_blueprint(user, url_prefix='/user')
db.create_all()


import sensors
sensors.init()
from admin import event
event.init()
#a = Blog('my first post', 'some looooong body')
#b = Blog('my second post', 'some short body')
#c = Blog('my third post', 'bla bla bla')

#db.session.add(a)
#db.session.add(b)
#db.session.add(c)
#db.session.commit()



@app.route('/')
def home():
    return 'Blog be here'

