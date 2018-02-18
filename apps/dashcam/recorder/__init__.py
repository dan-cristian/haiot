import subprocess
import os
import time
import datetime
import traceback
import shutil
import usb_tool
import uploader
import utils
from recordtype import recordtype
from pydispatch import dispatcher
try:
    from main.logger_helper import L
except Exception:
    class L:
        class l:
            @staticmethod
            def info(msg): print msg
            @staticmethod
            def warning(msg): print msg
            @staticmethod
            def error(msg): print msg

try:
    from common import Constant
except Exception:
    L.l.error("Cannot import Constant, running standalone I guess")

_has_picamera_module = False
try:
    import picamera
    _has_picamera_module = True
except Exception, ex:
    pass

__author__ = 'Dan Cristian<dan.cristian@gmail.com>'
initialised = False
thread_tick = 1
CamParam = recordtype(
    'CamParam', 'name is_on is_recording ffmpeg_proc rec_filename pipe_std_path pipe_err_path std_pipe err_pipe')


class P:
    cam_list = {}  # detected camera list
    cam_param = {}  # camera parameters
    ffmpeg_pi = None  # process encoding
    #ffmpeg_usb = {}  # list with usb process encoding
    segment_duration = 900  # in seconds
    is_recording_pi = False
    #is_recording_usb = {}
    is_one_recording_usb = False
    is_pi_camera_detected = True
    is_recording_on = True
    is_one_usb_camera_detected = False
    #is_usb_camera_detected = {}
    #usb_sound_enabled = True
    # comma needed as suffix for flip filter
    usb_rotation_filter = {'HD Webcam C525': 'vflip,', 'UVC Camera (046d:081b)': '', 'HD USB Camera': ''}
    pi_rotation_degree = 90
    root_mountpoint = '/'  # to check space available for recording
    recordings_root = '/home/haiot/recordings/'  # recording is stored here
    dir_recordings_uploaded = recordings_root + 'uploaded'  # video moved here after upload
    dir_recordings_safe = recordings_root + 'safe'  # not yet used
    dir_pipe_out = recordings_root + '/out/'
    pi_out_filename = recordings_root + '%Y-%m-%d_%H-%M-%S_pi.mkv'
    usb_out_filename_template = recordings_root + '%Y-%m-%d_%H-%M-%S_usb_x.mkv'  # x to be replaced with camera ID
    #usb_out_filename = {}
    pi_out_filepath_std = dir_pipe_out + 'pi.std'
    pi_out_filepath_err = dir_pipe_out + 'pi.err'
    #pi_out_std = None
    #pi_out_err = None
    usb_out_filepath_std_template = dir_pipe_out + 'usb_x.std'
    usb_out_filepath_err_template = dir_pipe_out + 'usb_x.err'
    #usb_out_filepath_std = {}
    #usb_out_filepath_err = {}
    #usb_out_std = {}
    #usb_out_err = {}
    #usb_camera_name = {}
    #usb_camera_dev_path = {}  # '/dev/video0'
    #usb_record_hw = {}  # '1:0'
    usb_max_resolution = '1280x720'
    pi_max_resolution = (1296, 972)
    win_camera_dev_name = "Integrated Camera"
    pi_thread = None
    usb_thread = {}  # None
    pi_framerate = 8
    usb_framerate = 8
    pi_camera = None
    pi_bitrate = 2000000
    inactivity_duration = 300  # seconds from last event after which camera will turn off
    last_move_time = None
    last_clock_time = None
    usb_recover_count = 0
    usb_recover_attempts_limit = 5  # number of recovery attempts before pausing
    usb_recover_pause = 30  # pause x seconds between usb recovery attempts
    usb_last_recovery_attempt = datetime.datetime.min
    usb_last_cam_detect_attempt = datetime.datetime.min
    gps_lat = 0
    gps_lon = 0
    gps_hspeed = 0
    gps_alt = 0
    overlay_text_file = '/tmp/overlay_text'


def _get_win_cams():
    pass


def _get_overlay_text():
    speed = int(P.gps_hspeed)
    alt = int(P.gps_alt)
    time_txt = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return '{} {}kph {}m {},{} '.format(time_txt, speed, alt, P.gps_lat, P.gps_lon)


def _write_overlay_text():
    f = open(P.overlay_text_file, 'w')
    f.write(_get_overlay_text())
    f.close()


