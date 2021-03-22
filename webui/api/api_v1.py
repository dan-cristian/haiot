import os
from pydispatch import dispatcher
from flask import abort, send_file, render_template, request
from main.flask_app import app
from main.logger_helper import L
from common import Constant, utils
from music import amp

__author__ = 'Dan Cristian <dan.cristian@gmail.com>'


class P:
    alexa_initialised = False
    lastfm_initialised = False
    mpd_initialised = False


def init_alexa():
    import cloud.alexa.mpd_run
    P.alexa_initialised = True


def init_lastfm():
    from cloud import lastfm
    P.lastfm_initialised = True


def init_mpd():
    from music import mpd
    P.mpd_initialised = True


def return_web_message(pin_value, ok_message='', err_message=''):
    if pin_value:
        return 'OK: {} \n {}={}'.format(ok_message, Constant.SCRIPT_RESPONSE_OK, pin_value)
    else:
        return 'ERR: {} \n {}={}'.format(err_message, Constant.SCRIPT_RESPONSE_NOTOK, pin_value)


@app.route('/apiv1/db_update/model_name=<model_name>&filter_name=<filter_name>'
           '&field_name=<field_name>&filter_value=<filter_value>&field_value=<field_value>')
def generic_db_update(model_name, filter_name, filter_value, field_name, field_value):
    try:
        L.l.info("Execute API generic_db_update model={} filter={} filtervalue={} field={} fieldvalue={}"
                 .format(model_name, filter_name, filter_value, field_name, field_value))
        pass
    except Exception as ex:
        msg = 'Exception on /apiv1/db_update: {}'.format(ex)
        L.l.error(msg, exc_info=1)
        return '%s: %s' % (Constant.SCRIPT_RESPONSE_NOTOK, msg)
    finally:
        # db.session.remove()
        pass


@app.route('/apiv1/camera_alert/zone_name=<zone_name>&cam_name=<cam_name>&has_move=<has_move>')
def camera_alert(zone_name, cam_name, has_move):
    dispatcher.send(Constant.SIGNAL_CAMERA, zone_name=zone_name, cam_name=cam_name, has_move=has_move)
    return Constant.SCRIPT_RESPONSE_OK


@app.route('/apiv1/amp_power/state=<power_state>&relay_name=<relay_name>&amp_zone_index=<amp_zone_index>')
def amp_power(power_state, relay_name, amp_zone_index=None):
    L.l.info("Amp_power relay={} state={} index={}".format(relay_name, power_state, amp_zone_index))
    result = amp.set_amp_power(int(power_state), relay_name, int(amp_zone_index))
    L.l.info("Done amp_power api request result={}".format(result))
    return result


def return_error(message):
    return message


def return_ok():
    return "all ok"


@app.route('/api')
def api():
    return '<a href="">API TEST</a>'


@app.route('/alexa/mpd', methods=['GET', 'POST'])
def alexa_mpd():
    if not P.alexa_initialised:
        init_alexa()
    if not P.mpd_initialised:
        init_mpd()
    return cloud.alexa.mpd_run.mpd(request)


@app.route('/test/lastfm/love', methods=['GET', 'POST'])
def test_lastfm_love():
    if not P.lastfm_initialised:
        init_lastfm()
    return lastfm.love(request)


@app.route('/lastfm/love', methods=['GET', 'POST'])
def lastfm_love():
    if not P.lastfm_initialised:
        init_lastfm()
    try:
        result = lastfm.love(request)
    except Exception as e:
        result = "{}".format(e)
    return result


@app.route('/test/lastfm/current', methods=['GET'])
def test_lastfm_current():
    if not P.lastfm_initialised:
        init_lastfm()
    try:
        result = lastfm.current()
    except Exception as e:
        result = "{}".format(e)
    return result


@app.route('/lastfm/current', methods=['GET'])
def lastfm_current():
    if not P.lastfm_initialised:
        init_lastfm()
    try:
        result = lastfm.current()
    except Exception as e:
        result = "{}".format(e)
    return result


@app.route('/lastfm/play_loved', methods=['GET'])
def lastfm_play_loved():
    if not P.lastfm_initialised:
        init_lastfm()
    return lastfm.get_loved_tracks_to_mpd()


@app.route('/lastfm/get_by_tag/<tag_name>', methods=['GET'])
def lastfm_get_by_tag(tag_name):
    if not P.lastfm_initialised:
        init_lastfm()
    return lastfm.get_by_tag(tag_name)


@app.route('/test/lastfm/play_loved', methods=['GET'])
def test_lastfm_play_loved():
    if not P.lastfm_initialised:
        init_lastfm()
    return lastfm.get_loved_tracks_to_mpd()


@app.route('/mpd/next', methods=['GET'])
def mpd_next():
    if not P.mpd_initialised:
        init_mpd()
    return mpd.next()


@app.route('/mpd/toggle', methods=['GET'])
def mpd_toggle():
    if not P.mpd_initialised:
        init_mpd()
    return mpd.toggle()


@app.route('/amp/zone_on/<zone_index>', methods=['GET'])
def amp_zone_on(zone_index):
    return amp.amp_zone_power(on=True, zone_index=zone_index)


@app.route('/amp/zone_off/<zone_index>', methods=['GET'])
def amp_zone_off(zone_index):
    return amp.amp_zone_power(on=False, zone_index=zone_index)

# &mac=<mac>&ip=<ip>&device=<device>
@app.route('/network/wifi_dhcp/operation=<operation>', methods=['GET'])
def wifi_dhcp(operation):
    L.l.info('Got wifi dhcp update {}'.format(operation))
    return operation


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
    except Exception as ex:
        return 'Error request={}, err={}'.format(req_path, ex)


L.l.info('API V1 module initialised')
