from reolink.camera_api import Api
from reolink.runners.fetch import get_stream
from datetime import datetime
from dateutil.relativedelta import relativedelta
import keyring
import asyncio
import subprocess


def test_fetch(offset_hours):
    api = Api("10.1.0.120", "dev", keyring.get_password("REOLINK", "dev"), stream='sub')
    asyncio.run(api.login())
    s = datetime.now() - relativedelta(hours=offset_hours)
    url = get_stream(api, s, stream='sub')

    print(f"Getting Playback at {s.strftime('%m/%d %I:%M:%S %p')}")

    with subprocess.Popen(['ffplay', url], stdout=subprocess.PIPE, stdin=subprocess.PIPE, shell=False) as p:
        result, _ = p.communicate()
    print(result.decode().strip())
