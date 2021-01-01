import asyncio
import logging
import logging.config
import sys
from datetime import datetime
from typing import List, Tuple

from reolink.camera_api import Api
from reolink.common import AuthenticationError
from reolink.models import Channel, get_session, Session
from reolink.utils import dt_string

logger = logging.getLogger('detect')
logging.config.fileConfig('logging.conf')


def get_stream(api: Api, channel: int, start_time: datetime, port: int = 1935):
    """
    host/flv?port=1935&app=bcs&stream=playback.bcs&channel=0&type=1&start=20201229045959&seek=1&token

    start must correspond with a file that exists on NVR
    These

    Parameters
    ----------
    api
    seek_time
    start_time
    host
    token
    channel
    port

    Returns
    -------

    """

    url = f"http://{host}/flv?port={port}&app=bcs&stream=playback.bcs&channel=0&type=1&start={dt_string(start_time)}" \
          f"&seek={seek_time}&token={token}"


