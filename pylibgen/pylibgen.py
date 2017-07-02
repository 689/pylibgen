import os
import re
import requests
import webbrowser
from urllib.parse import quote_plus
from . import constants


class Library(object):

    def __init__(self, mirror=constants.DEFAULT_MIRROR):
        assert(mirror in constants.MIRRORS)
        self.mirror = mirror


    def search(self, query, type='title'):
        '''Performs a search query to libgen and returns a list of
        libgen book IDs that matched the query.

        You can specify a search type: title, author, isbn.
        For ISBN searches, the query can be ISBN 10 or 13, either is fine.
        '''
        assert(type in {'title', 'author', 'isbn'})
        r = self.__req('search', {
            'req': quote_plus(query),
            'column': type,
        })
        return re.findall("<tr.*?><td>(\d+)", r.text)


    def lookup(self, ids, fields=constants.DEFAULT_FIELDS):
        '''Returns a list of JSON dicts each containing metadata field
        values for each libgen book ID. Uses the unofficial libgen query
        API to retrieve this information.

        The default fields are probably enough, but there are a LOT
        more like openlibraryid, publisher, etc. To get all fields,
        use fields=['*'].
        '''
        r = self.__req('lookup', {
            'ids': ','.join(ids),
            'fields': ','.join(fields),
        })
        return r.json()


    def get_download_url(self, md5, enable_ads=False):
        '''Given the libgen MD5 hash of a book, this returns a valid but
        temporary (keys expire) URL for a direct download. The key is parsed
        from the initial redirect to ads.php.

        If you want to support Library Genesis, setting enable_ads to True
        will just return the download URL with no key, which redirects to ads.php.
        '''
        url = self.__req('download', {'md5': md5}, urlonly=True)
        if enable_ads:
            return url

        r = self.__req('download', {'md5': md5})
        key = re.findall("&key=(.*?)'", r.text)[0]
        return url + '&key={}'.format(key)


    def download(self, md5, dest='.', use_browser=False):
        '''Downloads a book given its libgen MD5 hash to the destination directory.

        Libgen seems to delay programmatically sent dl requests, even if the UA
        string is spoofed and the URL contains a good key, so I recommend just
        using get_download_url. Alternatively, you can set use_browser=True, which
        will just open up the download URL in a new browser tab.

        Note that if you spam download requests, libgen will temporarily 503.
        Again, I recommend using get_download_url and downloading from the browser.
        '''
        auth_url = self.get_download_url(md5, enable_ads=False)
        if use_browser:
            webbrowser.open_new_tab(auth_url)
            return

        r = requests.get(auth_url)
        r.raise_for_status()
        with open(os.path.join(dest, md5), 'wb') as f:
            for chunk in r.iter_content(1024):
                f.write(chunk)


    def __req(self, endpoint, getargs, urlonly=False):
        url = constants.ENDPOINTS[endpoint].format(
            mirror=self.mirror, **getargs
        )
        if urlonly:
            return url
        r = requests.get(url)
        r.raise_for_status()
        return r