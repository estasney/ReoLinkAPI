import asyncio
import logging.config
import math
import os
import subprocess
from datetime import datetime
from typing import Optional, cast, List, Tuple
from urllib.parse import urlparse, urlencode
from tempfile import TemporaryDirectory
from dateutil.relativedelta import relativedelta

from reolink.camera_api import Api, STREAM_TYPES
from reolink.utils import SearchResponse, SearchResultFile, dt_string

logger = logging.getLogger('fetch')


def get_stream(api: Api, start_time: datetime, port: int = 1935, channel: Optional[int] = None,
               stream: Optional[STREAM_TYPES] = None):
    """
    host/flv?port=1935&app=bcs&stream=playback.bcs&channel=0&type=1&start=20201229045959&seek=1&token

    start must correspond with a file that exists on NVR
    seek corresponds to seconds offset

    These

    Parameters
    ----------
    api : Api
        Api, required in order to query available recordings meeting a certain timeframe
    start_time : datetime
        The desired start_time
    port : int, defaults to 1935
        RTMP port
    channel : int, optional
        If passed get stream for this channel. Otherwise get API's channel
    stream : One of {'main', 'sub'}, optional
        If passed, must be one of STREAM_TYPES. Defaults to api.stream

    Returns
    -------

    """

    # Determine a window for querying files that meet specified start_time
    window_start = start_time - relativedelta(hours=4)
    window_end = start_time + relativedelta(hours=4)

    # Future dates will cause error
    # It also seems to throw an error when querying currently recording
    window_end = min((datetime.now() - relativedelta(hours=1)), window_end)

    matched_file_start_dt_str, seek_time = url_logic_start_time(api, channel, start_time, stream)

    params = {
        "port":    port,
        "app":     "bcs",
        "stream":  "playback.bcs",
        "channel": channel if channel else api.channel,
        "type":    1,
        "start":   matched_file_start_dt_str,
        "seek":    seek_time,
        "token":   api.token
        }

    url_params = urlencode(params)

    url_stream = f"http://{api.host}/flv?{url_params}"
    logger.info(f"Got URL : {url_stream}")

    return url_stream


def url_logic_start_time(api, channel, start_time, stream) -> Tuple[str, int]:
    """
    Get the filename and seektime that matches a start_time

    Parameters
    ----------
    api
    channel
    start_time
    stream

    Returns
    -------

    """
    # Determine a window for querying files that meet specified start_time
    recordings = query_window(api, channel, start_time, stream)
    if not recordings:
        raise Exception(f"No Recordings Match Found for {start_time}")
    responses = cast(List[SearchResponse], recordings)
    rec_files = [file for rfiles in [r.files for r in responses] for file in rfiles]  # Flatten
    matched_file = next((f for f in rec_files if start_time in f), None)
    if not matched_file:
        raise Exception(f"No Recordings Match Found for {start_time}")
    seek_time = math.floor((start_time - matched_file.StartTime.dt).total_seconds())
    matched_file_start_dt_str = dt_string(matched_file.PlaybackTime.dt)
    return matched_file_start_dt_str, seek_time


def query_window(api, channel, start_time, stream):
    """
    Run a query with window

    Parameters
    ----------
    api
    channel
    start_time
    stream

    Returns
    -------

    """
    window_start = start_time - relativedelta(hours=4)
    window_end = start_time + relativedelta(hours=4)
    # Future dates will cause error
    # It also seems to throw an error when querying currently recording
    window_end = min((datetime.now() - relativedelta(hours=1)), window_end)
    recordings = asyncio.run(api.query_recordings(window_start, window_end, channel=channel, stream=stream))
    return recordings


def url_logic_duration(api, channel, start_time, duration_secs, stream):
    """
    Get the filename(s) and seektimes that matches a start_time and duration

    Parameters
    ----------
    api
    channel
    start_time
    duration_secs
    stream

    Returns
    -------

    """

    recordings = query_window(api, channel, start_time, stream)
    if not recordings:
        raise Exception(f"No Recordings Match Found for {start_time}")
    responses = cast(List[SearchResponse], recordings)
    rec_files = [file for rfiles in [r.files for r in responses] for file in rfiles]  # Flatten
    rec_files.sort(key=lambda x: x.StartTime.dt)



def save_stream(api: Api, start_time: datetime, duration_secs: int, fp: str, padding_secs: int = 5, port: int = 1935,
                channel: Optional[int] = None,
                stream: Optional[STREAM_TYPES] = 'sub'):
    """
    Saves a stream with FFMpeg


    Parameters
    ----------
    api
    start_time
    duration_secs
    fp
    padding_secs : int
        Number of seconds
    port
    channel
    stream
    fp

    Returns
    -------
    """

    # We also need to handle cases where durations may cause files to be split
    _, rec_files = get_stream(api=api, start_time=start_time, stream=stream)

    # True start time adjusted for padding
    pad_start_time = start_time - relativedelta(seconds=padding_secs)
    end_time = start_time + relativedelta(seconds=duration_secs)

    rec_files = sorted(rec_files, key=lambda x: x.StartTime.dt)

    duration_timer = pad_start_time
    duration_remain = duration_secs

    tasks = []

    for file in rec_files:
        # Seconds that can conribute to requested
        if file.EndTime.dt < pad_start_time:
            continue
        if file.StartTime.dt > end_time:
            continue
        useable_seconds = math.floor((file.EndTime.dt - pad_start_time).total_seconds())
        if useable_seconds >= duration_remain:
            tasks.append((file, duration_timer, duration_remain))
            break
        else:
            tasks.append((file, duration_timer, useable_seconds))
            duration_timer += relativedelta(seconds=useable_seconds)
            duration_remain -= useable_seconds


    logger.info(f"Writing {len(tasks)} Video Files")

    # store in tempdir
    merge_dir = TemporaryDirectory()
    merge_fp = merge_dir.name

    for i, (file, dtimer, secs) in enumerate(tasks):
        seek_time = int(round((dtimer - file.StartTime.dt).total_seconds(), 0))
        stream_url_start_dt = dt_string(file.PlaybackTime.dt)
        params = {
            "port":    port,
            "app":     "bcs",
            "stream":  "playback.bcs",
            "channel": channel if channel else api.channel,
            "type":    1,
            "start":   stream_url_start_dt,
            "seek":    seek_time,
            "token":   api.token
            }

        url_params = urlencode(params)
        url_stream = f"http://{api.host}/flv?{url_params}"
        file_name = f"{i}.mp4"
        full_path = os.path.join(merge_fp, file_name)


        with subprocess.Popen(['ffmpeg', "-to", str(secs), "-i", url_stream, full_path],
                              stdout=subprocess.PIPE, stdin=subprocess.PIPE,
                              shell=False) as p:
            try:
                result, _ = p.communicate(timeout=secs + 30)
            except:
                p.terminate()
        print(result.decode().strip())

    # rejoin videos

    vidlist_fp = os.path.join(merge_fp, "vidlist.txt")
    with open(vidlist_fp, "w") as vfp:
        for i in range(len(tasks)):
            vfp.write(f"{i}.mp4")
            vfp.write("\n")

    with subprocess.Popen(['ffmpeg', '-f', 'concat', '-safe', '0', '-i', vidlist_fp, '-c', 'copy', fp],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False) as p:
        result, _ = p.communicate()

    print(result.decode().strip())

    merge_dir.cleanup()



