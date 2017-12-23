try:
    import picamera
    __has_picamera = True
except Exception, ex:
    __has_picamera = False
import subprocess
import time
import os
import datetime as dt
from common import Constant

__author__ = 'Dan Cristian<dan.cristian@gmail.com>'


class Params:
    ffmpeg_pi = None
    ffmpeg_usb = None
    segment_duration = '3600'  # in seconds
    is_recording_pi = False
    is_recording_usb = False
    recordings_root = '/home/haiot/recordings/'
    pi_out_filename = recordings_root + 'pi_%Y-%m-%d_%H-%M-%S.mp4'
    usb_out_filename = recordings_root + 'usb_%Y-%m-%d_%H-%M-%S.mp4'
    usb_camera_keywords = 'HD Webcam C525'
    usb_camera_dev_name = '/dev/video0'
    usb_record_hw_id = 0
    usb_max_resolution = '1280x720'
    pi_max_resolution = (1296, 972)
    win_camera_dev_name = "Integrated Camera"
    pi_thread = None
    usb_thread = None
    pi_framerate = '8'
    usb_framerate = '8'
    pi_camera = None
    pi_bitrate = '2000000'


def _get_win_cams():
    pass


def _get_usb_params():
    rec = subprocess.check_output(['arecord', '-l']).split('\n')
    for line in rec:
        if len(line) > 1:
            atoms = line.split(',')
            if len(atoms) > 1:
                if Params.usb_camera_keywords in atoms[0]:
                    Params.usb_record_hw_id = atoms[1].split(':')[0].split(' device ')[1]


def _run_ffmpeg_pi():
    print "Recording on {}".format(Params.pi_out_filename)
    if Params.ffmpeg_pi is None:
        Params.ffmpeg_pi = subprocess.Popen([
            'ffmpeg', '-y', '-r', Params.pi_framerate, '-i', '-', '-vcodec', 'copy',
            '-f', 'segment', '-segment_time', Params.segment_duration, '-segment_format', 'mp4',
            '-reset_timestamps', '1', '-force_key_frames', '"expr:gte(t,n_forced*10)"',
            '-frag_duration', '1000', '-strftime', '1',
            '-an', Params.pi_out_filename], stdin=subprocess.PIPE)


def _run_ffmpeg_usb_win(no_sound=True):
    if no_sound:
        sound_param = "-an"
    else:
        sound_param = ""
    if Params.ffmpeg_usb is None:
        Params.ffmpeg_usb = subprocess.Popen([
            'ffmpeg', '-y', '-f', 'dshow', '-i', 'video={}'.format(Params.win_camera_dev_name),
            sound_param, '-c:v', 'libx264', '-b:v', '3000k', '-r', Params.usb_framerate,
            '-f', 'segment', '-segment_time', Params.segment_duration, '-segment_format', 'mp4',
            '-reset_timestamps', '1',
            '-force_key_frames', 'expr:gte(t,n_forced*10)',
            #'-vf', '"drawtext=fontfile=/Windows/Fonts/arial.ttf: text=\'%{localtime\:%c}\': fontcolor=white@0.8: fontsize=32: x=10: y=10"',
            '-s', '800x600', '-frag_duration', '1000',
            '-strftime', '1',
            Params.usb_out_filename])
        #, stdin=subprocess.PIPE)
        print Params.ffmpeg_usb.returncode


def _run_ffmpeg_usb(no_sound=True):
    if no_sound:
        sound_param = "-an"
    else:
        sound_param = ""
    if Params.ffmpeg_usb is None:
        Params.ffmpeg_usb = subprocess.Popen([
            'ffmpeg', '-y',
            '-f', 'alsa', '-thread_queue_size', '16384', '-ac', '1', '-i', 'hw:'+str(Params.usb_record_hw_id),
            '-r', Params.usb_framerate, '-f', 'video4linux2', '-i', Params.usb_camera_dev_name,
            '-thread_queue_size', '16384', '-reset_timestamps', '1', '-force_key_frames', '"expr:gte(t,n_forced*10)"',
            '-vf', '"drawtext=text=\'%{localtime\:%c}\': fontcolor=white@0.8: fontsize=32: x=10: y=10"',
            '-s', Params.usb_max_resolution, sound_param, "-c:v", "h264_omx", "-b:v", "3000k",
            '-frag_duration', '1000', '-strftime', '1',
            Params.usb_out_filename], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def _usb_init():
    print "Recording USB"
    if Constant.IS_OS_WINDOWS():
        _run_ffmpeg_usb_win(no_sound=True)
    else:
        _run_ffmpeg_usb(no_sound=True)
        print "Recording started"
    if Params.ffmpeg_usb._child_created:
        Params.is_recording_usb = True
    else:
        print "Recording process not created"


def usb_record_loop():
    if Params.is_recording_usb:
        Params.ffmpeg_usb.poll()
        if Params.ffmpeg_usb.returncode is not None:
            Params.is_recording_usb = False
            print "usb record exit with code {}".format(Params.ffmpeg_usb.returncode)
            if Params.ffmpeg_usb.returncode == 1:
                stdout, stderr = Params.ffmpeg_usb.communicate()
                print "Recording stopped with error"
                print stderr

    #time.sleep(10)
    #Params.ffmpeg_usb.terminate()


def _pi_init():
    if __has_picamera:
        Params.pi_camera = picamera.PiCamera()
        Params.pi_camera.resolution = Params.pi_max_resolution
        Params.pi_camera.framerate = Params.pi_framerate
        Params.pi_camera.annotate_background = picamera.Color('black')
        print "Recording PI"
        _run_ffmpeg_pi(Params.pi_out_filename)
        Params.pi_camera.start_recording(Params.ffmpeg_pi.stdin, format='h264', bitrate=Params.pi_bitrate)
        Params.is_recording_pi = True


def _pi_stop():
    Params.pi_camera.stop_recording()
    Params.pi_camera.close()
    Params.is_recording_pi = False


def pi_record_loop():
    if Params.is_recording_pi:
        Params.pi_camera.annotate_text = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        #Params.pi_camera.wait_recording(0.4)


def init():
    if not os.path.exists(Params.recordings_root):
        os.makedirs(Params.recordings_root)
    _get_usb_params()
    _pi_init()
    _usb_init()


def thread_run():
    pi_record_loop()
    usb_record_loop()


if __name__ == '__main__':
    usb_record_loop()
