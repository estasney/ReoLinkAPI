import asyncio
import logging.config
import math
import os
import shutil
import subprocess
from collections import namedtuple
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlencode

from dateutil.relativedelta import relativedelta

from reolink.camera_api import STREAM_TYPES, Api
from reolink.models import MotionRange
from reolink.utils import SearchResponse, dt_string

logger = logging.getLogger(__name__)

FetchTask = namedtuple("FetchTask", "filename, seek, duration")


def query_window(
    api: Api,
    start_time: datetime,
    stream: STREAM_TYPES,
    channel: int | None = None,
    window_hours: int = 4,
) -> list[SearchResponse] | None:
    """
    Run a query with window

    Parameters
    ----------
    api
    start_time
    stream
    channel : int, optional
        Channel to search. If `None` defaults to `api.channel`
    window_hours : int
        Number of hours to search before and after start_time

    Returns
    -------

    """
    window_start = start_time - relativedelta(hours=window_hours)
    window_end = start_time + relativedelta(hours=window_hours)
    # Future dates will cause error
    # It also seems to throw an error when querying currently recording
    window_end = min((datetime.now() - relativedelta(hours=1)), window_end)
    recordings = asyncio.run(
        api.query_recordings(
            window_start,
            window_end,
            channel=channel if channel else api.channel,
            stream=stream,
        )
    )
    return recordings


def build_fetch_tasks(
    api: Api,
    start_time: datetime,
    duration_secs: int,
    stream: STREAM_TYPES,
    pad_secs: int = 5,
    channel: int | None = None,
    **window_kwargs,
) -> list[FetchTask]:
    """
    Get the filename(s) and seektimes that matches a start_time and duration

    Parameters
    ----------
    api
    channel
    start_time
    duration_secs
    stream
    pad_secs
    window_kwargs
        Passed to `query_window`

    Returns
    -------

    """

    recordings = query_window(api, start_time, stream, channel, **window_kwargs)
    if not recordings:
        msg = f"No Recordings Match Found for {start_time}"
        raise Exception(msg)

    rec_files = [
        file for rfiles in [r.files for r in recordings] for file in rfiles
    ]  # Flatten
    rec_files = sorted(rec_files, key=lambda x: x.StartTime.dt)

    pad_start_time: datetime = start_time - relativedelta(seconds=pad_secs)
    end_time = pad_start_time + relativedelta(seconds=duration_secs)

    def dt_range(x, y):
        return range(int(x.timestamp()), int(y.timestamp()))

    target_range = dt_range(pad_start_time, end_time)

    timestamps = {}
    for f in rec_files:
        ts_range = dt_range(f.StartTime.dt, f.EndTime.dt)
        timestamps[ts_range] = f

    fully_covered = next((f for f in timestamps if target_range in f), None)

    if fully_covered:
        file = timestamps[fully_covered]
        filename = dt_string(file.PlaybackTime.dt)
        seek = target_range.start - fully_covered.start
        duration = duration_secs
        return [FetchTask(filename, seek, duration)]

    tasks = []
    cursor = target_range.start
    for file_ts_range, file in timestamps.items():
        # Seconds that can contribute to requested

        if cursor in file_ts_range:
            cursor_start_abs = cursor
            cursor_start_rel = cursor_start_abs - file_ts_range.start
            cursor_end_rel = min(
                [
                    (file_ts_range.stop - 1 - file_ts_range.start),
                    (target_range.stop - 1 - file_ts_range.start),
                ]
            )

            filename = dt_string(file.PlaybackTime.dt)

            tasks.append(
                FetchTask(
                    filename, cursor_start_rel, (cursor_end_rel - cursor_start_rel)
                )
            )
            cursor += cursor_end_rel + 1
            if cursor >= target_range.stop:
                return tasks

    return tasks


