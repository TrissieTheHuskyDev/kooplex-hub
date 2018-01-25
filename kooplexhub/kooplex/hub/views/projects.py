import re
import logging

from django.contrib import messages
from django.conf.urls import patterns, url, include
from django.shortcuts import render, redirect
from django.http import HttpRequest
from django.template import RequestContext

from kooplex.hub.models import *
from kooplex.logic.spawner import spawn_project_container, stop_project_container
from kooplex.logic import create_project, delete_project, configure_project
from kooplex.logic import Repository

logger = logging.getLogger(__name__)

def projects(request):
    """Renders the projectlist page."""
    assert isinstance(request, HttpRequest)
    if request.user.is_anonymous():
        logger.debug('User not authenticated yet --> goes to login page')
        return redirect('login')
    try:
        PUBLIC = ScopeType.objects.get(name = 'public')
        NOTEBOOK = ContainerType.objects.get(name = 'notebook')
    except ScopeType.DoesNotExist:
        return redirect('/admin')
    except ContainerType.DoesNotExist:
        return redirect('/admin')
    user = request.user
    projects_mine = Project.objects.filter(owner = user)
    projects_sharedwithme = sorted([ upb.project for upb in UserProjectBinding.objects.filter(user = user) ])
    projects_public = sorted(Project.objects.filter(scope = PUBLIC).exclude(owner = user))
    running = [ c.project for c in Container.objects.filter(user = user, is_running = True, container_type = NOTEBOOK) ]
    stopped = [ c.project for c in Container.objects.filter(user = user, is_running = False, container_type = NOTEBOOK) ]
    users = sorted(User.objects.all())
    images = Image.objects.all()
    scopes = ScopeType.objects.all()
    functional_volumes = FunctionalVolume.objects.all()
    storage_volumes = StorageVolume.objects.all()
    logger.debug('Rendering projects.html')
    return render(
        request,
        'project/projects.html',
        context_instance = RequestContext(request,
        {
            'user': user,
            'projects_mine': projects_mine,
            'projects_shared': projects_sharedwithme,
            'projects_public': projects_public,
            'running': running,
            'stopped': stopped,
            'users': users,
            'images' : images,
            'scopes' : scopes,
            'functional_volumes': functional_volumes,
            'storage_volumes': storage_volumes,
        })
    )


def project_new(request):
    """Handles the creation of a new project."""
    assert isinstance(request, HttpRequest)
    if request.user.is_anonymous():
        return redirect('login')
    user = request.user
    name = request.POST['project_name'].strip()
    description = request.POST['project_description'].strip()
    button = request.POST['button']
    if button == 'Cancel':
        return redirect('projects')
    template = request.POST.get('project_template')
    volumes = [ FunctionalVolume.objects.get(name = x) for x in request.POST.getlist('func_volumes') ]
    volumes.extend( [ StorageVolume.objects.get(name = x) for x in request.POST.getlist('storage_volumes') ] )
    logger.debug('New project to be created: %s' % name)
    stop = False
    if not re.match(r'^[a-zA-Z][0-9a-zA-Z_-]*$', name):
        messages.error(request, 'For project name specification please use only Upper/lower case letters, hyphens and underscores.')
        stop = True
    if not re.match(r'^[0-9a-zA-Z_ -]*$', description):
        messages.error(request, 'In your project description use only Upper/lower case letters, hyphens, spaces and underscores.')
        stop = True
    if stop:
        return redirect('projects')
        
    if template.startswith('clonable_project='):
        messages.error(request, 'Not implemented error. Wait for the code maintainers...')
        return redirect('projects')
        raise NotImplementedError
#FIXME:
#        name, owner = template.split('=')[-1].split('@')
#        project = Project.objects.get(name = name, owner_username = owner)
#        project_image_name = project.image
#        # Retrieve former_shares and unify with users current choices
#        for mpb in MountPointProjectBinding.objects.filter(project = project):
#            mp.append(mpb.id)
#        mp = list(set(mp))
#        # Retrieve former_volumes and unify with users current choices
#        for vpb in VolumeProjectBinding.objects.filter(project = project):
#            vols.append(vpb.volume)
#        vols = list(set(vols))
#        cloned_project = True
    elif template.startswith('image='):
        imagename = template.split('=')[-1]
        logger.debug('Project to be created from image: %s' % imagename)
        cloned_project = False
    scope = ScopeType.objects.get(name = button)
    image = Image.objects.get(name = imagename)
    project = Project(name = name, owner = user, description = description, image = image, scope = scope)
    # NOTE: create_project takes good care of saving the new project instance
    try:
       create_project(project, volumes)
    except AssertionError:
        messages.error(request, 'Could not create project!. Wait for the administrator to respond!' )
        logger.error('Could not create project %s for user %s' % (name, user.username) )
        return redirect('projects')
    logger.debug('New project saved in HubDB: %s' % name)
    return redirect('projects')
