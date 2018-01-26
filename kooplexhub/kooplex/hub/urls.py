from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.views import login as login_view
from django.template import RequestContext
from django.conf.urls import url, include
from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponseRedirect
from datetime import datetime
from django.contrib import messages

from kooplex.hub.forms import authenticationForm
from kooplex.hub.views import passwordresetForm, passwordtokenForm, passwordchangeForm
from kooplex.hub.models import User

def indexpage(request):
    """Renders the home page."""
    assert isinstance(request, HttpRequest)
    if request.user.is_active:
        return redirect('/hub/projects')

    return render(
        request,
        'app/index.html',
        context_instance = RequestContext(request,
        {
            'title': 'Home Page',
            'year': datetime.now().year,
        })
    )

def loginHandler(request, *v, **kw):
    if request.method == 'GET':
        if request.user.is_authenticated:
            if isinstance(request.user, User):
                messages.info(request, 'You are already logged in as %s.' % request.user.username)
                return redirect('projects')
            else:
                messages.info(request, 'User %s was logged in but we logged it out.' % request.user.username)
                logout(request)
        return login_view(request, *v, **kw)
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(username = username, password = password)
        if user is not None:
            login(request, user)
            return redirect('projects')
        else:
            return redirect('login')
    return redirect('indexpage')


def logoutHandler(request):
    logout(request)
    return redirect('indexpage')

def tutorial(request):
    """Renders the page with videos."""
    assert isinstance(request, HttpRequest)
    return render(request, 'tutorial/tutorial.html')

login_kwargs = {
    'template_name': 'auth/login.html',
    'authentication_form': authenticationForm,
    'extra_context':
    {
        'next_page': '/hub/projects',
        'year': datetime.now().year,
        'title' : 'Login',
    }
}

urlpatterns = [
    url(r'^/?$', indexpage, name = 'indexpage'),
    url(r'^/tutorial$', tutorial, name = 'tutorial'),

    url(r'^/login/?$', loginHandler, login_kwargs, name = 'login'),
    url(r'^/logout$', logoutHandler, name = 'logout'),
    url(r'^/passwordreset$', passwordresetForm, name = 'passwordreset'),
    url(r'^/passwordtoken$', passwordtokenForm, name = 'passwordresettoken'),
    url(r'^/passwordchange$', passwordchangeForm, name = 'passwordchange'),

    url(r'^/projects', include('kooplex.hub.views.projects')),
    url(r'^/publish', include('kooplex.hub.views.publish')),
    url(r'^/reports', include('kooplex.hub.views.reports')),
]
