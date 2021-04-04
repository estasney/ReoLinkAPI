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
def get_token(username, password, host, env_file):
    """
    Get token for Reolink API and echo stdout. Credentials can be passed as args, Environment Variables, or .env file.

    username - REO_USERNAME
    password - REO_PASSWORD
    host - REO_HOST
    """
    if env_file:
        dotenv.load_dotenv(env_file)
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
    print(api)
    try:
        run(api.login())
    except RuntimeWarning:
        pass
    print(api.token)


@cli.command()
@click.option('-c', '--channel', type=int)
@click.option('-f', '--folder', type=click.Path(file_okay=False, dir_okay=True))
@click.option('-u', '--username', default=None)
@click.option('-p', '--password', default=None)
@click.option('-h', "--host", default=None)
@click.option('-e', '--env-file', default=None)
def save_snapshot(channel, folder, username, password, host, env_file):
    """
    Retrieve a channel's snapshot and save to folder

    Parameters
    ----------
    channel : int
        Channel number
    folder : str
        Folder path
    username : Optional[str]
    password : Optional[str]
    host : Optional[str]
    env_file : Optional[str]

    Returns
    -------
    None

    Notes
    -----
    Credentials can be passed directly via stdin or with environment variables.

    If environment variables, they should be of form:
    ```
    username - REO_USERNAME
    password - REO_PASSWORD
    host - REO_HOST
    ```

    """
    from reolink.camera_api import Api
    from reolink.runners.fetch import save_snapshot as snapshot_saver
    from asyncio import run

    if env_file:
        dotenv.load_dotenv(env_file)
    else:
        dotenv.load_dotenv()

    username = username if username else os.getenv('REO_USERNAME')
    password = password if password else os.getenv('REO_PASSWORD')
    host = host if host else os.getenv('REO_HOST')

    if not all([username, password, host]):
        missing = [param_name for param, param_name in
                   zip([username, password, host], ['username', 'password', 'host']) if not param]
        raise Exception(f"Missing Parameters: {', '.join(missing)}")

    api = Api(host, username, password)
    run(api.login())
    snapshot_saver(api, channel, folder)
