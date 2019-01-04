import logging

from django.contrib import messages
from django.conf.urls import url, include
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.utils.html import format_html
import django_tables2 as tables
from django_tables2 import RequestConfig
from django.utils.translation import gettext_lazy as _


from hub.forms import FormProject
from hub.forms import table_collaboration
from hub.models import Project, UserProjectBinding, Volume
from hub.models import Image
from hub.models import Profile

from kooplex.logic import configure_project

logger = logging.getLogger(__name__)

@login_required
def new(request):
    logger.debug("user %s" % request.user)
    user_id = request.POST.get('user_id')
    try:
        assert user_id is not None and int(user_id) == request.user.id, "user id mismatch: %s tries to save %s %s" % (request.user, request.user.id, request.POST.get('user_id'))
        projectname = request.POST.get('name')
        for upb in UserProjectBinding.objects.filter(user = request.user):
            assert upb.project.name != projectname, "Not a unique name"
        form = FormProject(request.POST)
        form.save()
        upb = UserProjectBinding(user = request.user, project = form.instance, role = UserProjectBinding.RL_CREATOR)
        upb.save()
        messages.info(request, 'Your new project is created')
        return redirect('project:list')
    except Exception as e:
        logger.error("New project not created -- %s" % e)
        messages.error(request, 'Creation of a new project is refused.')
        return redirect('indexpage')
        


@login_required
def listprojects(request):
    """Renders the projectlist page for courses taught."""
    logger.debug('Rendering project.html')
    context_dict = {
        'next_page': 'project:list',
    }
    return render(request, 'project/list.html', context = context_dict)


class ProjectSelectionColumn(tables.Column):
    def render(self, record):
        state = "checked" if record.is_hidden else ""
        return format_html('<input type="checkbox" name="selection" value="%s" %s>' % (record.id, state))

class T_PROJECT(tables.Table):
    id = ProjectSelectionColumn(verbose_name = 'Hide', orderable = False)
    class Meta:
        model = UserProjectBinding
        fields = ('id', 'project')
        sequence = ('id', 'project')
        attrs = { "class": "table-striped table-bordered", "td": { "style": "padding:.5ex" } }

def sel_col(project):
    class VolumeSelectionColumn(tables.Column):
        def render(self, record):
            state = "checked" if record in project.volumes else ""
            return format_html('<input type="checkbox" name="selection" value="%s" %s>' % (record.id, state))
    return VolumeSelectionColumn

def sel_table(user, project, volumetype):
    if volumetype == 'functional': #FIXME: Volume.FUNCTIONAL
        user_volumes = user.profile.functional_volumes
    elif volumetype == 'storage':
        user_volumes = user.profile.storage_volumes
    column = sel_col(project)

    class T_VOLUME(tables.Table):
        id = column(verbose_name = 'Selection')
    
        class Meta:
            model = Volume
            exclude = ('name', 'volumetype')
            attrs = { "class": "table-striped table-bordered", "td": { "style": "padding:.5ex" } }
    return T_VOLUME(user_volumes)


@login_required
def configure(request, project_id, next_page):
    """Handles the project configuration."""
    user = request.user
    logger.debug("method: %s, project id: %s, user: %s" % (request.method, project_id, user))
    try:
        project = Project.get_userproject(project_id = project_id, user = request.user)
    except Project.DoesNotExist:
        messages.error(request, 'Project does not exist')
        return redirect(next_page)
    if request.method == 'POST':
        logger.debug(request.POST)
        button = request.POST.get('button')
        if button == 'apply':
            msg = []
            for role in request.POST.getlist('role_map'):
                targetrole, userid = role.split('-')
                u = User.objects.get(id = userid)
                if targetrole == 'skip':
                    try:
                        UserProjectBinding.objects.get(user = u, project = project).delete()
                        msg.append("Removed %s from the collaboration" % u)
                    except UserProjectBinding.DoesNotExist:
                        pass
                elif targetrole == 'collaborator':
                    try:
                        upb = UserProjectBinding.objects.get(user = u, project = project)
                        upb.role = UserProjectBinding.RL_COLLABORATOR #FIXME: if really changed message
                        upb.save()
                    except UserProjectBinding.DoesNotExist:
                        UserProjectBinding.objects.create(user = u, project = project, role = UserProjectBinding.RL_COLLABORATOR)
                        msg.append("%s is in collaboration" % u)
                elif targetrole == 'admin':
                    try:
                        upb = UserProjectBinding.objects.get(user = u, project = project)
                        upb.role = UserProjectBinding.RL_ADMIN        #FIXME: like above
                        upb.save()
                    except UserProjectBinding.DoesNotExist:
                        UserProjectBinding.objects.create(user = u, project = project, role = UserProjectBinding.RL_ADMIN)
                        msg.append("%s is in collaboration and is an admin" % u)
            if len(msg):
                messages.info(request, '\n'.join(msg))
            volumes = [ Volume.objects.get(id = x) for x in request.POST.getlist('selection') ]
            imagename = request.POST['project_image']
            image = Image.objects.get(name = imagename) if imagename != 'None' else None
    #        scope = ScopeType.objects.get(name = request.POST['project_scope'])
            description = request.POST.get('description')
            marked_to_remove = configure_project(project, image = image, volumes = volumes, description = description)
            if marked_to_remove:
                messages.info(request, '%d running containers of project %s will be removed when you stop. Changes take effect after a restart.' % (marked_to_remove, project))
        return redirect(next_page)
    else:
        everybody = filter(lambda p: p not in [ user.profile ], Profile.objects.all()) # FIXME: get rid of hubadmin
        table = table_collaboration(project)
        table_collaborators = table(everybody)
        RequestConfig(request).configure(table_collaborators)
        context_dict = {
            'images': Image.objects.all(),
            'project': project, 
            'enable_image': True,
            'enable_modulevolume': True, 
            'enable_storagevolume': True,
            't_collaborators': table_collaborators,
            't_volumes_fun': sel_table(user = user, project = project, volumetype = 'functional'), #FIXME: tables placed in forms/ ReqConfig
            't_volumes_stg': sel_table(user = user, project = project, volumetype = 'storage'),    #FIXME: like above
            'next_page': next_page,
        }
        return render(request, 'project/settings.html', context = context_dict)


