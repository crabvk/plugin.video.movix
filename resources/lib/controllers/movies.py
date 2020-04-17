from future import standard_library
standard_library.install_aliases()  # noqa: E402

import xbmcplugin
import xbmcgui
import resources.lib.api as api
import resources.lib.utils as utils
from resources.lib.translation import _


def index(router, params):
    handle = router.session.handle
    limit = utils.addon.getSettingInt('page_limit')
    offset = params.get('offset', 0)

    resp = api.movies(router.session.token['token'], limit, offset)
    if not resp.ok:
        if utils.show_error(resp.data, ask=_('button.try_again')):
            return index(router, params)
        return router.redirect('root', 'index')

    movies = []
    for mov in resp.data:
        li = xbmcgui.ListItem(label=mov['title'], label2=mov['description'])
        li.setArt({'poster': api.art_url(mov['poster_id'])})
        if mov['fanart_id']:
            li.setArt({'fanart': api.art_url(mov['fanart_id'], 630, 354)})
        li.setInfo('video', dict(
            title=mov['title'],
            plot=mov['description']
        ))
        li.setProperty('IsPlayable', 'true')
        url = router.root_url('play', id=mov['id'], hls_id=mov['hls_id'])
        movies.append((url, li, False))

    # Next page
    if resp.meta['offset'] < resp.meta['total']:
        li = xbmcgui.ListItem(label=_('li.next_page'))
        url = router.movies_url('index', offset=resp.meta['offset'])
        movies.append((url, li, True))

    xbmcplugin.addDirectoryItems(handle, movies, len(movies))
    xbmcplugin.endOfDirectory(handle)
    xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_TITLE)