def _run_ffmpeg_pi():
    L.l.info("Recording on {}".format(P.pi_out_filename))
    P.pi_out_std = open(P.pi_out_filepath_std, 'w')
    P.pi_out_err = open(P.pi_out_filepath_err, 'w')
    if P.ffmpeg_pi is None:
        P.ffmpeg_pi = subprocess.Popen([
            'ffmpeg', '-y', '-r', str(P.pi_framerate), '-i', '-', '-vcodec', 'copy',
            '-f', 'segment', '-segment_time', str(P.segment_duration),
            '-reset_timestamps', '1', '-force_key_frames', '"expr:gte(t,n_forced*10)"',
            '-frag_duration', '1000', '-strftime', '1', '-an',
            '-nostats', '-loglevel', 'info', P.pi_out_filename],
            stdin=subprocess.PIPE, stdout=P.pi_out_std, stderr=P.pi_out_err)


def _run_ffmpeg_usb_win(no_sound=True):
    if P.ffmpeg_usb is None:
        P.ffmpeg_usb = subprocess.Popen([
            'ffmpeg', '-y', '-f', 'dshow', '-i', 'video={}'.format(P.win_camera_dev_name),
            '-an', '-c:v', 'libx264', '-b:v', '3000k', '-r', P.usb_framerate,
            '-f', 'segment', '-segment_time', P.segment_duration, '-segment_format', 'mp4',
            '-reset_timestamps', '1',
            '-force_key_frames', 'expr:gte(t,n_forced*10)',
            #'-vf', '"drawtext=fontfile=/Windows/Fonts/arial.ttf: text=\'%{localtime\:%c}\': fontcolor=white@0.8: fontsize=32: x=10: y=10"',
            '-s', '800x600', '-frag_duration', '1000',
            '-strftime', '1',
            P.usb_out_filename])


# ffmpeg -y -f alsa -thread_queue_size 16384 -ac 1 -i hw:1 -r 8 -f video4linux2 -thread_queue_size 8192 -i /dev/video0 -vf "drawtext=text='%{localtime\:%c}': fontcolor=white@0.8: fontsize=32: x=10: y=10" -s 1280x720 -c:v h264_omx -b:v 3000k -frag_duration 1000 -f segment -segment_time 3600 -reset_timestamps 1  -force_key_frames "expr:gte(t,n_forced*2)" -strftime 1 /home/haiot/recordings/usb_%Y-%m-%d_%H-%M-%S.mp4
def _run_ffmpeg_usb(cam_name):
    L.l.info("Starting ffmpeg process for cam {}".format(cam_name))
    res = False
    cp = P.cam_param[cam_name]
    cam = P.cam_list[cam_name]
    if cp.ffmpeg_proc is None:
        cp.std_pipe = open(cp.pipe_std_path, 'w')
        cp.err_pipe = open(cp.pipe_err_path, 'w')

        if cam.devpath is None:
            res = False
            L.l.error("No camera detected before starting USB recording")
        else:
            if cam.audio is not None:
                audio = ['-i', 'hw:{}'.format(cam.audio)]
            else:
                L.l.warning("USB audio not detected, starting record without audio")
                audio = ['-an']
            if cam_name in P.usb_rotation_filter:
                rotation = P.usb_rotation_filter[cam_name]
            else:
                L.l.info("No specific rotation setting for camera {}, assuming none".format(cam_name))
                rotation = ''
            # https://superuser.com/questions/578321/how-to-rotate-a-video-180-with-ffmpeg/578329#578329
            # '-vf', rotation + 'drawtext=text=\'%{localtime\:%c}\':fontcolor=white@0.8:fontsize=16:x=10:y=10',
            cp.ffmpeg_proc = subprocess.Popen(
                ['ffmpeg', '-y', '-f', 'alsa', '-thread_queue_size', '8192', '-ac', '1'] + audio +
                ['-r', str(P.usb_framerate), '-f', 'video4linux2', '-thread_queue_size', '8192', '-i', cam.devpath,
                 '-vf', rotation + 'drawtext=textfile=' + P.overlay_text_file
                + ':fontcolor=white@0.8:fontsize=16:x=10:y=10:reload=1',
                 '-s', P.usb_max_resolution, "-c:v", "h264_omx", "-b:v", "2000k",
                 '-frag_duration', '1000', '-f', 'segment', '-segment_time', str(P.segment_duration),
                 '-reset_timestamps', '1', '-force_key_frames', 'expr:gte(t,n_forced*10)', '-strftime', '1',
                 '-nostats', '-loglevel', 'info', cp.rec_filename],
                stdin=subprocess.PIPE, stdout=cp.std_pipe, stderr=cp.err_pipe)
            res = True
    else:
        L.l.warning("ffmpeg not null on record start")
    return res


