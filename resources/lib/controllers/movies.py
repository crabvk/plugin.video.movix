import xbmcplugin
import xbmcgui
import resources.lib.api as api
import resources.lib.utils as utils
from resources.lib.translation import _


def index_page(router, params, free):
    handle = router.session.handle
    limit = utils.addon.getSettingInt('page_limit')
    offset = params.get('offset', 0)

    resp = api.movies(router.session.token['token'], limit, offset, free)
    movies = []
    for mov in resp['movies']:
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
    if resp['offset'] < resp['total']:
        label = _('li.next_page_left') % (resp['total'] - resp['offset'])
        li = xbmcgui.ListItem(label=label)
        url = router.movies_url('index_free' if free else 'index', offset=resp['offset'])
        movies.append((url, li, True))

    xbmcplugin.addDirectoryItems(handle, movies, len(movies))
    xbmcplugin.endOfDirectory(handle)
    xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_TITLE)


@api.on_error(lambda r: r.redirect('root', 'index'))
def index(router, params):
    index_page(router, params, free=False)


@api.on_error(lambda r: r.redirect('root', 'index'))
def index_free(router, params):
    index_page(router, params, free=True)
