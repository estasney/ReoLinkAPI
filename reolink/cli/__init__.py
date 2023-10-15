import click


@click.group()
def cli():
    """CLI Commands for Reolink API"""
    pass


@cli.command()
@click.option('-e', '--env-file', default=None)
def get_token(env_file):
    """
    Get token for Reolink API and echo stdout. Credentials are provided via environment variables or env file.
    """
    from reolink.settings import ReolinkApiSettings
    from reolink.camera_api import Api
    from asyncio import run
    settings = ReolinkApiSettings(_env_file=env_file)
    api = Api(settings.api_url, settings.username, settings.password.get_secret_value())
    try:
        run(api.login())
    except RuntimeWarning:
        pass
    print(api.token)


@cli.command()
@click.option('-c', '--channel', type=int)
@click.option('-f', '--folder', type=click.Path(file_okay=False, dir_okay=True))
@click.option('-e', '--env-file', default=None)
def save_snapshot(channel, folder, env_file):
    """
    Retrieve a channel's snapshot and save to folder

    Parameters
    ----------
    channel : int
        Channel number
    folder : str
        Folder path
    env_file : Optional[str]

    Returns
    -------
    None

    Notes
    -----
    Credentials can be passed directly via stdin or with environment variables.

    If environment variables, they should be of form:
    ```
    ```

    """
    from reolink.camera_api import Api
    from reolink.runners.fetch import save_snapshot as snapshot_saver
    from asyncio import run
    from reolink.settings import ReolinkApiSettings

    settings = ReolinkApiSettings(_env_file=env_file)
    api = Api(settings.api_url, settings.username, settings.password.get_secret_value())
    run(api.login())
    snapshot_saver(api, channel, folder)