def _kill_proc(keywords):
    kill_try = 0
    while True:
        pid = utils.get_proc(keywords)
        if pid is not None:
            L.l.info('Found process {} with pid {}, killing attempt {}'.format(keywords, pid, kill_try))
            if kill_try == 0:
                os.kill(pid, 15)
            else:
                os.kill(pid, 9)
            kill_try += 1
        else:
            L.l.info('Process to kill not found with keywords {} in attempt {}'.format(keywords, kill_try))
            break


def _save_usb_err_output(cam_name):
    cp = P.cam_param[cam_name]
    # make a copy for debug
    L.l.info('Copy usb output file for debug')
    shutil.copy(cp.pipe_err_path, cp.pipe_err_path+ '.' + str(time.time()))
    ferr = open(cp.pipe_err_path)
    contents = ferr.read()
    ferr.close()
    return contents


def _recover_usb(cam_name):
    cp = P.cam_param[cam_name]
    if P.usb_recover_count <= P.usb_recover_attempts_limit:
        if not os.path.isfile(cp.pipe_err_path):
            L.l.info('Unknown USB error, no recent ffmpeg output found')
            usb_tool.reset_usb(cam_name)
            time.sleep(5)  # let camera to be detected
        else:
            contents = _save_usb_err_output(cam_name)
            is_exit_normal = 'Exiting normally, received signal' in contents
            if is_exit_normal:
                L.l.info('Exit was normal, nothing to do to recover')
            else:
                is_exit_io_err = 'Input/output error' in contents or 'no soundcards found' in contents
                if is_exit_io_err:
                    L.l.info('Found an USB I/O error')
                else:
                    L.l.info('Unknown USB error, details below:')
                    L.l.info(contents)
                usb_tool.reset_usb(cam_name)
                time.sleep(5)  # let camera to be detected
        P.usb_recover_count += 1
        if P.usb_recover_count == P.usb_recover_attempts_limit:
            P.usb_last_recovery_attempt = datetime.datetime.now()
            P.is_recording_on = False
            L.l.info('Pausing USB recover attempts')
    else:
        if (datetime.datetime.now() - P.usb_last_recovery_attempt).total_seconds() > P.usb_recover_pause:
            P.usb_recover_count = 0


def _usb_init():
    delta = (datetime.datetime.now() - P.usb_last_cam_detect_attempt).total_seconds()
    if delta <= P.usb_recover_pause:
        return
    P.usb_last_cam_detect_attempt = datetime.datetime.now()
    new_cam_list = usb_tool.get_usb_camera_list()
    L.l.info("Found {} USB cameras".format(len(new_cam_list)))
    for cam in new_cam_list.itervalues():
        if cam.name not in P.cam_list:
            L.l.info("Initialising new USB cam {}".format(cam.name))
            P.cam_list[cam.name] = cam
            cp = CamParam(name=cam.name, is_on=True, is_recording=False, ffmpeg_proc=None, rec_filename=None,
                          pipe_std_path=None, pipe_err_path=None, std_pipe=None, err_pipe=None)
            cp.pipe_std_path = P.usb_out_filepath_std_template.replace('_x', '_' + cam.name.strip().replace(' ', '_'))
            cp.pipe_err_path = P.usb_out_filepath_err_template.replace('_x', '_' + cam.name.strip().replace(' ', '_'))
            cp.rec_filename = P.usb_out_filename_template.replace('_x', '_' + cam.name.strip().replace(' ', '_'))
            if os.path.isfile(cp.pipe_err_path):
                os.remove(cp.pipe_err_path)
            P.cam_param[cam.name] = cp
        else:
            L.l.info("Cam {} already initialised".format(cam.name))
            cp = P.cam_param[cam.name]
        try:
            L.l.info("Starting USB Recording on {}".format(cam.name))
            _kill_proc(cp.rec_filename)
            # if Constant.IS_OS_WINDOWS():
            #    _run_ffmpeg_usb_win()
            # else:
            _run_ffmpeg_usb(cam.name)
            if cp.ffmpeg_proc is not None and cp.ffmpeg_proc._child_created:
                L.l.info("Recording started on {}".format(cam.name))
                cp.is_recording = True
                P.is_one_recording_usb = True
                P.is_one_usb_camera_detected = True
            else:
                L.l.info("Recording process not created for {}".format(cam.name))
        except Exception, ex:
            L.l.info("Unable to initialise USB camera, ex={}".format(ex))
            traceback.print_exc()


