try:
    import picamera
    __has_picamera = True
except Exception, ex:
    __has_picamera = False
import subprocess
import os
import time
import datetime as dt
import traceback
import shutil
import usb_tool
try:
    from common import Constant
except Exception:
    pass

__author__ = 'Dan Cristian<dan.cristian@gmail.com>'
initialised = False

class Params:
    ffmpeg_pi = None
    ffmpeg_usb = None
    segment_duration = 900  # in seconds
    is_recording_pi = False
    is_recording_usb = False
    is_pi_camera_on = True
    is_usb_camera_on = True
    usb_sound_enabled = True
    recordings_root = '/home/haiot/recordings/'
    pi_out_filename = recordings_root + '%Y-%m-%d_%H-%M-%S_pi.mp4'
    usb_out_filename = recordings_root + '%Y-%m-%d_%H-%M-%S_usb.mp4'
    pi_out_filename_std = 'pi.std'
    pi_out_filename_err = 'pi.err'
    pi_out_std = None
    pi_out_err = None
    usb_out_filename_std = 'usb.std'
    usb_out_filename_err = 'usb.err'
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


def _get_win_cams():
    pass



def _run_ffmpeg_pi():
    print "Recording on {}".format(Params.pi_out_filename)
    Params.pi_out_std = open(Params.recordings_root + Params.pi_out_filename_std, 'w')
    Params.pi_out_err = open(Params.recordings_root + Params.pi_out_filename_err, 'w')
    if Params.ffmpeg_pi is None:
        Params.ffmpeg_pi = subprocess.Popen([
            'ffmpeg', '-y', '-r', str(Params.pi_framerate), '-i', '-', '-vcodec', 'copy',
            '-f', 'segment', '-segment_time', str(Params.segment_duration), '-segment_format', 'mp4',
            '-reset_timestamps', '1', '-force_key_frames', '"expr:gte(t,n_forced*10)"',
            '-frag_duration', '1000', '-strftime', '1', '-an',
            '-nostats', '-loglevel', 'info', Params.pi_out_filename],
            stdin=subprocess.PIPE, stdout=Params.pi_out_std, stderr=Params.pi_out_err)


def _run_ffmpeg_usb_win(no_sound=True):
    if Params.ffmpeg_usb is None:
        Params.ffmpeg_usb = subprocess.Popen([
            'ffmpeg', '-y', '-f', 'dshow', '-i', 'video={}'.format(Params.win_camera_dev_name),
            '-an', '-c:v', 'libx264', '-b:v', '3000k', '-r', Params.usb_framerate,
            '-f', 'segment', '-segment_time', Params.segment_duration, '-segment_format', 'mp4',
            '-reset_timestamps', '1',
            '-force_key_frames', 'expr:gte(t,n_forced*10)',
            #'-vf', '"drawtext=fontfile=/Windows/Fonts/arial.ttf: text=\'%{localtime\:%c}\': fontcolor=white@0.8: fontsize=32: x=10: y=10"',
            '-s', '800x600', '-frag_duration', '1000',
            '-strftime', '1',
            Params.usb_out_filename])


# ffmpeg -y -f alsa -thread_queue_size 16384 -ac 1 -i hw:1 -r 8 -f video4linux2 -thread_queue_size 8192 -i /dev/video0 -vf "drawtext=text='%{localtime\:%c}': fontcolor=white@0.8: fontsize=32: x=10: y=10" -s 1280x720 -c:v h264_omx -b:v 3000k -frag_duration 1000 -f segment -segment_time 3600 -reset_timestamps 1  -force_key_frames "expr:gte(t,n_forced*2)" -strftime 1 /home/haiot/recordings/usb_%Y-%m-%d_%H-%M-%S.mp4
def _run_ffmpeg_usb():
    if Params.ffmpeg_usb is None:
        Params.usb_out_std = open(Params.recordings_root + Params.usb_out_filename_std, 'w')
        Params.usb_out_err = open(Params.recordings_root + Params.usb_out_filename_err, 'w')

        Params.usb_record_hw = usb_tool.get_usb_audio(Params.usb_camera_keywords)
        Params.usb_camera_dev_path = usb_tool.get_usb_dev(Params.usb_camera_keywords)

        Params.ffmpeg_usb = subprocess.Popen(
            ['ffmpeg', '-y', '-f', 'alsa', '-thread_queue_size', '8192', '-ac', '1',
             '-i', 'hw:{}'.format(Params.usb_record_hw), '-r', str(Params.usb_framerate),
             '-f', 'video4linux2', '-thread_queue_size', '8192', '-i', Params.usb_camera_dev_path,
             '-vf', 'drawtext=text=\'%{localtime\:%c}\':fontcolor=white@0.8:fontsize=32:x=10:y=10',
             '-s', Params.usb_max_resolution, "-c:v", "h264_omx", "-b:v", "2000k",
             '-frag_duration', '1000', '-f', 'segment', '-segment_time', str(Params.segment_duration),
             '-reset_timestamps', '1', '-force_key_frames', 'expr:gte(t,n_forced*10)', '-strftime', '1',
             '-nostats', '-loglevel', 'info', Params.usb_out_filename],
            stdin=subprocess.PIPE, stdout=Params.usb_out_std, stderr=Params.usb_out_err)


