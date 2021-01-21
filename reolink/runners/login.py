import asyncio
import argparse
import dotenv
import os
from reolink.runners.detect import setup_api


def get_token(host: str, username=None, password=None):
    """

    Parameters
    ----------
    host : str
    username : str
    password : str
    """
    if any([username is None, password is None]):
        dotenv.load_dotenv()

    if username is None:
        username = os.getenv("REO_USERNAME")
    if password is None:
        password = os.getenv("REO_PASSWORD")

    if not all([username, password]):
        raise Exception("Credentials Not Found")

    api = asyncio.run(setup_api(host, username, password))
    return api.token


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Print a token to stdout")
    parser.add_argument("host", help="IP Address of NVR")
    parser.add_argument("--username", help="Optional. Otherwise REO_USERNAME will be read from .env file")
    parser.add_argument("--password", help="Optional. Otherwise REO_PASSWORD will be read from .env file")
    args = parser.parse_args()
    token = get_token(args.host, args.username, args.password)
    print(token)

