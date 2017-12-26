import subprocess
from stat import S_ISREG, ST_CTIME, ST_MODE, ST_MTIME
import os, sys, time, datetime
import shutil


class P():
    server = 'haiot@192.168.0.18'
    port = '222'
    dest_folder = '/media/usb/dashcam/'
    include_ext = '.mp4'
    root_folder = None
    move_folder = None
    exclude_time_delta = 120 # exclude files modified in the last x seconds
    folder_dict = set()


def _upload_file(file_path, file_date):
    fd = datetime.datetime.fromtimestamp(file_date)
    subfolder = str(fd.year) + '-' + str(fd.month) + '-' + str(fd.day) + '/'
    if subfolder not in P.folder_dict:
        #ssh -T -p 222 -c arcfour -o Compression=no $SSH_SERVER "mkdir -p $dest_parent"
        res = subprocess.check_output(['ssh -T -p ' + P.port + ' -c arcfour -o Compression=no ' +
                                       P.server + ' "mkdir -p "' + P.dest_folder + subfolder], shell=True)
        print('Created folder {}, res=[{}]'.format(subfolder, res))
        P.folder_dict.add(subfolder)
    # rsync -avrPe 'ssh -p 222 -T -c arcfour -o Compression=no -x ' $src haiot@$HOST_DEST:/media/usb/$dest
    res = subprocess.check_output(['rsync -avrPe "ssh -p ' + P.port + ' -T -c arcfour -o Compression=no -x" ' +
                                   file_path + ' ' + P.server + ':' + P.dest_folder + subfolder], shell=True)
    print('Uploaded file {}, res=[{}]'.format(file_path, res))



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
        if P.include_ext in path:
            # print time.ctime(cdate), path
            delta_sec = (now - cdate)
            if delta_sec > exclude_delta:
                result.append([path, cdate])
                print('Added {}'.format(path))
    return result


def _upload():
    files = _file_list(P.root_folder, exclude_delta=P.exclude_time_delta)
    for file in files:
        try:
            _upload_file(file_path=file[0], file_date=file[1])
            shutil.move(file[0], P.move_folder)
        except Exception, ex:
            print('Exception uploading file {}, ex={}'.format(file[0], ex))


def thread_run():
    _upload


if __name__ == '__main__':
    P.root_folder = '/home/haiot/recordings/'
    P.move_folder = '/home/haiot/recordings/uploaded/'
    _upload()