def _recover_usb():
    src = Params.recordings_root + Params.usb_out_filename_err
    # make a copy for debug
    shutil.copy(src, src + '.' + time.time())
    ferr = open(src)
    contents = ferr.read()
    ferr.close()

    is_exit_normal = 'Exiting normally, received signal' in contents
    if is_exit_normal:
        print('Exit was normal, nothing to do to recover')
    else:
        print('Unknown error')
        print(contents)


def _usb_init():
    print("Recording USB")
    try:
        if Constant.IS_OS_WINDOWS():
            _run_ffmpeg_usb_win()
        else:
            _run_ffmpeg_usb()
            print("Recording started")
        if Params.ffmpeg_usb._child_created:
            Params.is_recording_usb = True
        else:
            print("Recording process not created")
    except Exception, ex:
        print("Unable to initialise USB camera, ex={}".format(ex))


def _usb_record_loop():
    if Params.is_recording_usb:
        Params.ffmpeg_usb.poll()
        if Params.ffmpeg_usb.returncode is not None:
            print("usb record exit with code {}".format(Params.ffmpeg_usb.returncode))
            if Params.ffmpeg_usb.returncode != 0:
                print("USB recording stopped")
            else:
                print("USB exit, not an error?")
            _usb_stop()
        else:
            pass
    else:
        print("USB not recording")


def _pi_record_loop():
    if Params.is_recording_pi:
        Params.pi_camera.annotate_text = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        Params.ffmpeg_pi.poll()
        if Params.ffmpeg_pi.returncode is not None:
            print("PI record exit with code {}".format(Params.ffmpeg_pi.returncode))
            if Params.ffmpeg_pi.returncode != 0:
                print("PI recording stopped with error")
            else:
                print("PI exit, not an error?")
            _pi_stop()
        else:
            pass
    else:
        print("PI not recording")


def _pi_init():
    if __has_picamera:
        try:
            Params.pi_camera = picamera.PiCamera()
            Params.pi_camera.resolution = Params.pi_max_resolution
            Params.pi_camera.framerate = Params.pi_framerate
            Params.pi_camera.annotate_background = picamera.Color('black')
            print("Recording PI")
            _run_ffmpeg_pi()
            Params.pi_camera.start_recording(Params.ffmpeg_pi.stdin, format='h264', bitrate=Params.pi_bitrate)
            if Params.ffmpeg_pi._child_created:
                Params.is_recording_pi = True
        except Exception, ex:
            print("Unable to initialise picamera, ex={}".format(ex))
    else:
        print("No picamera module")


def _pi_stop():
    print "Stopping PI"
    try:
        Params.is_recording_pi = False
        if Params.pi_camera is not None:
            if Params.ffmpeg_pi is not None:
                try:
                    Params.ffmpeg_pi.terminate()
                except Exception:
                    pass
                Params.ffmpeg_pi = None
            try:
                print("Camera closed={} recording={}".format(Params.pi_camera.closed, Params.pi_camera.recording))
                Params.pi_camera.stop_recording()
            except Exception, ex:
                print("Exception on pi camera stop, ex={}".format(ex))
            try:
                print("Camera closed={} recording={}".format(Params.pi_camera.closed, Params.pi_camera.recording))
                Params.pi_camera.close()
            except Exception, ex:
                print("Exception on pi camera close, ex={}".format(ex))
            print("Camera closed={} recording={}".format(Params.pi_camera.closed, Params.pi_camera.recording))
            if Params.pi_out_std is not None:
                Params.pi_out_std.close()
            if Params.pi_out_err is not None:
                Params.pi_out_err.close()
    except Exception, ex:
        print("Error in pi_stop, ex={}".format(ex))
        print(traceback.print_exc())


def _usb_stop():
    print "Stopping USB"
    Params.is_recording_usb = False
    if Params.ffmpeg_usb is not None:
        try:
            Params.ffmpeg_usb.terminate()
        except Exception:
            pass
        Params.ffmpeg_usb = None
        if Params.usb_out_std is not None:
            Params.usb_out_std.close()
        if Params.usb_out_err is not None:
            Params.usb_out_err.close()


def unload():
    global initialised
    _pi_stop()
    _usb_stop()
    initialised = False


def init():
    global initialised
    if not os.path.exists(Params.recordings_root):
        os.makedirs(Params.recordings_root)
    if Params.is_pi_camera_on:
        _pi_init()
    if Params.is_usb_camera_on:
        _usb_init()
    initialised = True


def thread_run():
    try:
        if Params.is_pi_camera_on:
            if Params.is_recording_pi:
                _pi_record_loop()
            else:
                print("Starting PI camera, should have been on")
                _pi_init()
        if Params.is_usb_camera_on:
            if Params.is_recording_usb:
                _usb_record_loop()
            else:
                print("Starting USB camera, should have been on")
                _recover_usb()
                _usb_init()
    except Exception, ex:
        print "Error in recorder thread_run, ex={}".format(ex)
        print traceback.print_exc()


if __name__ == '__main__':
    _run_ffmpeg_usb()
    if Params.ffmpeg_usb._child_created:
        Params.is_recording_usb = True
        print("Recording started")
        #Params.ffmpeg_usb_out = NBSR(Params.ffmpeg_usb.stdout)
    else:
        print("Recording process not created")
    _pi_init()
    while True:
        _usb_record_loop()
        _pi_record_loop()
        time.sleep(2)
