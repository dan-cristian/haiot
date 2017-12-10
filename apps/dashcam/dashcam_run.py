try:
    import picamera
    __has_picamera = True
except Exception, ex:
    __has_picamera = False

import subprocess
import time
import datetime as dt
import re

__author__ = 'Dan Cristian<dan.cristian@gmail.com>'


_ffmpeg_pi = None
_ffmpeg_usb = None
_segment_duration = 3600  # in seconds

def _get_win_cams():
    pass


def _run_ffmpeg_pi(out_filename):
    global _ffmpeg_pi, _segment_duration
    if _ffmpeg_pi is None:
        _ffmpeg_pi = subprocess.Popen([
            'ffmpeg', '-y', '-r', '8', '-i', '-',
            '-vcodec', 'copy',
            '-f', 'segment', '-segment_time', _segment_duration, '-segment_format', 'mp4', '-reset_timestamps', '1',
            '-force_key_frames', '"expr:gte(t,n_forced*10)"',
            '-frag_duration', '1000',
            '-an', out_filename,
        ], stdin=subprocess.PIPE)


def _run_ffmpeg_usb_win(out_filename, camera_dev_name, resolution, no_sound=True):
    global _ffmpeg_usb, _segment_duration
    if no_sound:
        sound_param = "-an"
    else:
        sound_param = ""
    if _ffmpeg_usb is None:
        _ffmpeg_usb = subprocess.Popen([
            'ffmpeg', '-y', '-f', 'dshow', '-i', 'video=%s' % camera_dev_name,
            sound_param,
            '-c:v', 'libx264', '-b:v', '3000k',
            '-frag_duration', '1000', '-r', '8',
            #'-t', '00:00:05',
            '-f', 'segment', '-segment_time', _segment_duration, '-segment_format', 'mp4', '-reset_timestamps', '1',
            '-vf', 'drawtext=fontfile=/Windows/Fonts/arial.ttf: text=\'%{localtime\:%c}\': fontcolor=white@0.8: fontsize=32: x=10: y=10',
            #'-segment_wrap', '7',
            #"%03d.ts"
            out_filename
        ], stdin=subprocess.PIPE)
    else:
        # check if done
        pass


def _run_ffmpeg_usb(out_filename, camera_dev_name, resolution, no_sound=True):
    global _ffmpeg_usb
    if no_sound:
        sound_param = "-an"
    else:
        sound_param = ""
    if _ffmpeg_usb is None:
        _ffmpeg_usb = subprocess.Popen([
            'ffmpeg', '-y', '-r', '8',
            '-i', camera_dev_name,
            '-f', 'video4linux2',
            '-vf', '"drawtext=text=\'%{localtime\:%c}\': fontcolor=white@0.8: fontsize=32: x=10: y=10"',
            '-s', resolution, sound_param, "-c:v", "h264_omx", "-b:v", "3000k",
            '-frag_duration', '1000',
            out_filename,
        ])
            #, stdin=subprocess.PIPE)


def usb_record_loop():
    global _ffmpeg_usb
    i = 1
    while True:
        _run_ffmpeg_usb_win("capture%03d.mp4", "Integrated Camera", "640x480", no_sound=True)
        _ffmpeg_usb.wait()
        if _ffmpeg_usb.returncode is not None:
            _ffmpeg_usb.poll()
            pass


def pi_record_loop():
    global _ffmpeg_pi
    out_filename = 'capturepi%03d.mp4'
    camera = picamera.PiCamera()
    camera.resolution = (1296, 972)
    camera.framerate = 8
    camera.annotate_background = picamera.Color('black')
    print "Recording"
    _run_ffmpeg_pi(out_filename)
    camera.start_recording(_ffmpeg_pi.stdin, format='h264', bitrate=2000000)
    start = dt.datetime.now()
    while (dt.datetime.now() - start).seconds < 30:
        camera.annotate_text = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        camera.wait_recording(0.3)
    camera.stop_recording()
    camera.close()


def thread_run():
    #usb_record_loop()
    pi_record_loop()


if __name__ == '__main__':
    thread_run()
