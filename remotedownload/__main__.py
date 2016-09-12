import cgi
import email.parser
import http.cookiejar
import json
import os
import os.path
import posixpath
import tempfile
import time
import urllib.parse

import requests

from .api import *

def log(message): print(message)

class ProgressReporter:

    def __init__(self):
        self.start_time = time.time()

    def __call__(self, done, doing):
        progress = float(done) / doing if doing != 0 else 1
        kbytesps = (done / (time.time() - self.start_time)) / 1024

        bar_width = 50
        bars = int(progress * bar_width)
        spaces = bar_width - bars

        print('\r' + \
            '[' + ('#' * bars) + (' ' * spaces) + ']' + \
            (' %d kB/s' % kbytesps), end='')

        if done == doing:
            self.finish()

    def finish(self):
        print('\r' + (' ' * 80), end='\r')

class Downloader:
    def __init__(self, data):
        # - Unused parameters:
        # label
        # folder

        data = json.loads(data.decode(encoding))

        session = requests.Session()

        referer = data.get(field_keys.referer)
        if referer: session.headers['Referer'] = referer
        user_agent = data.get(field_keys.user_agent)
        if user_agent: session.headers['User-Agent'] = user_agent

        cookies_txt = data.get(field_keys.cookies)
        if cookies_txt:
            cookies_file = tempfile.NamedTemporaryFile('wt', encoding='utf-8', delete=False)
            cookies_file.write(http.cookiejar.MozillaCookieJar.header)
            cookies_file.write(cookies_txt)
            cookies_file.close()

            cookie_jar = http.cookiejar.MozillaCookieJar()
            cookie_jar.load(cookies_file.name)

            os.remove(cookies_file.name)

            session.cookies = cookie_jar

        session.stream = True

        headers_string = data.get(field_keys.headers)
        if headers_string:
            headers = email.parser.Parser().parsestr(headers_string)
            session.headers.update(headers)

        self._session = session
        self._data = data
        self.urls = [i[item_keys.url] for i in data[field_keys.items]]

    def get(self, url, out_file, chunk_size=4096, progress_reporter=None):
        post = self._data.get(field_keys.post_data)
        if post:
            response = self._session.post(url, data=post, headers={'Content-Type': 'application/x-www-form-urlencoded'})
        else:
            response = self._session.get(url)

        response.raise_for_status()

        total_file_size = int(response.headers.get('Content-Length', 0))
        total_bytes_written = 0
        for chunk in response.iter_content(chunk_size):
            out_file.write(chunk)
            total_bytes_written += len(chunk)
            if progress_reporter: progress_reporter(total_bytes_written, total_file_size)
        if progress_reporter and total_file_size == 0: progress_reporter.finish()

        filename = None

        for item in self._data[field_keys.items]:
            if item[item_keys.url] == url:
                filename = os.path.basename(item.get(item_keys.filename, ''))

        if not filename:
            filename = cgi.parse_header(response.headers.get('Content-Disposition', ''))[1].get('filename')
            if filename:
                filename = os.path.basename(filename)
            else:
                # Guess it from the URL
                filename = posixpath.basename(urllib.parse.unquote(urllib.parse.urlparse(response.url).path))

        return filename or None # return None instead of empty string

def main():
    import sys

    if len(sys.argv) == 2:
        with open(sys.argv[1], 'rb') as f: downloader = Downloader(f.read())
    else:
        downloader = Downloader(sys.stdin.buffer.read())

    for url in downloader.urls:
        with tempfile.NamedTemporaryFile('wb', suffix='.remotedownload', dir=os.getcwd(), delete=False) as out_file:
            filename = downloader.get(url, out_file, progress_reporter=ProgressReporter())

        if filename:
            final_filename = filename
            duplicate_number = 2
            while True:
                # Make sure the file doesn't exist already
                try:
                    open(final_filename, 'xb').close()
                    break
                except:
                    root, ext = os.path.splitext(filename)
                    final_filename = '%s %d%s' % (root, duplicate_number, ext)
                    duplicate_number += 1

            os.replace(out_file.name, final_filename)
        else:
            final_filename = out_file.name

        log(os.path.abspath(final_filename))
