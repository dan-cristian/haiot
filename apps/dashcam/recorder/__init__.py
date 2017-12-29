import subprocess
import os
import time
import datetime
import traceback
import shutil
import usb_tool
import uploader
import utils
from pydispatch import dispatcher
try:
    from common import Constant
except Exception:
    pass

_has_picamera = False
try:
    import picamera
    _has_picamera = True
except Exception, ex:
    pass

__author__ = 'Dan Cristian<dan.cristian@gmail.com>'
initialised = False

class P:
    ffmpeg_pi = None
    ffmpeg_usb = None
    segment_duration = 900  # in seconds
    is_recording_pi = False
    is_recording_usb = False
    is_pi_camera_on = True
    is_usb_camera_on = True
    usb_sound_enabled = True
    root_mountpoint = '/'
    recordings_root = '/home/haiot/recordings/'
    dir_recordings_uploaded = recordings_root + 'uploaded'
    dir_recordings_safe = recordings_root + 'safe'
    dir_pipe_out = recordings_root + '/out/'
    pi_out_filename = recordings_root + '%Y-%m-%d_%H-%M-%S_pi.mp4'
    usb_out_filename = recordings_root + '%Y-%m-%d_%H-%M-%S_usb.mp4'
    pi_out_filepath_std = dir_pipe_out + 'pi.std'
    pi_out_filepath_err = dir_pipe_out + 'pi.err'
    pi_out_std = None
    pi_out_err = None
    usb_out_filepath_std = dir_pipe_out + 'usb.std'
    usb_out_filepath_err = dir_pipe_out + 'usb.err'
    usb_out_std = None
    usb_out_err = None
    usb_camera_keywords = 'C525'
    usb_camera_dev_path = '/dev/video0'
    usb_record_hw = '1:0'
    usb_max_resolution = '1280x720'
    pi_max_resolution = (1296, 972)
    win_camera_dev_name = "Integrated Camera"
    pi_thread = None
    usb_thread = None
    pi_framerate = 8
    usb_framerate = 8
    pi_camera = None
    pi_bitrate = 2000000
    inactivity_duration = 300  # seconds from last event after which camera will turn off
    last_move_time = None


def _get_win_cams():
    pass



