﻿import json
import requests
from django.conf import settings
from threadlocals.threadlocals import get_current_request

from kooplex.lib.libbase import LibBase
from kooplex.lib.restclient import RestClient
from kooplex.lib.libbase import get_settings

class Gitlab(RestClient):
    """description of class"""

    SESSION_PRIVATE_TOKEN_KEY = 'gitlab_user_private_token'
    HEADER_PRIVATE_TOKEN_KEY = 'PRIVATE-TOKEN'
    URL_PRIVATE_TOKEN_KEY = 'private_token'

    base_url = get_settings('gitlab', 'base_url', None, 'http://www.gitlab.com/')

    def __init__(self, request=None):
        self.request = request
        self.session = {}       # local session used for unit tests
    
    ###########################################################
    # HTTP request authentication

    def get_session_store(self):
        if self.request:
            return self.request.session
        else:
            request = get_current_request()
        if request:
            return request.session
        else:
            return self.session

    def get_user_private_token(self):
        s = self.get_session_store()
        if Gitlab.SESSION_PRIVATE_TOKEN_KEY in s:
            return s[Gitlab.SESSION_PRIVATE_TOKEN_KEY]
        else:
            return None

    def set_user_private_token(self, user):
        s = self.get_session_store()
        s[Gitlab.SESSION_PRIVATE_TOKEN_KEY] = user[Gitlab.URL_PRIVATE_TOKEN_KEY]

    def http_prepare_url(self, url):
        return RestClient.join_path(Gitlab.base_url, url)

    def http_prepare_headers(self, headers):
        headers = RestClient.http_prepare_headers(self, headers)
        token = self.get_user_private_token()
        if token:
            headers[Gitlab.HEADER_PRIVATE_TOKEN_KEY] = token
        return headers

    ###########################################################
    # Django authentication hooks

    def authenticate(self, username=None, password=None):
        res = self.http_post("api/v3/session", params={'login': username, 'password': password})
        if res.status_code == 201:
            u = res.json()
            return res, u
        return res, None

    def get_user(self, username):
        return None

    def authenticate_user(self, username=None, password=None):
        res, user = self.authenticate(username, password)
        if user is not None:
            self.set_user_private_token(user)
            return res, user
        return res, None
    
    ###########################################################
    # Projects

    def get_projects(self):
        res = self.http_get('api/v3/projects')
        projects_json = res.json()
        unforkable_projectids = self.get_unforkable_projectids(projects_json)
        return projects_json, unforkable_projectids

    def get_unforkable_projectids(self, projects_json):
        result = set()
        for project in projects_json:
            if 'forked_from_project' in project:
                result.add(project['forked_from_project']['id'])
        return result

    def fork_project(self, itemid):
        res = self.http_post("api/v3/projects/fork/" + itemid)
        message = ""
        if res.status_code == 409:
            message = res.json()["message"]["base"][0]
        return message

    def create_mergerequest(self, project_id, target_id, title, description):
        url = "api/v3/projects/"
        url += project_id
        url += "/merge_requests?source_branch=master&target_branch=master"
        url += "&target_project_id=" + target_id
        url += "&title=" + title
        url += "&description=" + description
        res = self.http_post(url)
        message = ""
        if res.status_code != 201:
            message = res.json()
        return message

    def list_mergerequests(self, itemid):
        url = "api/v3/projects/"
        url += itemid
        url += "/merge_requests?state=opened"
        res = self.http_get(url)
        return res.json()

    def accept_mergerequest(self, project_id, mergerequestid):
        url = "api/v3/projects/"
        url += project_id
        url += "/merge_requests/"
        url += mergerequestid
        url += "/merge"
        res = self.http_put(url)
        message = ""
        if res.status_code != 200:
            message = res.json()
        return message