from pydantic import BaseSettings, SecretStr


class ReolinkApiSettings(BaseSettings):
    # Reolink API URL
    class Config:
        env_prefix = 'REOLINK_'

    api_url: str
    username: str
    password: SecretStr