#FIXME: 
###### Create a magic script to clone ancient projects content
#####            ancientprojecturl = "ssh://git@%s/%s.git" % (get_settings('gitlab', 'ssh_host'), project.path_with_namespace)
#####            commitmsg = "Snapshot commit of project %s" % project
#####            script = """#! /bin/bash
#####TMPFOLDER=$(mktemp -d)
#####git clone %(url)s ${TMPFOLDER}
#####cd ${TMPFOLDER}
#####rm -rf ./.git/
#####mv * ~/git/
#####for hidden in $(echo .?* | sed s/'\.\.'//) ; do
#####  mv $hidden ~/git
#####done
#####cd ~/git
#####git add --all
#####git commit -a -m "%(message)s"
#####git push origin master
#####rm -rf ${TMPFOLDER}
#####rm ~/$(basename $0)
#####            """ % { 'url': ancientprojecturl, 'message': commitmsg }
#####            home_dir = os.path.join(get_settings('volumes', 'home'), p.owner_username)
#####            fn_basename = ".gitclone-%s.sh" % p.name
#####            fn_script = os.path.join(home_dir, fn_basename)
#####            open(fn_script, 'w').write(script)
#####            os.chmod(fn_script, 0b111000000)
#####            hubuser = HubUser.objects.get(username = p.owner_username)
#####            os.chown(fn_script, int(hubuser.uid), int(hubuser.gid))
#####        else:
###### Create a README file
#####            g.create_project_readme(p.id, "README.md", "* proba", "Created a default README")
#####        return HttpResponseRedirect(HUB_NOTEBOOKS_URL)
#####    except Exception as e:
#####        return render(
#####            request,
#####            'app/error.html',
#####            context_instance=RequestContext(request,
#####                                            {
#####                                                'error_title': 'Error',
#####                                                'error_message': str(e),
#####                                            })
#####        )


def project_configure(request):
    """Handles the project configuration."""
    assert isinstance(request, HttpRequest)
    if request.user.is_anonymous():
        return redirect('login')
    if request.method != 'POST':
        return redirect('projects')
    button = request.POST['button']
    project_id = request.POST['project_id']
    try:
        project = Project.objects.get(id = project_id, owner = request.user)
    except Project.DoesNotExist:
        messages.error(request, 'Project does not exist')
        return redirect('projects')
    if button == 'delete':
        delete_project(project)
    elif button == 'apply':
        collaborators = [ User.objects.get(id = x) for x in request.POST.getlist('collaborators') ]
        volumes = [ FunctionalVolume.objects.get(name = x) for x in request.POST.getlist('func_volumes') ]
        volumes.extend( [ StorageVolume.objects.get(name = x) for x in request.POST.getlist('storage_volumes') ] )
        image = Image.objects.get(name = request.POST['project_image'])
        scope = ScopeType.objects.get(name = request.POST['project_scope'])
        configure_project(project, image, scope, volumes, collaborators)
    return redirect('projects')


def project_start(request):
    """Starts. the project container."""
    assert isinstance(request, HttpRequest)
    if request.user.is_anonymous():
        return redirect('login')
    try:
        project_id = request.GET['project_id']
        project = Project.objects.get(id = project_id)
        if project.owner != request.user:
            UserProjectBinding(user = request.user, project = project)
        spawn_project_container(request.user, project)
    except KeyError:
        return redirect('/')
    except Project.DoesNotExist:
        messages.error(request, 'Project does not exist')
    except UserProjectBinding.DoesNotExist:
        messages.error(request, 'You are not authorized to start that project')
    return redirect('projects')


def project_open(request):
    """Opens the project container."""
    assert isinstance(request, HttpRequest)
    if request.user.is_anonymous():
        return redirect('login')
    user = request.user
    project_id = request.GET['project_id']
    try:
        project = Project.objects.get(id = project_id)
        container = Container.objects.get(user = user, project = project, is_running = True)
        return redirect(container.url_with_token)
    except Project.DoesNotExist:
        messages.error(request, 'Project does not exist')
    except Container.DoesNotExist:
        messages.error(request, 'Project container is missing or stopped')
    return redirect('projects')


