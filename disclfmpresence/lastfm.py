import logging
import time

import requests

from disclfmpresence import exceptions


log = logging.getLogger(__name__)


def get_last_playing(api_root: str, api_key: str, user: str, retry_backoff: int, playing_threshold: int):
    """
    Get the last playing track

    :param api_root: Scrobbling API root
    :param api_key: Scrobbling API key
    :param user: Scrobbling user
    :param retry_backoff: Seconds to wait before retry
    :param playing_threshold:
    :return:
    """

    r = _scrobble_api(
        api_root=api_root,
        api_key=api_key,
        method='user.getRecentTracks',
        retry_backoff=retry_backoff,
        # 11 : Service Offline - This service is temporarily offline. Try again later.
        # 16 : There was a temporary error processing your request. Please try again
        # 29 : Rate limit exceeded - Your IP has made too many requests in a short period
        retry_errs=[11, 16, 29],
        params=dict(
            user=user,
            limit=1
        )
    )

    if len(tracks := r['recenttracks']['track']) > 0:
        track = tracks[0]

        if track.get('@attr', {}).get('nowplaying', False):
            # is now playing
            return track

        elif play_timestamp := track.get('date', {}).get('uts'):
            # already finished
            if time.time() - int(play_timestamp) <= playing_threshold:
                # ...within the threshold
                return track
            else:
                # ...too long ago
                return None

        else:
            # no nowplaying and no date - should never be reached
            log.warning("Track doesn't have nowplaying nor date: %s", track)
            return None

    else:
        return None


def _scrobble_api(api_root: str, api_key: str, method: str, retry_backoff: int, retry_errs: list[int], params=None):
    # add method and auth params
    params = (params or {}) | dict(
        method=method,
        api_key=api_key,
        format='json'
    )

    while True:
        try:
            r = requests.get(api_root, params=params)
        except Exception as e:
            log.warning(f"Couldn't retrieve data... Retrying in {retry_backoff}", exc_info=e)
            time.sleep(retry_backoff)
            continue

        try:
            data = r.json()
        except ValueError:
            data = dict()

        if err_code := data.get("error"):
            err_msg = data.get("message", "No message.")
            log.warning(f"API error {err_code}: {err_msg}")
            if int(err_code) not in retry_errs:
                raise exceptions.ScriptException("LFM_API_ERROR", "Error has no recovery.")
            else:
                log.warning(f"Retrying in {retry_backoff}...")
                time.sleep(retry_backoff)
                continue

        elif data is None:
            log.warning(f"Couldn't decode JSON in {r.status_code} response.")
            log.warning(f"Retrying in {retry_backoff}...")

        else:
            return data
