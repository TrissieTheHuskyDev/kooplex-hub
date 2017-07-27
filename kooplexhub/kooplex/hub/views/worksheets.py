import base64
import codecs

from django.conf.urls import patterns, url, include
from django.shortcuts import render, redirect
from django.http import HttpRequest,HttpResponse
from django.template import RequestContext
from datetime import datetime
from django.http import HttpRequest, HttpResponseRedirect

from kooplex.hub.models.report import Report
from kooplex.hub.models.dashboard_server import Dashboard_server
from kooplex.lib.libbase import get_settings
from kooplex.lib.gitlab import Gitlab
from kooplex.lib.spawner import Spawner
from kooplex.lib.debug import *
from kooplex.hub.models.user import HubUser
from kooplex.hub.models.project import Project

import os

#TODO: rename worksheet -> report

HUB_REPORTS_URL = '/hub/worksheets'

def group_by_project(reports):
    reports_grouped = {}
    for r in reports:
        if not r.project in reports_grouped:
            reports_grouped[r.project] = []
        reports_grouped[r.project].append(r)
    for rl in reports_grouped.values():
        rl.sort()
    return reports_grouped

def worksheets(request):
    """Renders the worksheets page"""
    assert isinstance(request, HttpRequest)
    if request.user.is_anonymous():
        myreports = []
        internal_good_ = []
        username = None
    else:
        username = request.user.username
        me = HubUser.objects.get(username = username)
        my_gitlab_id = str( HubUser.objects.get(username = username).gitlab_id )
        myreports = Report.objects.filter(creator = me)
        internal_ = Report.objects.filter(scope = 'internal')
        internal_good_ = filter(lambda x: my_gitlab_id in x.project.gids.split(','), internal_)
    publicreports = list( Report.objects.filter(scope = 'public') )
    publicreports.extend(internal_good_)
    return render(
        request,
        'app/worksheets.html',
        context_instance = RequestContext(request,
        {
            'title':'Browse worksheets',
            'message':'',
            'myreports': group_by_project( myreports ),
            'publicreports': group_by_project( publicreports ),
            'username' : username,
       })
    )

def worksheets_open_as_dashboard(request):
#FIXME: check if authorization is enforced by the dashboard
    url = request.GET['url']
    cache_url = request.GET['cache_url']
    D = Dashboards()
    D.clear_cache_temp(cache_url)
    return HttpResponseRedirect(url)

def worksheets_open_html(request):
    report_id = request.GET['report_id']
    try:
        report = Report.objects.get(id = report_id)
    except Report.DoesNotExist:
        return HttpResponseRedirect(HUB_REPORTS_URL)
    if request.user.is_anonymous():
        if report.scope == 'public':
            pass
        else:
            return HttpResponseRedirect(HUB_REPORTS_URL)
    else:
        me = HubUser.objects.get(username = request.user.username)
        if report.scope == 'internal' and me in report.project.members_:
            pass
        elif report.creator == me:
            pass
        else:
            return HttpResponseRedirect(HUB_REPORTS_URL)
    with codecs.open(report.entry_, 'r', 'utf-8') as f:
        content = f.read()
    return HttpResponse(content)

def worksheets_open_html_latest(request):
    project_id = request.GET['project_id']
    try:
        project = Project.objects.get(id = project_id)
        reports = list(Report.objects.filter(project = project, scope = 'public'))
        report = reports.pop()
        while len(reports):
            r = reports.pop()
            if r.ts_created > report.ts_created:
                report = r
    except Report.DoesNotExist:
        return HttpResponseRedirect(HUB_REPORTS_URL)
    return HttpResponseRedirect(HUB_REPORTS_URL + 'open?report_id=%d' % report.id)

def reports_unpublish(request):
    if request.user.is_anonymous():
        return HttpResponseRedirect(HUB_REPORTS_URL)
    try:
        me = HubUser.objects.get(username = request.user.username)
        report_id = int(request.GET['report_id'])
        r = Report.objects.get(id = report_id, creator = me)
        r.remove()
    except Report.DoesNotExist:
        # only the creator is allowed to remove the report
        pass
    return HttpResponseRedirect(HUB_REPORTS_URL)

def report_changescope(request):
    if request.user.is_anonymous():
        return HttpResponseRedirect(HUB_REPORTS_URL)
    try:
        me = HubUser.objects.get(username = request.user.username)
        report_id = int(request.POST['report_id'])
        r = Report.objects.get(id = report_id)
        r.scope = request.POST['scope']
        r.save()
    except Report.DoesNotExist:
        # only the creator is allowed to change the scope of the report
        pass
    return HttpResponseRedirect(HUB_REPORTS_URL)

def report_former(request):
    try:
        report_id = int(request.POST['report_id'])
        return HttpResponseRedirect(HUB_REPORTS_URL + "open?report_id=%s" % report_id)  #FIXME: ugly
    except:
        return HttpResponseRedirect(HUB_REPORTS_URL)

def report_settings(request):
    return HttpResponseRedirect(HUB_REPORTS_URL)

urlpatterns = [
    url(r'^$', worksheets, name='worksheets'),
    url(r'^open$', worksheets_open_html, name='worksheet-open'),
    url(r'^openlatest$', worksheets_open_html_latest, name='worksheet-open-latest'),
    url(r'^opendashboard$', worksheets_open_as_dashboard, name='worksheet-open-as-dashboard'),
    url(r'^unpublish$', reports_unpublish, name='worksheet-unpublish'),
    url(r'^changescope$', report_changescope, name='reportschangescope'),
    url(r'^former$', report_former, name='reportformer'),
    url(r'^settings$', report_settings, name='report-settings'),
]