def save_stream_recording(
    api: Api,
    start_time: datetime,
    duration_secs: int,
    fp: str,
    padding_secs: int = 5,
    port: int = 1935,
    channel: int | None = None,
    stream: STREAM_TYPES = "sub",
):
    """
    Saves a previously recorded stream with FFMpeg

    Parameters
    ----------
    api
    start_time
    duration_secs
    fp : str
        Path to save to
    padding_secs : int
        Number of seconds to prepend to recording
    port : int, default 1935
    channel : int, optional
    stream

    Returns
    -------
    """

    tasks = build_fetch_tasks(
        api, start_time, duration_secs, stream, padding_secs, channel
    )

    logger.info("Writing %d Video Files", len(tasks))

    # store in tempdir
    merge_dir = TemporaryDirectory()
    merge_fp = merge_dir.name

    logging.debug("Tmp Directory : %s", merge_fp)

    for i, (filename, seek_time, duration) in enumerate(tasks):
        params = {
            "port": port,
            "app": "bcs",
            "stream": "playback.bcs",
            "channel": channel if channel else api.channel,
            "type": 1,
            "start": filename,
            "seek": seek_time,
            "token": api.token,
        }

        url_params = urlencode(params)
        url_stream = f"http://{api.host}/flv?{url_params}"
        file_name = f"{i}.mp4"
        full_path = os.path.join(merge_fp, file_name)

        logger.info("Getting URL %s", url_stream)
        logger.debug("Duration : %d", duration)

        with subprocess.Popen(
            ["ffmpeg", "-t", str(duration), "-i", url_stream, full_path],
            stdout=subprocess.PIPE,
            stdin=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
        ) as p:
            try:
                result, _ = p.communicate(timeout=duration + 15)
            except subprocess.TimeoutExpired:
                print("Killing Process")
                p.kill()
                result, errs = p.communicate()
                print(result.decode().strip())
                print(errs.decode().strip())

        print(result.decode().strip())

    # rejoin videos if + 1
    if len(tasks) == 1:
        shutil.move(os.path.join(merge_fp, "0.mp4"), fp)
        print(f"Saving to {fp}")
        merge_dir.cleanup()
        return

    vidlist_fp = os.path.join(merge_fp, "vidlist.txt")
    with open(vidlist_fp, "w") as vfp:
        for i in range(len(tasks)):
            vfp.write(f"file './{i}.mp4'")
            vfp.write("\n")

    print("Rejoining Videos")
    with subprocess.Popen(
        ["ffmpeg", "-f", "concat", "-safe", "0", "-i", vidlist_fp, "-c", "copy", fp],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.PIPE,
    ) as p:
        result, _ = p.communicate()

    print(result.decode().strip())

    merge_dir.cleanup()


def save_snapshot(api: Api, channel: int, folder: str, retries: int = 3):
    """
    Parameters
    ----------
    api: Api
    channel : int
    folder : str
    retries : int
        Max number of retries if image is truncated
    Returns
    -------

    """

    from datetime import datetime
    from io import BytesIO
    from typing import cast

    from PIL import Image
    from PIL.JpegImagePlugin import JpegImageFile

    current_try = 0
    while current_try < retries:
        img_bytes = asyncio.run(api.get_snapshot(channel))
        img_bytes = BytesIO(img_bytes)
        img = cast(JpegImageFile, Image.open(img_bytes))
        img_name = f"{datetime.now().timestamp():.0f}.jpg"
        img_path = os.path.join(folder, img_name)
        try:
            img.save(img_path, quality=90)
            logger.info(
                f"[Attempt {current_try}] Saved Channel {channel} Snapshot to {img_name}"
            )
        except OSError:
            logger.info(
                f"[Attempt {current_try}] Saving Channel {channel} Snapshot Failed."
            )
            current_try += 1
        else:
            return


def save_motion_recordings(
    api: Api,
    motions: list[MotionRange],
    output_dir: str,
    channel_folders: bool = True,
    port: int = 1935,
    pad_secs: int = 15,
    stream: STREAM_TYPES = "sub",
) -> None:
    """
    Fetch and Save Recording for MotionRange

    Parameters
    ----------
    api
    motions : List[MotionRange]
    port
    pad_secs : int
    output_dir
    channel_folders: bool
        If True, each channel is saved to a channel specific folder within output_dit
    stream

    Returns
    -------
    """
    output_dir = Path(output_dir)

    # Setup output
    channels_passed = {(motion.channel_id, motion.channel.name) for motion in motions}
    if channel_folders:
        channel2folder = {
            chn_id: (output_dir / chn_name) for chn_id, chn_name in channels_passed
        }
        for folder in channel2folder.values():
            folder.mkdir(exist_ok=True, parents=True)
    else:
        channel2folder = {chn_id: output_dir for chn_id, _ in channels_passed}

    def name_recording(m: MotionRange):
        return f"{m.channel.name}_{dt_string(m.range.lower)}.mp4"

    for motion in motions:
        start_time = motion.range.lower - relativedelta(seconds=pad_secs)
        duration = max(
            math.floor((motion.range.upper - motion.range.lower).total_seconds())
            + pad_secs,
            15,
        )
        save_folder = channel2folder[motion.channel_id]
        save_filename = name_recording(motion)
        save_location = Path(save_folder) / save_filename
        logging.info("Fetching %s", save_filename)
        save_stream_recording(
            api=api,
            start_time=start_time,
            duration_secs=duration,
            fp=str(save_location),
            port=port,
            channel=motion.channel_id,
            stream=stream,
        )
