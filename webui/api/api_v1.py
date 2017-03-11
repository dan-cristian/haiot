import os
from pydispatch import dispatcher
from flask import abort, send_file, render_template, request
from main import app, db
from main.logger_helper import Log
from main.admin.model_helper import commit, get_param
from common import Constant, utils
from mpd import MPDClient

__author__ = 'Dan Cristian <dan.cristian@gmail.com>'


def return_web_message(pin_value, ok_message='', err_message=''):
    if pin_value:
        return 'OK: {} \n {}={}'.format(ok_message, Constant.SCRIPT_RESPONSE_OK, pin_value)
    else:
        return 'ERR: {} \n {}={}'.format(err_message, Constant.SCRIPT_RESPONSE_NOTOK, pin_value)


@app.route('/apiv1/db_update/model_name=<model_name>&filter_name=<filter_name>'
           '&field_name=<field_name>&filter_value=<filter_value>&field_value=<field_value>')
def generic_db_update(model_name, filter_name, filter_value, field_name, field_value):
    try:
        Log.logger.info("Execute API generic_db_update model={} filter={} filtervalue={} field={} fieldvalue={}"
                        .format(model_name, filter_name, filter_value, field_name, field_value))
        table = utils.class_for_name('main.admin.models', model_name)
        # http://stackoverflow.com/questions/19506105/flask-sqlalchemy-query-with-keyword-as-variable
        kwargs = {filter_name: filter_value}
        # avoid getting "This session is in 'committed' state; no further SQL can be emitted within this transaction"
        db.session.remove()
        # db.session = db.create_scoped_session()
        record = table.query.filter_by(**kwargs).first()
        if record:
            if hasattr(record, field_name):
                setattr(record, field_name, field_value)
                db.session.add(record)
                commit()
                dispatcher.send(signal=Constant.SIGNAL_UI_DB_POST, model=table, row=record)
                return '%s: %s' % (Constant.SCRIPT_RESPONSE_OK, record)
            else:
                msg = 'Field {} not found in record {}'.format(field_name, record)
                Log.logger.warning(msg)
                return '%s: %s' % (Constant.SCRIPT_RESPONSE_NOTOK, msg)
        else:
            msg = 'No records returned for filter_name={} and filter_value={}'.format(filter_name, filter_value)
            Log.logger.warning(msg)
            return '%s: %s' % (Constant.SCRIPT_RESPONSE_NOTOK, msg)
    except Exception, ex:
        msg = 'Exception on /apiv1/db_update: {}'.format(ex)
        Log.logger.error(msg, exc_info=1)
        return '%s: %s' % (Constant.SCRIPT_RESPONSE_NOTOK, msg)
    finally:
        # db.session.remove()
        pass


@app.route('/apiv1/camera_alert/zone_name=<zone_name>&cam_name=<cam_name>&has_move=<has_move>')
def camera_alert(zone_name, cam_name, has_move):
    dispatcher.send(Constant.SIGNAL_CAMERA, zone_name=zone_name, cam_name=cam_name, has_move=has_move)
    return Constant.SCRIPT_RESPONSE_OK


def return_error(message):
    return message


def return_ok():
    return "all ok"


@app.route('/api')
def api():
    return '<a href="">API TEST</a>'


@app.route('/alexa/mpd', methods=['GET', 'POST'])
def alexa():
    if request.json is not None:
        Log.logger.info('ALEXA request request={}'.format(request.json['request']))
        if request.json['request']['intent'] is not None:
            slots = request.json['request']['intent']['slots']
            cmd = None
            zone = None
            for name, value in slots.iteritems():
                if name == 'Action':
                    cmd = value['value']
                elif name == 'Zone':
                    zone = value['value']
            if cmd is not None and zone is not None:
                Log.logger.info('ALEXA executes {} in {}'.format(cmd, zone))
                client = MPDClient()
                client.timeout = 5
                port = None
                port_list = get_param(Constant.P_MPD_PORT_ZONE).split(',')
                for pair in port_list:
                    if zone in pair:
                        port = int(pair.split('=')[1])
                        break
                if port is not None:
                    client.connect(get_param(Constant.P_MPD_SERVER), port)
                    if cmd == 'next':
                        client.next()
                    elif cmd == 'previous':
                        client.previous()
                    elif cmd == 'pause':
                        client.pause(1)
                    elif cmd == 'resume':
                        client.pause(0)
                    client.close()
                    client.disconnect()
                    response = 'Action done, ' + cmd + ' in zone ' + zone
                else:
                    response = 'Could not connect to MPD server, port not found'
            else:
                response = 'Warning, action not done, was ' + cmd + ' in zone ' + zone
        else:
            response = 'Warning, incomplete action'
    else:
        response = 'Invalid command'
    return '{ "version": "1.0", "sessionAttributes": {}, ' \
           '"response": { "outputSpeech": {"type": "PlainText", "text": " ' + response + ' "}, ' \
           '"shouldEndSession": true }}'


# @app.route('/ebooks', defaults={'req_path': ''})


# @app.route('/<path:req_path>')
def dir_listing(req_path):
    try:
        # BASE_DIR = '/media/ebooks'
        BASE_DIR = '/temp'

        # Joining the base and the requested path
        abs_path = os.path.join(BASE_DIR, req_path)

        # Return 404 if path doesn't exist
        if not os.path.exists(abs_path):
            return abort(404)

        # Check if path is a file and serve
        if os.path.isfile(abs_path):
            return send_file(abs_path)

        # Show directory contents
        files = os.listdir(abs_path)
        return render_template('files.html', files=files)
    except Exception, ex:
        return 'Error request={}, err={}'.format(req_path, ex)

Log.logger.info('API V1 module initialised')
