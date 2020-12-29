import asyncio
import logging
import logging.config
import sys
from datetime import datetime
from typing import List, Tuple
from reolink.common import AuthenticationError
from reolink.models import Channel, get_session, Session
from reolink.camera_api import Api

logger = logging.getLogger('detect')
logging.config.fileConfig('logging.conf')


async def poll_channel(channel: Channel, api: Api, session: Session, force_store: bool = False):
    """
    Poll a channel for it's Motion Detection state. Passes value to channel to conditionally store

    Parameters
    ----------
    channel : Channel
        Channel model
    api : Api
        Reolink API
    session : Session
        DB Session
    force_store : bool
        If true, store the current motion detection state.
        If false, only stores if `current_state != channel.last_state`

    Returns
    -------

    bool, if True, state has changed and session should commit

    """
    try:
        md_detect = await api.get_motion_state(channel.id)
    except AuthenticationError as auth_error:
        raise auth_error

    state_changed = channel.handle_detection(md_detect, session, force_new=force_store)
    return state_changed


def setup_channels(session: Session, channels: List[Tuple[int, str]]):
    db_channels = []
    for channel_number, channel_name in channels:
        db_channel = session.query(Channel).get(channel_number)
        if not db_channel:
            db_channel = Channel(id=channel_number, name=channel_name)
            session.add(db_channel)
            session.commit()
        db_channels.append(db_channel)
    return db_channels


async def setup_api(host: str, username: str, password: str) -> Api:
    api = Api(host, username, password, channel=0)
    await api.login()
    logger.info("Logged In")
    return api


async def poll_channels(session: Session, api: Api, channels: List[Channel], force_store: bool = False,
                        wait_time: int = 1):
    try:
        state_changes = await asyncio.gather(
                *[poll_channel(channel, api, session, force_store) for channel in channels]
                )
        if any(state_changes):
            session.commit()
        await asyncio.sleep(wait_time)
    except AuthenticationError as auth_error:
        session.rollback()
        raise auth_error


def run_detect(host: str, username: str, password: str, db_uri: str, channels: List[Tuple[int, str]]):
    """

    Parameters
    ----------
    host : str
    username : str
    password : str
    db_uri : str
        Connection to db
    channels : List[Tuple[int, str]]
        List of tuples of form: `(channel_number, channel_name)`

    """
    api = asyncio.run(setup_api(host, username, password))
    db_session = get_session(db_uri)
    channels = setup_channels(db_session, channels)
    logger.info("Channel Setup Complete")

    asyncio.run(poll_channels(db_session, api, channels, force_store=True))

    while True:
        try:
            asyncio.run(poll_channels(db_session, api, channels))
        except AuthenticationError:
            logger.warning("Re-Authenticating")
            api = asyncio.run(setup_api(host, username, password))
        except Exception as e:
            logger.exception(f"Got Exception: {str(e)}")
            sys.exit(1)
