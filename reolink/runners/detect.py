import asyncio
import logging
import logging.config
import sys
from datetime import datetime
from typing import List, Tuple
from reolink.common import AuthenticationError
from reolink.models import Channel, get_session, MotionDetection, Session
from reolink.camera_api import Api

logger = logging.getLogger('detect')
logging.config.fileConfig('logging.conf')


async def poll_channel(channel: Channel, api: Api, session: Session, force_store: bool = False):
    """
    Poll a channel for it's Motion Detection state. Conditionally stores the value with session_

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


    """
    try:
        md_detect = await api.get_motion_state(channel.id)
    except AuthenticationError as e:
        raise e
    last_detect = channel.last_state
    if last_detect is None or force_store is True:
        db_detect = MotionDetection(channel_id=channel.id, detected=md_detect, dt=datetime.now())
        session.add(db_detect)
        session.commit()
    elif last_detect != md_detect:
        db_detect = MotionDetection(channel_id=channel.id, detected=md_detect, dt=datetime.now())
        session.add(db_detect)
        session.commit()


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


async def poll_channels(session: Session, api: Api, channels: List[Channel], force_store: bool = False):
    try:
        await asyncio.gather(
                *[poll_channel(channel, api, session, force_store) for channel in channels]
                )
        session.commit()
    except AuthenticationError:
        session.rollback()
        raise e


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
    logger.info("Session Created")
    logger.info("Setup Channel")
    channels = setup_channels(db_session, channels)
    logger.info("Channels Created")
    logger.info("Channel Created")

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