def project_stop(request):
    """Stops project and delete container."""
    assert isinstance(request, HttpRequest)
    if request.user.is_anonymous():
        return redirect('login')
    user = request.user
    project_id = request.GET['project_id']
    try:
        project = Project.objects.get(id = project_id)
        container = Container.objects.get(user = user, project = project, is_running = True)
        stop_project_container(container)
    except Project.DoesNotExist:
        messages.error(request, 'Project does not exist')
    except Container.DoesNotExist:
        messages.error(request, 'Project container is already stopped or is missing')
    return redirect('projects')

def project_versioning(request):
    """Handles the git."""
    assert isinstance(request, HttpRequest)
    if request.user.is_anonymous():
        return redirect('login')
    if request.method != 'GET':
        return redirect('projects')
    user = request.user
    try:
        project = Project.objects.get(id = request.GET.get('project_id', -1))
        if project.owner != user and not user in project.collaborators:
            messages.error(request, 'You are not allowed to version control this project')
            return redirect('projects')
        repo = Repository(user, project)
        git_log = repo.log()
        git_files = repo.lsfiles()
        git_changed = repo.remote_changed()
        logger.debug('Rendering gitform.html')
        return render(
            request,
            'project/gitform.html',
            context_instance=RequestContext(request,
            {
                'project': project,
                'committable_dict' : git_files,
                'commits' : git_log,
                'changedremote': git_changed,
            })
        )
    except Project.DoesNotExist:
        messages.error(request, 'Project does not exist')
        return redirect('projects')


def project_versioning_commit(request):
    """Handles the git."""
    assert isinstance(request, HttpRequest)
    if request.user.is_anonymous():
        return redirect('login')
    if request.method != 'POST':
        return redirect('projects')
    if request.POST['button'] == 'Cancel':
        return redirect('projects')
    user = request.user
    try:
        project = Project.objects.get(id = request.POST['project_id'])
        if project.owner != user and not user in project.collaborators:
            messages.error(request, 'You are not allowed to version control this project')
            return redirect('projects')
        message = request.POST['message']
        repo = Repository(request.user, project)
        repo.add( request.POST.getlist('modified_files') )
        repo.add( request.POST.getlist('other_files') )
        repo.remove( request.POST.getlist('deleted_files') )
        repo.commit(message)
        repo.push()
        return redirect('projects')
    except Exception as e:
        msg = "Unhandled exception -- %s" % e
        messages.error(request, msg)
        logger.error(msg)
    return redirect('projects')


def project_versioning_revert(request):
    """Handles the git."""
    assert isinstance(request, HttpRequest)
    if request.user.is_anonymous():
        return redirect('login')
    if request.method != 'POST':
        return redirect('projects')
    if request.POST['button'] == 'Cancel':
        return redirect('projects')
    user = request.user
    try:
        project = Project.objects.get(id = request.POST['project_id'])
        if project.owner != user and not user in project.collaborators:
            messages.error(request, 'You are not allowed to version control this project')
            return redirect('projects')
        commitid = request.POST['commitid']
        repo = Repository(request.user, project)
        repo.revert(commitid)
        return redirect('projects')
    except Exception as e:
        msg = "Unhandled exception -- %s" % e
        messages.error(request, msg)
        logger.error(msg)
    return redirect('projects')


def project_versioning_pull(request):
    """Handles the git."""
    assert isinstance(request, HttpRequest)
    if request.user.is_anonymous():
        return redirect('login')
    if request.method != 'POST':
        return redirect('projects')
    if request.POST['button'] == 'Cancel':
        return redirect('projects')
    user = request.user
    try:
        project = Project.objects.get(id = request.POST['project_id'])
        if project.owner != user and not user in project.collaborators:
            messages.error(request, 'You are not allowed to version control this project')
            return redirect('projects')
        repo = Repository(request.user, project)
        repo.pull()
        return redirect('projects')
    except Exception as e:
        msg = "Unhandled exception -- %s" % e
        messages.error(request, msg)
        logger.error(msg)
    return redirect('projects')



urlpatterns = [
    url(r'^/?$', projects, name = 'projects'),
    url(r'^/new$', project_new, name = 'project-new'), 
    url(r'^/configure$', project_configure, name = 'project-settings'), 
    url(r'^/versioncontrol$', project_versioning, name = 'project-versioncontrol'), 
    url(r'^/versioncontrol/commit$', project_versioning_commit, name = 'project-commit'), 
    url(r'^/versioncontrol/revert$', project_versioning_revert, name = 'project-revert'), 
    url(r'^/versioncontrol/pull$', project_versioning_pull, name = 'project-pull'), 
    url(r'^/start$', project_start, name = 'container-start'), 
    url(r'^/open$', project_open, name = 'container-open'), 
    url(r'^/stop$', project_stop, name = 'container-delete'), 
]

