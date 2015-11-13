#!/usr/bin/env python

import os
import platform
import re
import shutil
import time
from datetime import timedelta
from subprocess import call, STDOUT, PIPE, Popen

from video_repr import Constants as Repr, DefaultRepresentations

tool_platform_subdir = "ix"

# for obtaining the duration of a video file
ffprobe_duration_regex = re.compile(
    r'.*Duration: (?P<hours>\d+?):(?P<minutes>\d+?):'
    r'(?P<seconds>\d+?).(?P<milliseconds>\d+?), start:.*'
)

# Added this because Ubuntu needs a different version of the convert.sh script
if platform.linux_distribution()[0] == "Ubuntu":
    tool_platform_subdir = "ubuntu"


def prepare_target_dir(file_path):
    if os.path.exists(file_path):
        os.remove(file_path)
        return

    # make sure the directory exists
    dir_name = os.path.dirname(os.path.realpath(file_path))
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)


def exec_command(command, log_file_path=None):
    # log to file or to /dev/null
    log_out = open(log_file_path, 'w') if log_file_path is not None else open(os.devnull, 'w')

    try:
        return call(command, shell=True, stdout=log_out, stderr=STDOUT)
    finally:
        log_out.close()


def encode_x264(file_src, file_target, bitrate, fps, width, height, audio_asfq, audio_bitrate, log=True):
    prepare_target_dir(file_target)

    # log to file or to /dev/null
    log_file = ("%s.log" % file_target) if log else None

    exec_command('./tools/%s/convert.sh "%s" %d %s %dx%d %d %d "%s"' % (
        tool_platform_subdir,
        file_src,
        bitrate,
        str(fps),
        width, height,
        audio_asfq,
        audio_bitrate,
        file_target
    ), log_file)

    # since convert.sh does not return a meaningful exit code,
    # we check the result file after a short wait
    time.sleep(0.2)

    return os.path.exists(file_target) and os.path.getsize(file_target) > 0


def encode_x264_repr(file_src, file_target, video_repr, log=True):
    return encode_x264(file_src,
                       file_target,
                       video_repr.bandwidth / Repr.VIDEO_BIT_RATE_DIV,
                       Repr.VIDEO_FPS,
                       video_repr.width,
                       video_repr.height,
                       Repr.AUDIO_SAMPLE_FREQUENCY,
                       Repr.AUDIO_BITRATE,
                       log)


def encode_mp42ts(file_src, file_target, log=True):
    prepare_target_dir(file_target)

    # log to file or to /dev/null
    log_file = ("%s.log" % file_target) if log else None

    exit_code = exec_command('/usr/local/bin/mp42ts "%s" "%s"' % (file_src, file_target), log_file)

    # check both the exit code and the file after a short wait
    time.sleep(0.2)

    return exit_code == 0 and os.path.exists(file_target) and os.path.getsize(file_target) > 0


def gen_thumbnail(file_src, file_target, log=True):
    prepare_target_dir(file_target)

    # log to file or to /dev/null
    log_file = ("%s.log" % file_target) if log else None

    exit_code = exec_command('/usr/local/bin/ffmpeg -i "%s" -vf  "thumbnail" -frames:v 1 "%s"' %
                             (file_src, file_target), log_file)

    # check both the exit code and the file after a short wait
    time.sleep(0.2)

    return exit_code == 0 and os.path.exists(file_target) and os.path.getsize(file_target) > 0


def get_duration_millis(file_name):
    result = Popen(["ffprobe", file_name], stdout=PIPE, stderr=STDOUT)
    lines = [x for x in result.stdout.readlines() if "Duration:" in x]
    if len(lines) == 0:
        return 0

    duration_parts = ffprobe_duration_regex.match(lines[0])
    if not duration_parts:
        return 0

    d = duration_parts.groupdict()
    d['milliseconds'] = int(str(d['milliseconds']).ljust(3, '0'))
    d['seconds'] = int(d['seconds'])
    d['minutes'] = int(d['minutes'])
    d['hours'] = int(d['hours'])

    duration = timedelta(hours=d['hours'], minutes=d['minutes'], seconds=d['seconds'], milliseconds=d['milliseconds'])
    return int(duration.total_seconds() * 1000)


if __name__ == "__main__":
    # test run

    if os.path.exists('test_videos/output'):
        shutil.rmtree('test_videos/output')

    os.makedirs('test_videos/output/ORIGINAL')
    os.makedirs('test_videos/output/HIGH')
    os.makedirs('test_videos/output/MEDIUM')
    os.makedirs('test_videos/output/LOW')

    encode_x264_repr('test_videos/test_video.mp4',
                     'test_videos/output/LOW/test_video.mp4',
                     DefaultRepresentations.LOW)

    encode_x264_repr('test_videos/test_video.mp4',
                     'test_videos/output/MEDIUM/test_video.mp4',
                     DefaultRepresentations.MEDIUM)

    encode_x264_repr('test_videos/test_video.mp4',
                     'test_videos/output/HIGH/test_video.mp4',
                     DefaultRepresentations.HIGH)

    encode_mp42ts('test_videos/test_video.mp4',
                  'test_videos/output/ORIGINAL/test_video.ts')

    encode_mp42ts('test_videos/output/LOW/test_video.mp4',
                  'test_videos/output/LOW/test_video.ts')

    encode_mp42ts('test_videos/output/MEDIUM/test_video.mp4',
                  'test_videos/output/MEDIUM/test_video.ts')

    encode_mp42ts('test_videos/output/HIGH/test_video.mp4',
                  'test_videos/output/HIGH/test_video.ts')

    # gen_thumbnail('test_videos/test_video.mp4', 'test_videos/output/thumbnail.jpeg')

    # print get_duration_millis('test_videos/test_video.mp4')