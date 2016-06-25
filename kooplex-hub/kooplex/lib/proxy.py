﻿from kooplex.lib.libbase import LibBase
from kooplex.lib.libbase import get_settings
from kooplex.lib.restclient import RestClient

class ProxyError(Exception):
    pass

class Proxy(RestClient):

    def __init__(self, host=None, port=None, auth_token=None, https=None, external_url=None):
        self.host = get_settings('KOOPLEX_PROXY', 'host', host, '127.0.0.1')
        self.port = get_settings('KOOPLEX_PROXY', 'port', port, 8001)
        self.https = get_settings('KOOPLEX_PROXY', 'https', https, False)
        self.auth_token = get_settings('KOOPLEX_PROXY', 'auth_token', auth_token, None)
        self.external_url = get_settings('KOOPLEX_PROXY', 'external_url', external_url, 'http://localhost')

    def http_prepare_headers(self, headers):
        headers = RestClient.http_prepare_headers(self, headers)
        if self.auth_token:
            headers['Authorization'] = 'token ' + self.auth_token
        return headers

    def get_external_url(self, path):
        url = RestClient.join_url(self.external_url, path)
        return url

    def make_path(self, path):
        path = RestClient.join_url('/api/routes/', path)
        return path

    def make_route(self, path, host=None, port=None, https=None):
        path = self.make_path(path)
        target = RestClient.make_url(host=host, port=port, https=https)
        data = {'target': target}
        return path, data

    def add_route(self, path, host, port, https=False):
        path, data = self.make_route(path, host, port, https)
        res = self.http_post(path, data=data)
        if res.status_code != 201:
            raise ProxyError

    def get_route(self, path):
        path = self.make_path(path)
        res = self.http_get(path)
        # NOTE: proxy returns something, even if route doesn't exist
        #if res.status_code != 200:
        #    raise ProxyError
        return res.json()

    def remove_route(self, path):
        url, data = self.make_route(path)
        res = self.http_delete(url)
