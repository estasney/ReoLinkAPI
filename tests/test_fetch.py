from io import BytesIO

import PIL.Image
import pytest

from reolink.camera_api import Api


@pytest.fixture()
def settings():
    from reolink.settings import ReolinkApiSettings

    return ReolinkApiSettings(_env_file="../.env")


@pytest.mark.parametrize("channel", [0, 1, 2, 3])
@pytest.mark.asyncio
async def test_get_snapshot(channel, settings):
    """Interactive end-to-end test to get snapshots from camera"""
    api = Api(
        host=settings.api_url,
        username=settings.username,
        password=settings.password.get_secret_value(),
        stream="sub",
    )
    await api.login()
    snapshot_data = await api.get_snapshot(channel)
    assert snapshot_data is not None
    fp = BytesIO(snapshot_data)
    img = PIL.Image.open(fp)
    img.show()