def _usb_record_loop():
    for cp in P.cam_param.itervalues():
        if cp.is_recording:
            if cp.ffmpeg_proc is not None:
                cp.ffmpeg_proc.poll()
                if cp.ffmpeg_proc.returncode is not None:
                    L.l.info("USB record exit with code {}".format(cp.ffmpeg_proc.returncode))
                    if cp.ffmpeg_proc.returncode != 0:
                        L.l.info("USB recording stopped for camera {}".format(cp.name))
                        _save_usb_err_output(cp.name)
                    else:
                        L.l.info("USB exit, not an error for camera {}?".format(cp.name))
                    _usb_stop(cp.name)
                else:
                    pass
            else:
                L.l.error("ffmpeg process is null for camera {}, stopping".format(cp.name))
                _save_usb_err_output(cp.name)
                _usb_stop(cp.name)


def _pi_record_loop():
    if P.is_recording_pi:
        P.pi_camera.annotate_text = _get_overlay_text()
        P.ffmpeg_pi.poll()
        if P.ffmpeg_pi.returncode is not None:
            L.l.info("PI record exit with code {}".format(P.ffmpeg_pi.returncode))
            if P.ffmpeg_pi.returncode != 0:
                L.l.info("PI recording stopped with error")
            else:
                L.l.info("PI exit, not an error?")
            _pi_stop()
        else:
            pass
    else:
        L.l.info("PI not recording")


def _pi_init():
    global _has_picamera_module
    if _has_picamera_module and P.is_pi_camera_detected:
        try:
            L.l.info("Starting PI Recording")
            _kill_proc(P.pi_out_filename)
            P.pi_camera = picamera.PiCamera()
            P.pi_camera.resolution = P.pi_max_resolution
            P.pi_camera.framerate = P.pi_framerate
            P.pi_camera.rotation = P.pi_rotation_degree
            P.pi_camera.annotate_background = picamera.Color('black')
            _run_ffmpeg_pi()
            P.pi_camera.start_recording(P.ffmpeg_pi.stdin, format='h264', bitrate=P.pi_bitrate)
            if P.ffmpeg_pi._child_created:
                L.l.info("Recording PI started")
                P.is_recording_pi = True
                P.is_pi_camera_detected = True
        except Exception, ex:
            if 'Camera is not enabled' in str(ex):
                _has_picamera_module = False
                P.is_pi_camera_detected = False
                #P.is_recording_on = False
                L.l.error("PI camera not found, disabling the camera, no recording from now")
            L.l.info("Unable to initialise picamera, ex={}".format(ex))
    #else:
    #    L.l.info("No picamera module, recording cannot start")


def _pi_stop():
    L.l.info("Stopping PI")
    try:
        P.is_recording_pi = False
        if P.pi_camera is not None:
            if P.ffmpeg_pi is not None:
                try:
                    P.ffmpeg_pi.terminate()
                finally:
                    P.ffmpeg_pi = None
            try:
                #L.l.info("Camera closed={} recording={}".format(P.pi_camera.closed, P.pi_camera.recording))
                P.pi_camera.stop_recording()
            except Exception, ex:
                L.l.info("Exception on pi camera stop, ex={}".format(ex))
            try:
                #L.l.info("Camera closed={} recording={}".format(P.pi_camera.closed, P.pi_camera.recording))
                P.pi_camera.close()
            except Exception, ex:
                L.l.info("Exception on pi camera close, ex={}".format(ex))
            L.l.info("Camera closed={} recording={}".format(P.pi_camera.closed, P.pi_camera.recording))
            if P.pi_out_std is not None:
                P.pi_out_std.close()
            if P.pi_out_err is not None:
                P.pi_out_err.close()
    except Exception, ex:
        L.l.info("Error in pi_stop, ex={}".format(ex))
        L.l.info(traceback.print_exc())


def _usb_stop(cam_name):
    L.l.info("Stopping USB {}".format(cam_name))
    #cam = P.cam_list[cam_name]
    cp = P.cam_param[cam_name]
    #P.is_recording_usb = False
    if cp.ffmpeg_proc is not None:
        try:
            cp.ffmpeg_proc.terminate()
        except Exception:
            pass
        cp.ffmpeg_proc = None
        if cp.std_pipe is not None:
            cp.std_pipe.close()
            cp.std_pipe = None
        if cp.err_pipe is not None:
            cp.err_pipe.close()
            cp.err_pipe = None


def _usb_stop_all():
    for cp in P.cam_param.itervalues():
        _usb_stop(cp.name)
    P.is_one_recording_usb = False


