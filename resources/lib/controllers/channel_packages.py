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

    resp = api.channel_packages(router.session.token['token'], limit, page)
    packages = []
    for pkg in resp['packages']:
        li = xbmcgui.ListItem(label=pkg['title'], label2=pkg['description'])
        li.setArt(dict(
            poster=api.art_url(pkg['poster_id']),
            fanart=api.art_url(pkg['fanart_id'])
        ))
        li.setInfo('video', dict(title=pkg['title'], plot=pkg['description']))
        adult = {'adult': 1} if pkg['adult'] == 'adult' else {}
        url = router.channel_packages_url('channels', id=pkg['id'], packages_page=page, **adult)
        packages.append((url, li, True))

    # Next page
    if page < resp['pages']:
        url = router.channel_packages_url('index', page=page + 1)
        label = _('li.next_page_number') % (page + 1, resp['pages'])
        li = xbmcgui.ListItem(label=label)
        packages.append((url, li, True))

    xbmcplugin.addDirectoryItems(handle, packages, len(packages))
    xbmcplugin.endOfDirectory(handle, updateListing=router.session.is_redirect)


@api.on_error(lambda r, p: r.redirect('channel_packages', 'index', page=p.get('packages_page')))
def channels(router, params):
    handle = router.session.handle

    resp = api.package_channels(router.session.token['token'], params['id'], params.get('adult'))
    items = []
    for ch in resp['channels']:
        li = xbmcgui.ListItem(label=ch['title'], label2=ch['description'])
        li.setArt({'poster': api.art_url(ch['poster_id'])})
        li.setInfo('video', dict(
            title=ch['title'],
            plot=ch['description'],
            tracknumber=ch['lcn']
        ))
        li.setProperty('IsPlayable', 'true')
        url = router.root_url('play', id=ch['id'], hls_id=ch['hls_id'])
        items.append((url, li, False))

    xbmcplugin.addDirectoryItems(handle, items, len(items))
    xbmcplugin.endOfDirectory(handle)
    xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_TRACKNUM)
    xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_TITLE)
