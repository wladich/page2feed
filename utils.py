# coding: utf-8

import base64
import requests
import urlparse
import time


def datauri(s):
    return 'data:text/html;base64,' + base64.standard_b64encode(s)


def get_favicon(url):
    url = urlparse.urlparse(url)
    url = '%s://%s/favicon.ico' % (url.scheme, url.netloc)
    try:
        response = requests.get(url)
        if response.status_code != 200:
            return None
        return response.content
    except:
        pass
    return None


def now():
    return int(time.time())


def open_in_browser(s, encoding=None):
    import os
    import webbrowser
    import tempfile
    handle, fn = tempfile.mkstemp(suffix='.html')
    f = os.fdopen(handle, 'wb')
    try:
        f.write(s)
    finally:
        # we leak the file itself here, but we should at least close it
        f.close()
    url = 'file://' + fn.replace(os.path.sep, '/')
    print(url)
    webbrowser.open(url)
