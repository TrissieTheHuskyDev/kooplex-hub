from django import forms
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
import django_tables2 as tables

from hub.models import VCRepository
from hub.models import VCToken
from hub.models import VCProject
from hub.models import VCProjectProjectBinding 

class ReposColumn(tables.Column):
    def render(self, record):
        repo = record.token.repository
        if repo.backend_type == repo.TP_GITHUB:
            return format_html('<img src="/static/content/logos/github.png" alt="github" width="30px" data-toggle="tooltip" title="{}" data-placement="bottom">'.format(repo.url))
        elif repo.backend_type == repo.TP_GITLAB:
            return format_html('<img src="/static/content/logos/gitlab.png" alt="gitlab" width="30px" data-toggle="tooltip" title="{}" data-placement="bottom">'.format(repo.url))
        elif repo.backend_type == repo.TP_GITEA:
            return format_html('<img src="/static/content/logos/gitea.png" alt="gitea" width="30px" data-toggle="tooltip" title="{}" data-placement="bottom">'.format(repo.url))
        else:
            return format_html(record)

class T_REPOSITORY_CLONE(tables.Table):
    id = tables.Column(verbose_name = 'Status', orderable = False)
    repos = ReposColumn(verbose_name = 'Src', empty_values = (), orderable = False)
    def render_id(self, record):
        if record.cloned:
            return format_html('<input type="checkbox" data-toggle="toggle" name="removecache" value="{}" data-on="Remove" data-off="Cloned" data-onstyle="danger" data-offstyle="success" data-size="xs"'.format(record.id))
        else:
            return format_html('<input type="checkbox" data-toggle="toggle" name="clone" value="{}" data-on="Clone" data-off="Unused" data-onstyle="success" data-offstyle="secondary" data-size="xs">'.format(record.id))
    def render_project_name(self, record):
        return format_html('<span data-toggle="tooltip" title="{}" data-placement="bottom">{} of {}</span>'.format(record.project_description, record.project_name, record.project_owner))
    class Meta:
        model = VCRepository
        fields = ('id', 'repos', 'project_name', 'project_created_at')
        sequence = ('id', 'repos', 'project_name', 'project_created_at')
        attrs = { "class": "table-striped table-bordered", "td": { "style": "padding:.5ex" } }

def s_column(project):
    lookup = dict([ (b.vcproject, b.id) for b in VCProjectProjectBinding.objects.filter(project = project) ])
    class SelectColumn(tables.Column):
        def render(self, record):
            if record in lookup.keys():
                return format_html('<input type="hidden" name="vcppb_ids_before" value="{0}"><input type="checkbox" name="vcppb_ids_after" value="{0}" checked data-toggle="toggle" data-on="Attached" data-off="Detach" data-onstyle="success" data-offstyle="dark" data-size="xs">'.format(lookup[record]))
            else:
                return format_html('<input type="checkbox" name="vcp_ids" data-toggle="toggle" value="{}" data-on="Attach" data-off="Unused" data-onstyle="success" data-offstyle="dark" data-size="xs">'.format(record.id))
    return SelectColumn

class ProjectsColumn(tables.Column):
    def render(self, record):
        return format_html(",".join(map(lambda b: str(b.project), record.vcprojectprojectbindings)))


def table_vcproject(project):
    sc = s_column(project)
    class T_VCPROJECT(tables.Table):
        id = sc(verbose_name = 'status', orderable = False)
        projects = ProjectsColumn(verbose_name = 'Bound to projects', empty_values = (), orderable = False)

        class Meta:
            model = VCProject
            fields = ('id', 'repository', 'projects')
            sequence = ('id', 'repository', 'projects')
            attrs = { "class": "table-striped table-bordered", "td": { "style": "padding: 5px 10px 5px 15px" } }

    return T_VCPROJECT


def table_vctoken(user):
    tokens = [ t for t in user.profile.vctokens ]
    repos = [ t.repository for t in tokens ]
    for r in VCRepository.objects.all():
        if not r in repos:
            tokens.append( VCToken(repository = r, user = user) )
 
    class T_VCTOKEN(tables.Table):
        id = tables.Column(verbose_name = 'Job', empty_values = ())
        username = tables.Column(verbose_name = 'Registered username', empty_values = ())
        token = tables.Column(empty_values = ())
        fn_rsa = tables.Column(empty_values = ())

        def render_id(self, record):
            if record.id:
                return format_html("<input type='hidden' name='token_ids' value='%s'><input type='checkbox' name='rm_token_ids' value='%s'> Delete" % (record.id, record.id))
            else:
                return format_html("<input type='checkbox' name='new_repository_ids' value='%s'> New" % (record.repository.id))

        def render_token(self, record):
            if record.id:
                return format_html("<input type='hidden' name='token_before-%d' value='%s'><input type='password' name='token_after-%d' value='%s'>" % (record.id, record.token, record.id, record.token))
            else:
                return format_html("<input type='password' name='token-%d' value='' placeholder='Paste your token'>" % (record.repository.id))

        def render_fn_rsa(self, record):
            if record.id:
                return format_html("<input type='hidden' name='fn_rsa_before-%d' value='%s'><input type='text' name='fn_rsa_after-%d' value='%s'>" % (record.id, record.fn_rsa, record.id, record.fn_rsa))
            else:
                return format_html("<input type='text' name='fn_rsa-%d' value='' placeholder='Filename in .ssh folder'>" % (record.repository.id))

        def render_username(self, record):
            if record.id:
                return format_html("<input type='hidden' name='username_before-%d' value='%s'><input type='text' name='username_after-%d' value='%s'>" % (record.id, record.username, record.id, record.username))
            else:
                return format_html("<input type'text' name='username-%d' value='%s'>" % (record.repository.id, user.username))

        class Meta:
            model = VCToken
            orderable = False
            fields = ('id', 'repository', 'username', 'fn_rsa', 'token', 'last_used', 'error_flag')
#            sequence = ('id', 'repository', 'projects')
            attrs = { "class": "table-striped table-bordered", "td": { "style": "padding:.5ex" } }

    return T_VCTOKEN(tokens)
