import common

while True:
    try:
        from flask import Flask
        from flask_admin import Admin
        break
    except ImportError as iex:
        if not common.fix_module(iex.message):
            break

app = None
app = Flask(__name__)
app.config['SECRET_KEY'] = '123456790'
app.config.update(DEBUG=True, SQLALCHEMY_ECHO=False)
admin = Admin(app, name='Haiot')


@app.route('/')
def index():
    return '<a href="/admin/">Click me to get to Admin!</a>'