@login_required
def delete_leave(request, project_id, next_page):
    """Delete or leave a project."""
    user = request.user
    logger.debug("method: %s, project id: %s, user: %s" % (request.method, project_id, user))
    try:
        project = Project.get_userproject(project_id = project_id, user = request.user)
    except Project.DoesNotExist:
        messages.error(request, 'Project does not exist')
        return redirect(next_page)
    if project.is_admin(request.user):
        project.delete()
        messages.info(request, 'Project %s is deleted' % (project))
    elif project.is_collaborator(request.user):
        UserProjectBinding.objects.get(project = project, user = request.user).delete()
        messages.info(request, 'You left project %s' % (project))
    return redirect(next_page)


@login_required
def show_hide(request, next_page):
    """Manage your projects"""
    user = request.user
    logger.debug("user %s method %s" % (user, request.method))
    userprojectbindings = user.profile.projectbindings
    userprojectbindings_course = user.profile.courseprojects_taught_NEW() #FIXME: diak is hideolhat ?
    if request.method == 'GET':
        table_project = T_PROJECT(userprojectbindings)
        table_course = T_PROJECT(userprojectbindings_course)
        RequestConfig(request).configure(table_project)
        RequestConfig(request).configure(table_course)
        context_dict = {
            't_project': table_project,
            't_course': table_course,
            'next_page': next_page,
        }
        return render(request, 'project/manage.html', context = context_dict)
    else:
        hide_bindingids_req = set([ int(i) for i in request.POST.getlist('selection') ])
        n_hide = 0
        n_unhide = 0
        for upb in set(userprojectbindings).union(userprojectbindings_course):
            if upb.is_hidden and not upb.id in hide_bindingids_req:
                upb.is_hidden = False
                upb.save()
                n_unhide += 1
            elif not upb.is_hidden and upb.id in hide_bindingids_req:
                upb.is_hidden = True
                upb.save()
                n_hide += 1
        msgs = []
        if n_hide:
            msgs.append('%d projects are hidden.' % n_hide)
        if n_unhide:
            msgs.append('%d projects are unhidden.' % n_unhide)
        if len(msgs):
            messages.info(request, ' '.join(msgs))
        return redirect(next_page)

@login_required
def hide(request, project_id, next_page):
    """Hide project from the list."""
    logger.debug("project id %s, user %s" % (project_id, request.user))
    try:
        project = Project.objects.get(id = project_id)
        UserProjectBinding.setvisibility(project, request.user, hide = True)
    except Project.DoesNotExist:
        messages.error(request, 'You cannot hide the requested project.')
    except ProjectDoesNotExist:
        messages.error(request, 'You cannot hide the requested project.')
    return redirect(next_page)


urlpatterns = [
    url(r'^list', listprojects, name = 'list'), 

    url(r'^new/?$', new, name = 'new'), 

    url(r'^configure/(?P<project_id>\d+)/(?P<next_page>\w+:?\w*)$', configure, name = 'configure'), 
    url(r'^delete/(?P<project_id>\d+)/(?P<next_page>\w+:?\w*)$', delete_leave, name = 'delete'), 
    url(r'^show/(?P<next_page>\w+:?\w*)$', show_hide, name = 'showhide'),
    url(r'^hide/(?P<project_id>\d+)/(?P<next_page>\w+:?\w*)$', hide, name = 'hide'), 
]

