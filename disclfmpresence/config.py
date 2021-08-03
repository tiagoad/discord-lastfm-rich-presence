import enum
import re
import typing

import pydantic
import tomli

from .exceptions import ScriptException


class LogLevel(enum.Enum):
    DEBUG = 'debug'
    INFO = 'info'
    WARNING = 'warning'
    ERROR = 'error'
    CRITICAL = 'critical'


@pydantic.dataclasses.dataclass
class Config:
    """
    Script configuration
    """

    scrobble_api_key: str = pydantic.Field(
        title="Scrobble API key",
        description="Generate one at https://www.last.fm/api/account/create, "
                    "or see the existing ones at https://www.last.fm/api/accounts.")

    scrobble_username: str = pydantic.Field(
        title="Scrobble site username")

    scrobble_endpoint: str = pydantic.Field(
        title="Scrobble API endpoint",
        default="https://ws.audioscrobbler.com/2.0/")

    discord_client_id: str = pydantic.Field(
        title="Discord Client ID",
        description="Read https://qwertyquerty.github.io/pypresence/html/info/quickstart.html",
        default="872110819100463214")

    interval: int = pydantic.Field(
        title="Seconds between playing track checks",
        default=60, ge=1)

    rate_limit_backoff: int = pydantic.Field(
        title="Seconds before trying again in case of rate limiting",
        default=180, ge=1)

    playing_threshold: int = pydantic.Field(
        title="Seconds passed since play to consider user not playing anything",
        default=120, ge=0)

    log_level: LogLevel = LogLevel.INFO

    log_format: str = pydantic.Field(
        title="Python logging format",
        description="https://docs.python.org/3/library/logging.html#logrecord-attributes",
        default="%(asctime)s [%(levelname)s] [%(filename)s:%(lineno)d:%(name)s] %(message)s")


def load_file(filename) -> Config:
    """
    Load configuration from a file.

    :param filename: Filename to open
    :return: Config object
    """
    # read file
    try:
        with open(filename) as f:
            config_data = f.read()
    except Exception as e:
        raise ScriptException("CONFIG_LOAD_ERR", f"Error loading config file: {e}", parent_exc=e)

    # parse toml
    try:
        config_dict = tomli.loads(config_data)
    except Exception as e:
        raise ScriptException("CONFIG_PARSE_ERR", f"Error parsing config file: {e}")

    # load dataclass and validate (pydantic)
    try:
        cfg = Config(**config_dict)

        # cast - type checker needs a nudge
        return typing.cast(Config, cfg)

    except pydantic.ValidationError as e:
        raise ScriptException("CONFIG_INVALID", str(e))

    except TypeError as e:
        if m := re.match(r".*got an unexpected keyword argument '(.+)'", str(e)):
            raise ScriptException("CONFIG_INVALID", f'The configured key "{m.group(1)}" is not supported.')

        elif m := re.match(r".*missing \d+ required positional arguments?: (.*)", str(e)):
            keys = m.group(1).replace("'", '"')
            raise ScriptException("CONFIG_INVALID", f'Missing config key(s): {keys}.')

        else:
            raise ScriptException("CONFIG_LOAD_ERR", f"Config error: {e}", e)