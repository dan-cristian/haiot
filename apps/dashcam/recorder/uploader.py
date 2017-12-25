import subprocess
from stat import S_ISREG, ST_CTIME, ST_MODE, ST_MTIME
import os, sys, time, datetime

_user = 'haiot'
_host = '192.168.0.18'
_port = '222'
_dest_folder = '/media/usb/dashcam/'
_include_ext = '.mp4'
_exclude_time_delta = 120 # exclude files modified in the last x seconds


def _upload_file(file_path):
    subfolder = ""
    # rsync -avrPe 'ssh -p 222 -T -c arcfour -o Compression=no -x ' $src haiot@$HOST_DEST:/media/usb/$dest
    res = subprocess.check_output(["rsync -avrPe 'ssh -p " + _port + " -T -c arcfour -o Compression=no -x '" +
                                   file_path + ' ' + _user + '@' + _host + ':' + _dest_folder + subfolder])
    print res



def _file_list(folder, exclude_delta):
    # https://stackoverflow.com/questions/168409/how-do-you-get-a-directory-listing-sorted-by-creation-date-in-python
    # get all entries in the directory w/ stats
    entries = (os.path.join(folder, fn) for fn in os.listdir(folder))
    entries = ((os.stat(path), path) for path in entries)

    # leave only regular files, insert creation date
    entries = ((stat[ST_MTIME], path) for stat, path in entries if S_ISREG(stat[ST_MODE]))
    # NOTE: on Windows `ST_CTIME` is a creation date
    #  but on Unix it could be something else
    # NOTE: use `ST_MTIME` to sort by a modification date

    result = []
    now = time.time()
    for cdate, path in sorted(entries, reverse=True):
        if _include_ext in path:
            # print time.ctime(cdate), path
            delta_sec = (now - cdate)
            if delta_sec > exclude_delta:
                result.append(path)
                print('Added {}'.format(path))
    return result


def upload(root_folder):
    files = _file_list(root_folder, exclude_delta=_exclude_time_delta)
    for file in files:
        _upload_file(file)



if __name__ == '__main__':
    upload('/home/haiot/recordings')