def _run_ffmpeg_pi():
    print "Recording on {}".format(P.pi_out_filename)
    P.pi_out_std = open(P.pi_out_filepath_std, 'w')
    P.pi_out_err = open(P.pi_out_filepath_err, 'w')
    if P.ffmpeg_pi is None:
        P.ffmpeg_pi = subprocess.Popen([
            'ffmpeg', '-y', '-r', str(P.pi_framerate), '-i', '-', '-vcodec', 'copy',
            '-f', 'segment', '-segment_time', str(P.segment_duration), '-segment_format', 'mp4',
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
def _run_ffmpeg_usb():
    if P.ffmpeg_usb is None:
        P.usb_out_std = open(P.usb_out_filepath_std, 'w')
        P.usb_out_err = open(P.usb_out_filepath_err, 'w')

        P.usb_record_hw = usb_tool.get_usb_audio(P.usb_camera_keywords)
        P.usb_camera_dev_path = usb_tool.get_usb_dev(P.usb_camera_keywords)

        if P.usb_record_hw is not None:
            audio = ['-i', 'hw:{}'.format(P.usb_record_hw)]
        else:
            audio = ['-na']

        if P.usb_camera_dev_path is not None:
            P.ffmpeg_usb = subprocess.Popen(
                ['ffmpeg', '-y', '-f', 'alsa', '-thread_queue_size', '8192', '-ac', '1'] + audio +
                ['-r', str(P.usb_framerate),
                 '-f', 'video4linux2', '-thread_queue_size', '8192', '-i', P.usb_camera_dev_path,
                 '-vf', 'drawtext=text=\'%{localtime\:%c}\':fontcolor=white@0.8:fontsize=32:x=10:y=10',
                 '-s', P.usb_max_resolution, "-c:v", "h264_omx", "-b:v", "2000k",
                 '-frag_duration', '1000', '-f', 'segment', '-segment_time', str(P.segment_duration),
                 '-reset_timestamps', '1', '-force_key_frames', 'expr:gte(t,n_forced*10)', '-strftime', '1',
                 '-nostats', '-loglevel', 'info', P.usb_out_filename],
                stdin=subprocess.PIPE, stdout=P.usb_out_std, stderr=P.usb_out_err)


def _kill_proc(keywords):
    kill_try = 0
    while True:
        pid = utils.get_proc(keywords)
        if pid is not None:
            print('Found process {} with pid {}, killing attempt {}'.format(keywords, pid, kill_try))
            if kill_try == 0:
                os.kill(pid, 15)
            else:
                os.kill(pid, 9)
            kill_try += 1
        else:
            print('Process to kill not found with keywords {} in attempt {}'.format(keywords, kill_try))
            break


def _recover_usb():
    src = P.usb_out_filepath_err
    # make a copy for debug
    print('Copy usb output file for debug')
    shutil.copy(src, src + '.' + str(time.time()))
    ferr = open(src)
    contents = ferr.read()
    ferr.close()

    is_exit_normal = 'Exiting normally, received signal' in contents
    if is_exit_normal:
        print('Exit was normal, nothing to do to recover')
    else:
        is_exit_io_err = 'Input/output error' in contents or 'no soundcards found' in contents
        if is_exit_io_err:
            print('Found an USB I/O error')
        else:
            print('Unknown USB error')
            print(contents)
        usb_tool.reset_usb(P.usb_camera_keywords)


def _usb_init():
    print("Recording USB")
    try:
        _kill_proc(P.usb_out_filename)
        if Constant.IS_OS_WINDOWS():
            _run_ffmpeg_usb_win()
        else:
            _run_ffmpeg_usb()
        if P.ffmpeg_usb is not None and P.ffmpeg_usb._child_created:
            print("Recording started")
            P.is_recording_usb = True
        else:
            print("Recording process not created")
    except Exception, ex:
        print("Unable to initialise USB camera, ex={}".format(ex))


def _usb_record_loop():
    if P.is_recording_usb:
        P.ffmpeg_usb.poll()
        if P.ffmpeg_usb.returncode is not None:
            print("usb record exit with code {}".format(P.ffmpeg_usb.returncode))
            if P.ffmpeg_usb.returncode != 0:
                print("USB recording stopped")
            else:
                print("USB exit, not an error?")
            _usb_stop()
        else:
            pass
    else:
        print("USB not recording")


def _pi_record_loop():
    if P.is_recording_pi:
        P.pi_camera.annotate_text = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        P.ffmpeg_pi.poll()
        if P.ffmpeg_pi.returncode is not None:
            print("PI record exit with code {}".format(P.ffmpeg_pi.returncode))
            if P.ffmpeg_pi.returncode != 0:
                print("PI recording stopped with error")
            else:
                print("PI exit, not an error?")
            _pi_stop()
        else:
            pass
    else:
        print("PI not recording")


def _pi_init():
    global _has_picamera
    if _has_picamera:
        try:
            _kill_proc(P.pi_out_filename)
            P.pi_camera = picamera.PiCamera()
            P.pi_camera.resolution = P.pi_max_resolution
            P.pi_camera.framerate = P.pi_framerate
            P.pi_camera.annotate_background = picamera.Color('black')
            print("Recording PI")
            _run_ffmpeg_pi()
            P.pi_camera.start_recording(P.ffmpeg_pi.stdin, format='h264', bitrate=P.pi_bitrate)
            if P.ffmpeg_pi._child_created:
                print("Recording PI started")
                P.is_recording_pi = True
        except Exception, ex:
            if 'Camera is not enabled' in str(ex):
                _has_picamera = False
                P.is_pi_camera_on = False
            print("Unable to initialise picamera, ex={}".format(ex))
    else:
        #print("No picamera module")
        P.is_pi_camera_on = False


def _pi_stop():
    print "Stopping PI"
    try:
        P.is_recording_pi = False
        if P.pi_camera is not None:
            if P.ffmpeg_pi is not None:
                try:
                    P.ffmpeg_pi.terminate()
                except Exception:
                    pass
                P.ffmpeg_pi = None
            try:
                print("Camera closed={} recording={}".format(P.pi_camera.closed, P.pi_camera.recording))
                P.pi_camera.stop_recording()
            except Exception, ex:
                print("Exception on pi camera stop, ex={}".format(ex))
            try:
                print("Camera closed={} recording={}".format(P.pi_camera.closed, P.pi_camera.recording))
                P.pi_camera.close()
            except Exception, ex:
                print("Exception on pi camera close, ex={}".format(ex))
            print("Camera closed={} recording={}".format(P.pi_camera.closed, P.pi_camera.recording))
            if P.pi_out_std is not None:
                P.pi_out_std.close()
            if P.pi_out_err is not None:
                P.pi_out_err.close()
    except Exception, ex:
        print("Error in pi_stop, ex={}".format(ex))
        print(traceback.print_exc())


def _usb_stop():
    print "Stopping USB"
    P.is_recording_usb = False
    if P.ffmpeg_usb is not None:
        try:
            P.ffmpeg_usb.terminate()
        except Exception:
            pass
        P.ffmpeg_usb = None
        if P.usb_out_std is not None:
            P.usb_out_std.close()
        if P.usb_out_err is not None:
            P.usb_out_err.close()


def _handle_event_alarm(zone_name, pin_connected):
    print("Got alarm in {} with pin connected {}".format(zone_name, pin_connected))
    P.last_move_time = datetime.datetime.now()
    P.is_usb_camera_on = True
    P.is_pi_camera_on = True


def _set_camera_state():
    now = datetime.datetime().now()
    move_lapsed = (now - P.last_move_time).total_seconds()
    if move_lapsed > P.inactivity_duration:
        print("Stopping cameras as no activity in the last {} seconds".format(move_lapsed))
        P.is_pi_camera_on = False
        P.is_usb_camera_on = False


def unload():
    global initialised
    _pi_stop()
    _usb_stop()
    uploader.unload()
    initialised = False


def init():
    global initialised
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
    if P.is_pi_camera_on:
        _pi_init()
    if P.is_usb_camera_on:
        _usb_init()
    dispatcher.connect(_handle_event_alarm, signal=Constant.SIGNAL_ALARM, sender=dispatcher.Any)
    initialised = True


def thread_run():
    try:
        _set_camera_state()
        if P.is_pi_camera_on:
            if P.is_recording_pi:
                _pi_record_loop()
            else:
                print("Starting PI camera, should have been on")
                _pi_init()
        if P.is_usb_camera_on:
            if P.is_recording_usb:
                _usb_record_loop()
            else:
                print("Starting USB camera, should have been on")
                _recover_usb()
                _usb_init()
        if not P.is_pi_camera_on and P.is_recording_pi:
            print("Stopping PI recording")
            _pi_stop()
        if not P.is_usb_camera_on and P.is_recording_usb:
            print("Stopping USB recording")
            _usb_stop()


    except Exception, ex:
        print "Error in recorder thread_run, ex={}".format(ex)
        print traceback.print_exc()


if __name__ == '__main__':
    init()
    thread_run()
