import os
import click
import dotenv


@click.group()
def cli():
    """CLI Commands for Reolink API"""
    pass


@cli.command()
@click.option('-u', '--username', default=None)
@click.option('-p', '--password', default=None)
@click.option('-h', "--host", default=None)
@click.option('-e', '--env-file', default=None)
def get_token(username, password, host, env):
    """
    Get token for Reolink API and echo stdout. Credentials can be passed as args, Environment Variables, or .env file.

    username - REO_USERNAME
    password - REO_PASSWORD
    host - REO_HOST
    """
    if env:
        dotenv.load_dotenv(env)
    else:
        dotenv.load_dotenv()
    username = username if username else os.getenv('REO_USERNAME')
    password = password if password else os.getenv('REO_PASSWORD')
    host = host if host else os.getenv('REO_HOST')

    if not all([username, password, host]):
        missing = [param_name for param, param_name in
                   zip([username, password, host], ['username', 'password', 'host']) if not param]
        raise Exception(f"Missing Parameters: {', '.join(missing)}")

    from reolink.camera_api import Api
    from asyncio import run
    api = Api(host, username, password)
    run(api.login())
    print(api.token)
