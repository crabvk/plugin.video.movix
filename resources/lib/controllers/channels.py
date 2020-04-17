from future import standard_library
standard_library.install_aliases()  # noqa: E402

import xbmcplugin
import xbmcgui
import resources.lib.api as api
import resources.lib.utils as utils
from resources.lib.translation import _


def index(router, params):
    handle = router.session.handle
    token = router.session.token
    paginate = utils.addon.getSettingBool('channels_pagination')

    if token['is_bound'] and paginate:
        limit = utils.addon.getSettingInt('page_limit')
        page = params.get('page', 1)
        resp = api.channels(token['token'], limit, page)
    else:
        resp = api.channels_all(token['token'], not token['is_bound'])

    if not resp.ok:
        if utils.show_error(resp.data, ask=_('button.try_again')):
            return index(router, params)
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

    # Next page
    if paginate and page < resp.meta['pages']:
        url = router.channels_url('index', page=page + 1)
        label = _('li.next_page_number') % (page + 1, resp.meta['pages'])
        li = xbmcgui.ListItem(label=label)
        channels.append((url, li, True))

    xbmcplugin.addDirectoryItems(handle, channels, len(channels))
    xbmcplugin.endOfDirectory(handle)
    xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_TRACKNUM)
    xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_TITLE)
