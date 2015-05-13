__author__ = 'dcristian'
import threading
from main import logger

class FlaskInThread (threading.Thread):

    """
    defines a thread for the server
    """

    def __init__(self, app, host="localhost", port=5000, debug=False, use_reloader=False):
        """
        constructor
        @param      app     Flask application
        """
        threading.Thread.__init__(self)
        self._app = app
        self._host = host
        self._port = port
        self.daemon = True
        self._debug = debug
        self._use_reloader=use_reloader

    def run(self):
        """
        start the server
        """
        try:
            logger.info('Starting flask web ui on host {} port {}'.format(self._host,  self._port))
            self._app.run(host=self._host, port=self._port, debug = self._debug, use_reloader=self._use_reloader)
        except Exception, ex:
            logger.error('Error init flask on host {} port {}, err={}'.format(self._host,  self._port, ex))

    def shutdown(self):
        """
        shuts down the server, the function could work if:
            * method run keeps a pointer on a server instance
              (the one owning method `serve_forever <https://docs.python.org/3.4/library/socketserver.html#socketserver.BaseServer.serve_forever>`_)
            * module `werkzeug <http://werkzeug.pocoo.org/>`_ returns this instance
              in function `serving.run_simple <https://github.com/mitsuhiko/werkzeug/blob/master/werkzeug/serving.py>`_
            * module `Flask <http://flask.pocoo.org/>`_ returns this instance in
              method `app.Flask.run <https://github.com/mitsuhiko/flask/blob/master/flask/app.py>`_
        """
        raise NotImplementedError()
        # self.server.shutdown()
        # self.server.server_close()