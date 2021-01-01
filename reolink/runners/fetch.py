import asyncio
import logging.config
from datetime import datetime
from typing import Optional, cast, List
from urllib.parse import urlparse, urlencode

from dateutil.relativedelta import relativedelta

from reolink.camera_api import Api, STREAM_TYPES
from reolink.utils import SearchResponse, SearchResultFile, dt_string

logger = logging.getLogger('fetch')
logging.config.fileConfig('logging.conf')


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

    recordings = asyncio.run(api.query_recordings(window_start, window_end, channel=channel, stream=stream))

    if not recordings:
        raise Exception(f"No Recordings Match Found for {start_time}")

    responses = cast(List[SearchResponse], recordings)
    rec_files = [file for rfiles in [r.files for r in responses] for file in rfiles]  # Flatten

    matched_file = next((f for f in rec_files if f.StartTime.dt <= start_time < f.EndTime.dt), None)

    if not matched_file:
        raise Exception(f"No Recordings Match Found for {start_time}")

    seek_time = int(round((start_time - matched_file.StartTime.dt).total_seconds(), 0))
    matched_file_start_dt_str = dt_string(matched_file.StartTime.dt)

    params = {
        "port": port,
        "app": "bcs",
        "stream": "playback.bcs",
        "channel": channel if channel else api.channel,
        "type": 1,
        "start": matched_file_start_dt_str,
        "seek": seek_time,
        "token": api.token
        }

    url_params = urlencode(params)

    url_stream = f"http://{api.host}/flv?{url_params}"
    logger.info(f"Got URL : {url_stream}")













