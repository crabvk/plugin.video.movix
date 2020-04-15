from future import standard_library
standard_library.install_aliases()  # noqa: E402

import xbmcplugin
import xbmcgui
import resources.lib.api as api
import resources.lib.utils as utils
from resources.lib.translation import _


def index(router, params):
    handle = router.session.handle
    page = params.get('page', 1)

    resp = api.serials(router.session.token['token'], page)
    if not resp.ok:
        if utils.show_error(resp.data, ask=_('button.try_again')):
            return index(router, params)
        return router.redirect('root', 'index')

    serials = []
    for srl in resp.data:
        li = xbmcgui.ListItem(label=srl['title'], label2=srl['description'])
        li.setArt({'poster': api.art_url(srl['poster_id'])})
        if srl['fanart_id']:
            li.setArt({'fanart': api.art_url(srl['fanart_id'], 630, 354)})
        li.setInfo('video', dict(
            title=srl['title'],
            plot=srl['description']
        ))
        url = router.serials_url('seasons', id=srl['id'], page=page)
        serials.append((url, li, True))

    # Next page
    if page < resp.meta['pages']:
        label = _('li.next_page') % (page + 1, resp.meta['pages'])
        li = xbmcgui.ListItem(label=label)
        url = router.serials_url('index', page=page + 1)
        serials.append((url, li, True))

    xbmcplugin.addDirectoryItems(handle, serials, len(serials))
    xbmcplugin.endOfDirectory(handle, updateListing=router.session.is_redirect)
    xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_TITLE)


def seasons(router, params):
    handle = router.session.handle

    resp = api.seasons(router.session.token['token'], params['id'])
    if not resp.ok:
        if utils.show_error(resp.data, ask=_('button.try_again')):
            return seasons(router, params)
        return router.redirect('serials', 'index', page=params['page'])

    items = []
    for sn in resp.data:
        li = xbmcgui.ListItem(label=sn['title'], label2=sn['description'])
        li.setArt({'poster': api.art_url(sn['poster_id'])})
        li.setInfo('video', dict(
            title=sn['title'],
            plot=sn['description'],
            tracknumber=sn['number']
        ))
        url = router.serials_url('episodes', id=sn['id'], serial_id=params['id'])
        items.append((url, li, True))

    xbmcplugin.addDirectoryItems(handle, items, len(items))
    xbmcplugin.endOfDirectory(handle, updateListing=router.session.is_redirect)
    xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_TRACKNUM)
    xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_TITLE)


def episodes(router, params):
    handle = router.session.handle

    resp = api.episodes(router.session.token['token'], params['id'])
    if not resp.ok:
        if utils.show_error(resp.data, ask=_('button.try_again')):
            return episodes(router, params)
        return router.redirect('serials', 'seasons', id=params['serial_id'])

    items = []
    for epd in resp.data:
        li = xbmcgui.ListItem(label=epd['title'], label2=epd['description'])
        if epd['poster_id']:
            li.setArt({'poster': api.art_url(epd['poster_id'])})
        li.setInfo('video', dict(
            title=epd['title'],
            plot=epd['description'],
            tracknumber=epd['number']
        ))
        li.setProperty('IsPlayable', 'true')
        url = router.root_url('play', id=epd['id'], hls_id=epd['hls_id'])
        items.append((url, li, False))

    xbmcplugin.addDirectoryItems(handle, items, len(items))
    xbmcplugin.endOfDirectory(handle)
    xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_TRACKNUM)
    xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_TITLE)
