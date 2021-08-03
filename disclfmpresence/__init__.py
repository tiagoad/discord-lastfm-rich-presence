#!/usr/bin/env python3
import logging
import sys
import time
import os.path

import pypresence

from disclfmpresence import config, exceptions, lastfm

log = logging.getLogger(__name__)


def main() -> int:
    """
    Main function. Loads config from a file or argv, and starts the main loop.

    :return: Exit code (0 = OK, others = Failure)
    """
    try:
        config_fn = (len(sys.argv) >= 2 and sys.argv[1]) or './config.toml'
        if not os.path.isfile(config_fn):
            print(f"Usage: {sys.argv[0]} [config.toml]")
            return 3

        cfg = config.load_file(config_fn)
        setup_logging(cfg.log_level.name, cfg.log_format)
        loop(cfg)

    except exceptions.ScriptException as e:
        log.critical(f"Script exception ocurred. {e.err_code} - {e.err_str}", exc_info=e.parent_exc)
        return 1

    except KeyboardInterrupt:
        log.info("Terminating.")
        return 0

    except Exception as e:
        log.critical(f"Unexpected {type(e).__name__}: {str(e)}")
        return 2

    return 0


def setup_logging(level: str, fmt: str):
    """
    Sets up the logging system for the project.

    :param level: Desired log level name
    :param fmt: Desired format string
    """
    log_formatter = logging.Formatter(fmt)
    log_handler = logging.StreamHandler(sys.stderr)
    log_handler.setFormatter(log_formatter)
    logging.getLogger().addHandler(log_handler)
    logging.getLogger(__name__).setLevel(level)


def loop(cfg: config.Config):
    """
    Main loop. Throws exceptions on critical errors.

    :param cfg: Config object
    """
    playing = None

    discord = pypresence.Presence(cfg.discord_client_id)

    while True:
        log.debug("Checking last.fm")
        track = lastfm.get_last_playing(
            api_root=cfg.scrobble_endpoint,
            api_key=cfg.scrobble_api_key,
            user=cfg.scrobble_username,
            retry_backoff=cfg.rate_limit_backoff,
            playing_threshold=cfg.playing_threshold
        )

        if track is None:
            _update_presence(discord, state=None)

        else:
            artist = track['artist']['#text']
            title = track['name']
            album = track['album']['#text']

            now_playing = (title, artist, album)

            if album:
                presence = dict(
                    state=f'{artist} - {album}',
                    details=f'{title}'
                )
            else:
                presence = dict(
                    state=f'{artist}',
                    details=f'{title}'
                )

            presence['large_image'] = 'logo'
            presence['small_image'] = 'logo'

            _update_presence(discord, **presence)

            if now_playing != playing:
                log.info(f'Now playing: {presence["details"]} | {presence["state"]}')
            playing = now_playing

        log.debug("Sleeping...")
        time.sleep(cfg.interval)


def _update_presence(rpc: pypresence.Presence, *args, **kwargs) -> bool:
    """
    Tries to update Discord rich presence.
    If no state is given, closes RPC connection to Discord.

    :param rpc: RPC Presence() object
    :param args: Positional arguments to Presence.update
    :param kwargs: Keyword arguments to Presence.update
    :return: True if successful
    """

    if kwargs.get('state') is None:
        try:
            rpc.close()
        except Exception as e:
            log.debug("Discord RPC already closed", exc_info=e)
        return True

    try:
        log.debug("Updating.")
        rpc.update(*args, **kwargs)
        log.debug("Updated.")
        return True
    except Exception as e:
        log.debug(f"Update failed: {e}")
        if rpc.sock_writer:
            try:
                log.debug("Trying to close Discord RPC")
                rpc.close()
            except Exception as e:
                log.debug("Failed to close.", exc_info=e)

        try:
            log.debug("Trying to connect.")
            rpc.connect()
            log.info("Connected to Discord.")

            rpc.update(*args, **kwargs)
            log.debug("Updated")
            return True
        except Exception as e:
            log.debug("Retry failed.", exc_info=e)

    return False
