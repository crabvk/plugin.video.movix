from future import standard_library
standard_library.install_aliases()  # noqa: E402

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
router.add('/play/{id}', root, 'play', id=int, hls_id=int)
router.add('/channels', channels, 'index')
router.add('/channel-packages', channel_packages, 'index')
router.add('/channel-packages/{id}/channels', channel_packages, 'channels', id=int, adult=int)
router.add('/movies', movies, 'index', page=int)
router.add('/serials', serials, 'index', page=int)
router.add('/serials/{id}/seasons', serials, 'seasons', id=int, page=int)
router.add('/episodes/season/{id}', serials, 'episodes', id=int, serial_id=int)

if len(sys.argv) == 4:
    handle = int(sys.argv[1])
    xbmcplugin.setContent(handle, 'videos')
    router.run(*sys.argv)
