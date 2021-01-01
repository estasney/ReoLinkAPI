from reolink.camera_api import Api
from reolink.runners.fetch import get_stream, save_stream
from datetime import datetime
from dateutil.relativedelta import relativedelta
import keyring
import asyncio
import subprocess


def test_fetch(offset_hours, padding_sec=5):
    api = Api("10.1.0.120", "dev", keyring.get_password("REOLINK", "dev"), stream='sub')
    asyncio.run(api.login())
    s = datetime.now() - relativedelta(hours=offset_hours)
    print(f"Getting Playback at {s.strftime('%m/%d %I:%M:%S %p')}")

    s = s - relativedelta(seconds=padding_sec)
    url, _ = get_stream(api, s, stream='sub')


    with subprocess.Popen(['ffplay', url], stdout=subprocess.PIPE, stdin=subprocess.PIPE, shell=False) as p:
        result, _ = p.communicate()
    print(result.decode().strip())

def test_offset_fetch(offset_hours, padding_sec=5):
    api = Api("10.1.0.120", "dev", keyring.get_password("REOLINK", "dev"), stream='sub')
    asyncio.run(api.login())
    s = datetime.now() - relativedelta(hours=offset_hours)
    s = datetime(year=s.year, month=s.month, day=s.day, hour=s.hour, minute=59, second=0)
    print(f"Getting Playback at {s.strftime('%m/%d %I:%M:%S %p')}")

    s = s - relativedelta(seconds=padding_sec)
    tasks = save_stream(api, s, stream='sub', fp='/home/eric/Downloads/testoffset.mp4', duration_secs=600)

    print(tasks)
