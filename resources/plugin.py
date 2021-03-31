import sys
import xbmcplugin
from resources.lib.router import Router
from resources.lib.controllers import (
    root,
    channels,
    channel_packages,
    movies,
    serials
)

router = Router('plugin://plugin.video.movix')
router.add('/', root, 'index')
router.add('/sign_in', root, 'sign_in')
router.add('/sign_in_sms', root, 'sign_in_sms')
router.add('/play/{id}/{hls_id}', root, 'play', id=int, hls_id=int)
router.add('/channels', channels, 'index', page=int)
router.add('/channel-packages', channel_packages, 'index', page=int)
router.add('/channel-packages/{id}/channels', channel_packages, 'channels', id=int, packages_page=int, adult=int)
router.add('/movies', movies, 'index', offset=int)
router.add('/movies/free', movies, 'index_free', offset=int)
router.add('/serials', serials, 'index', offset=int)
router.add('/serials/{id}/seasons', serials, 'seasons', id=int, serials_offset=int)
router.add('/episodes/season/{id}', serials, 'episodes', id=int, serial_id=int)

if len(sys.argv) == 4:
    xbmcplugin.setContent(int(sys.argv[1]), 'videos')
    router.run(*sys.argv)  # pylint: disable=no-value-for-parameter
