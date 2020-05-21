from future import standard_library
standard_library.install_aliases()  # noqa: E402

import xbmcplugin
import xbmcgui
import resources.lib.api as api
import resources.lib.utils as utils
from resources.lib.translation import _


@api.on_error(lambda r: r.redirect('root', 'index'))
def index(router, params):
    handle = router.session.handle
    limit = utils.addon.getSettingInt('page_limit')
    page = params.get('page', 1)

    resp = api.serials(router.session.token['token'], limit, page)
    serials = []
    for srl in resp['serials']:
        li = xbmcgui.ListItem(label=srl['title'], label2=srl['description'])
        li.setArt({'poster': api.art_url(srl['poster_id'])})
        if srl['fanart_id']:
            li.setArt({'fanart': api.art_url(srl['fanart_id'], 630, 354)})
        li.setInfo('video', dict(
            title=srl['title'],
            plot=srl['description']
        ))
        url = router.serials_url('seasons', id=srl['id'], serials_page=page)
        serials.append((url, li, True))

    # Next page
    if page < resp['pages']:
        label = _('li.next_page_number') % (page + 1, resp['pages'])
        li = xbmcgui.ListItem(label=label)
        url = router.serials_url('index', page=page + 1)
        serials.append((url, li, True))

    xbmcplugin.addDirectoryItems(handle, serials, len(serials))
    xbmcplugin.endOfDirectory(handle, updateListing=router.session.is_redirect)
    xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_TITLE)


@api.on_error(lambda r, p: r.redirect('serials', 'index', page=p['serials_page']))
def seasons(router, params):
    handle = router.session.handle

    resp = api.seasons(router.session.token['token'], params['id'])
    items = []
    for sn in resp['seasons']:
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


@api.on_error(lambda r, p: r.redirect('serials', 'seasons', id=p['serial_id']))
def episodes(router, params):
    handle = router.session.handle

    resp = api.episodes(router.session.token['token'], params['id'])
    items = []
    for epd in resp['episodes']:
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
