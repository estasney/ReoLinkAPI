"""
Reolink Camera API

Extended from https://github.com/fwestenberg/reolink

"""

import json
import logging
from datetime import datetime, timedelta
from typing import Literal, TypedDict

import aiohttp
from dateutil.relativedelta import relativedelta

from reolink.common import AuthenticationError
from reolink.utils import SearchResponse

MANUFACTURER = "Reolink"
DEFAULT_STREAM = "main"
DEFAULT_PROTOCOL = "rtmp"

logger = logging.getLogger(__name__)

STREAM_TYPES = Literal["main", "sub"]


class DTOffset(TypedDict):
    years: int | None
    months: int | None
    days: int | None
    leapdays: int | None
    weeks: int | None
    hours: int | None
    minutes: int | None
    seconds: int | None
    microseconds: int | None


class Api:
    """Reolink API class."""

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        port: int = 80,
        channel: int = 0,
        timeout: int = 10,
        stream: STREAM_TYPES = DEFAULT_STREAM,
    ):
        """

        Parameters
        ----------
        host : str
            Url of Reolink NVR
        username : str
        password : str
        port : int, optional
            Defaults to 80
        channel : int, optional
            Defaults to 0
        timeout : int, optional
            Timeout, in seconds, defaults to 10
        stream
        """
        self.url = f"http://{host}:{port}/cgi-bin/api.cgi"
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.channel = channel
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.token = None
        self.lease_time = None
        self.stream = stream
        self.protocol = DEFAULT_PROTOCOL

    @property
    def session_active(self):
        """Return if the session is active."""
        if self.token is not None and self.lease_time > datetime.now():
            return True

        self.token = None
        self.lease_time = None
        return False

    def clear_token(self):
        """Initialize the token and lease time."""
        self.token = None
        self.lease_time = None

    async def get_motion_state(self, channel: int | None = None) -> bool:
        """
        Fetch the motion state

        Parameters
        ----------
        channel : int, optional
            Defaults to `self.channel`. Otherwise queries the channel passed

        Returns
        -------
        bool

        Raises
        -------
        AuthenticationError

        """
        body = [
            {
                "cmd": "GetMdState",
                "action": 0,
                "param": {"channel": self.channel if not channel else channel},
            }
        ]

        response = await self.send(body)

        try:
            json_data = json.loads(response)

            if json_data is None:
                logger.error(
                    f"Unable to get Motion detection state at IP {self.host}"
                )
                return False
            try:
                return json_data[0]["value"]["state"] == 1
            except KeyError:
                self.clear_token()
                raise AuthenticationError("Not Authenticated")
        except (TypeError, json.JSONDecodeError, KeyError):
            self.clear_token()
            return False

    async def get_snapshot(self, channel: int | None = None) -> bytes | None:
        """
        Get snapshot image

        Parameters
        ----------
        channel : int, optional
            Defaults to self.channel

        Returns
        -------
        bytes, if successful otherwise None

        """
        param = {"cmd": "Snap", "channel": self.channel if not channel else channel}
        response = await self.send(None, param)

        if response is None or response == b"" or b"error" in response:
            return None
        return response

    async def login(self) -> bool:
        """Login and store the session"""
        if self.session_active:
            return True

        logger.debug(
            f"Reolink camera with host {self.host}:{self.port} trying to login with user {self.username}"
        )
        body = [
            {
                "cmd": "Login",
                "action": 0,
                "param": {
                    "User": {"userName": self.username, "password": self.password}
                },
            }
        ]
        param = {"cmd": "Login", "token": "null"}

        response = await self.send(body, param)

        try:
            json_data = json.loads(response)
            logger.debug(f"Got response from {self.host}: {json_data}")
        except (TypeError, json.JSONDecodeError):
            logger.error("Error translating login response to json")
            return False

        if json_data is not None:
            try:
                if json_data[0]["code"] == 0:
                    self.token = json_data[0]["value"]["Token"]["name"]
                    lease_time = json_data[0]["value"]["Token"]["leaseTime"]
                    self.lease_time = datetime.now() + timedelta(seconds=lease_time)
                    return True
            except (KeyError, IndexError):
                logger.error("JSON structure from login response not recognized")
                return False

        logger.error(f"Failed to login at IP {self.host}. Connection error.")
        return False

    async def logout(self):
        """Logout from the API."""
        body = [{"cmd": "Logout", "action": 0, "param": {}}]
        param = {"cmd": "Logout"}

        await self.send(body, param)
        self.clear_token()

    async def send(self, body, param=None) -> bool | str | bytes:
        """Generic send method."""
        if body is None or (body[0]["cmd"] != "Login" and body[0]["cmd"] != "Logout"):
            if not await self.login():
                return False

        if not param:
            param = {}
        if self.token is not None:
            param["token"] = self.token

        try:
            if body is None:
                async with aiohttp.ClientSession(timeout=self.timeout) as session:
                    async with session.get(url=self.url, params=param) as response:
                        return await response.read()
            else:
                async with aiohttp.ClientSession(timeout=self.timeout) as session:
                    async with session.post(
                        url=self.url, json=body, params=param
                    ) as response:
                        json_data = await response.text()
                        return json_data
        except:  # pylint: disable=bare-except
            return False

    async def query_recordings(
        self,
        start_time: datetime,
        end_time: DTOffset | datetime,
        channel: int | None = None,
        stream: STREAM_TYPES | None = None,
    ) -> None | list[SearchResponse]:
        """
        Query Recordings

        Parameters
        ----------
        start_time : datetime
            Search for files after this datetime
        end_time : Union[DTOffset, datetime]
            Search for files before this datetime. Can either be datetime or valid `relativeoffset` params
        channel : int, optional
            If passed, searches this channel. Otherwise searches using `self.channel`
        stream : One of {'main', 'sub'}, optional
            If passed, must be one of STREAM_TYPES. Defaults to `self.stream`

        Returns
        -------

        """

        params = {
            "cmd": "Search",
            "rs": self.token,
            "user": self.username,
            "password": self.password,
        }

        if isinstance(end_time, dict):
            end_time = start_time + relativedelta(**end_time)

        body = [
            {
                "cmd": "Search",
                "action": 1,
                "param": {
                    "Search": {
                        "channel": channel if channel is not None else self.channel,
                        "onlyStatus": 0,
                        "streamType": stream if stream else self.stream,
                        "StartTime": {
                            "year": start_time.year,
                            "mon": start_time.month,
                            "day": start_time.day,
                            "hour": start_time.hour,
                            "min": start_time.minute,
                            "sec": start_time.second,
                        },
                        "EndTime": {
                            "year": end_time.year,
                            "mon": end_time.month,
                            "day": end_time.day,
                            "hour": end_time.hour,
                            "min": end_time.minute,
                            "sec": end_time.second,
                        },
                    }
                },
            }
        ]

        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.post(url=self.url, json=body, params=params) as response:
                resp_data = await response.text()

        try:
            json_data = json.loads(resp_data)
        except (TypeError, json.JSONDecodeError):
            logger.error("Error translating search response to json")
            return None

        return [SearchResponse.from_response(resp) for resp in json_data]
