from future import standard_library
standard_library.install_aliases()  # noqa: E402

import xbmcplugin
import xbmcgui
import resources.lib.api as api
import resources.lib.utils as utils
from resources.lib.translation import _


def index(router, _params=None):
    handle = router.session.handle
    token = router.session.token

    resp = api.channels(token['token'], not token['is_bound'])
    if not resp.ok:
        if utils.show_error(resp.data, ask=_('button.try_again')):
            return index(router)
        return router.redirect('root', 'index')

    channels = []
    for ch in resp.data:
        li = xbmcgui.ListItem(label=ch['title'], label2=ch['description'])
        li.setArt({'poster': api.art_url(ch['poster_id'])})
        li.setInfo('video', dict(
            title=ch['title'],
            plot=ch['description'],
            tracknumber=ch['lcn']
        ))
        li.setProperty('IsPlayable', 'true')
        url = router.root_url('play', id=ch['id'], hls_id=ch['hls_id'])
        channels.append((url, li, False))

    xbmcplugin.addDirectoryItems(handle, channels, len(channels))
    xbmcplugin.endOfDirectory(handle)
    xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_TRACKNUM)
    xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_TITLE)
