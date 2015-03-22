__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

from main import app

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False, host='0.0.0.0')
    print 'App EXIT'