def _handle_event_gps(lat, lon, hspeed, alt):
    P.gps_lat = lat
    P.gps_lon = lon
    P.gps_hspeed = hspeed
    P.gps_alt = alt


def _handle_event_alarm(zone_name, alarm_pin_name, pin_connected):
    L.l.info("Got alarm in {} name={} with pin connected {}".format(zone_name, alarm_pin_name, pin_connected))
    if alarm_pin_name == 'car vibrate':
        P.last_move_time = datetime.datetime.now()
        P.usb_last_cam_detect_attempt = datetime.datetime.min
        P.is_recording_on = True
        P.usb_recover_count = 0
        P.is_recording_on = True
    elif alarm_pin_name == 'pidash battery low':
        if not pin_connected:
            L.l.info("Battery is LOW")
            P.is_recording_on = False
            P.is_recording_on = False
        else:
            L.l.info("Battery is OK")
    elif alarm_pin_name == 'pidash low power':
        L.l.info("PI power is LOW")
        P.is_recording_on = False
        P.is_recording_on = False
        dispatcher.send(Constant.SIGNAL_EMAIL_NOTIFICATION, subject="Pidash power low", body="got low power signal")


def _set_camera_state():
    now = datetime.datetime.now()
    move_lapsed = (now - P.last_move_time).total_seconds()
    if (move_lapsed > P.inactivity_duration) and (P.is_one_recording_usb or P.is_recording_pi):
        L.l.info("Stopping cameras as no activity in the last {} seconds".format(move_lapsed))
        P.is_recording_on = False


def unload():
    global initialised
    _pi_stop()
    _usb_stop()
    uploader.unload()
    initialised = False


def init():
    global initialised, _has_picamera_module
    if not _has_picamera_module:
        P.is_pi_camera_detected = False
    P.last_clock_time = datetime.datetime.now()
    if not os.path.exists(P.recordings_root):
        os.makedirs(P.recordings_root)
    if not os.path.exists(P.dir_recordings_uploaded):
        os.makedirs(P.dir_recordings_uploaded)
    if not os.path.exists(P.dir_recordings_safe):
        os.makedirs(P.dir_recordings_safe)
    if not os.path.exists(P.dir_pipe_out):
        os.makedirs(P.dir_pipe_out)
    uploader.P.root_folder = P.recordings_root
    uploader.P.uploaded_folder = P.dir_recordings_uploaded
    uploader.P.root_mountpoint = P.root_mountpoint
    uploader.P.std_out_folder = P.recordings_root + P.dir_pipe_out
    P.last_move_time = datetime.datetime.now()
    if P.is_recording_on:
        if P.is_pi_camera_detected:
            L.l.info("Initialising PI camera")
            _pi_init()
        L.l.info("Initialising USB cameras")
        _usb_init()
    try:
        dispatcher.connect(_handle_event_alarm, signal=Constant.SIGNAL_ALARM, sender=dispatcher.Any)
        dispatcher.connect(_handle_event_gps, signal=Constant.SIGNAL_GPS, sender=dispatcher.Any)
    except Exception, ex:
        L.l.error("Unable to connect to alarm dispatch, ex={}".format(ex))
    initialised = True


def thread_run():
    try:
        _write_overlay_text()
        # detect ntp time drift, if clock changed adjust last move to avoid sudden recording stop
        if (datetime.datetime.now() - P.last_clock_time).total_seconds() > thread_tick + 60:
            P.last_move_time = datetime.datetime.now()
            L.l.warning("Detected clock adjustment")
        P.last_clock_time = datetime.datetime.now()
        _set_camera_state()
        if P.is_recording_on:
            if P.is_recording_pi:
                _pi_record_loop()
            else:
                if P.is_pi_camera_detected:
                    L.l.info("Starting PI camera, should have been on")
                _pi_init()
            if P.is_one_recording_usb:
                #if P.is_recording_usb:
                _usb_record_loop()
            else:
                if P.is_one_usb_camera_detected:  # stay silent if recovery failed
                    L.l.info("Starting USB camera, should have been on")
                _usb_init()
        if not P.is_recording_on and P.is_recording_pi:
            L.l.info("Stopping PI recording")
            _pi_stop()
        if not P.is_recording_on and P.is_one_recording_usb:
            L.l.info("Stopping USB recording")
            _usb_stop_all()
    except Exception, ex:
        print "Error in recorder thread_run, ex={}".format(ex)
        print traceback.print_exc()


if __name__ == '__main__':
    init()
    thread_run()
