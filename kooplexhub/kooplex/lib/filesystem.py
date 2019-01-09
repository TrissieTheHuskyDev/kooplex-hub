"""
@autor: Jozsef Steger
@summary: file and directory operations
"""
import re
import logging
import os
import ast
import time
import glob
import base64
from distutils import dir_util
from distutils import file_util
import tarfile

from kooplex.lib import bash, Dirname, Filename

logger = logging.getLogger(__name__)

def _mkdir(path, uid = 0, gid = 0, mode = 0b111101000, mountpoint = False):
    """
    @summary: make directory, set ownership and mode. (A helper method)
    @param path: the directory to make
    @type path: str
    @param uid: filesystem level user id, default 0
    @type uid: int
    @param gid: filesystem level group id, default 0
    @type gid: int
    @param mode: filesystem access flags (9 bits), default 0b111101000
    @type mode: int
    @param mountpoint: whether the created directory is to be used as a mount point, default False
    @type mountpoint: bool
    """
    logger.debug("dir: %s uid/gid: %d/%d; mountpoint: %s" % (path, uid, gid, mountpoint))
    dir_util.mkpath(path)
    os.chown(path, uid, gid)
    os.chmod(path, mode)
    if mountpoint:
        placeholder = os.path.join(path, '_not_mounted_')
        open(placeholder, 'w').close()
        os.chown(placeholder, 0, 0)
        os.chmod(placeholder, 0)

def _archivedir(folder, target, remove = True):
    if not os.path.exists(folder):
        logger.warning("Folder %s is missing" % folder)
        return
    try:
        assert len(os.listdir(folder)) > 0, "Folder %s is empty" % folder
        dir_util.mkpath(os.path.dirname(target))
        with tarfile.open(target, mode='w:gz') as archive:
            archive.add(folder, arcname = '.', recursive = True)
            logger.debug("tar %s -> %s" % (folder, target))
    except Exception as e:
        logger.error("Cannot create archive %s -- %s" % (folder, e))
    finally:
        if remove:
            dir_util.remove_tree(folder)
            logger.debug("Folder %s removed" % folder)


########################################

def mkdir_home(user):
    """
    @summary: create a home directory for the user
    @param user: the user
    @type user: kooplex.hub.models.User
    """
    dir_home = Dirname.userhome(user)
    _mkdir(dir_home, uid = user.profile.userid, gid = user.profile.groupid)

def garbagedir_home(user):
    dir_home = Dirname.userhome(user)
    garbage = Filename.userhome_garbage(user)
    _archivedir(dir_home, garbage)


def mkdir_share(userprojectbinding):
    project = userprojectbinding.project
    dir_share = Dirname.share(userprojectbinding)
    _mkdir(dir_share, uid = project.fs_uid, gid = project.fs_gid)

def garbagedir_share(userprojectbinding):
    dir_share = Dirname.share(userprojectbinding)
    garbage = Filename.share_garbage(userprojectbinding)
    _archivedir(dir_share, garbage)


def mkdir_workdir(userprojectbinding):
    dir_workdir = Dirname.workdir(userprojectbinding)
    _mkdir(dir_workdir, uid = userprojectbinding.user.profile.userid, gid = userprojectbinding.user.profile.groupid)

def archivedir_workdir(userprojectbinding):
    dir_workdir = Dirname.workdir(userprojectbinding)
    target = Filename.workdir_archive(userprojectbinding)
    _archivedir(dir_workdir, target)


def mkdir_vcpcache(vcprojectprojectbinding):
    profile = vcprojectprojectbinding.vcproject.token.user.profile
    dir_cache = Dirname.vcpcache(vcprojectprojectbinding)
    _mkdir(dir_cache, uid = profile.userid, gid = profile.groupid)

def archivedir_vcpcache(vcprojectprojectbinding):
    dir_cache = Dirname.vcpcache(vcprojectprojectbinding)
    target = Filename.vcpcache_archive(vcprojectprojectbinding)
    _archivedir(dir_cache, target)


########################################

def mkdir_course_share(course):
    try:
        dir_courseprivate = Dirname.courseprivate(course)
        _mkdir(dir_courseprivate, gid = course.groupid, mode = 0o770)
        dir_coursepublic = Dirname.coursepublic(course)
        _mkdir(dir_coursepublic, gid = course.groupid, mode = 0o750)
        logger.info("Course dir created for course %s" % course)
    except KeyError as e:
        logger.error("Cannot create course dir, KOOPLEX['mountpoint']['course'] is missing")

def grantacl_course_share(usercoursebinding):
    try:
        dir_coursepublic = Dirname.coursepublic(usercoursebinding.course)
        if usercoursebinding.is_teacher:
            bash("setfacl -R -m u:%d:rwX %s" % (usercoursebinding.user.profile.userid, dir_coursepublic))
        logger.debug("acl granted %s" % usercoursebinding)
    except Exception as e:
        logger.error("Cannot grant acl %s -- %s" % (usercoursebinding, e))

def revokeacl_course_share(usercoursebinding):
    try:
        dir_coursepublic = Dirname.coursepublic(usercoursebinding.course)
        if usercoursebinding.is_teacher:
            bash("setfacl -R -x u:%d %s" % (usercoursebinding.user.profile.userid, dir_coursepublic))
        logger.debug("acl revoked %s" % usercoursebinding)
    except Exception as e:
        logger.error("Cannot revoke acl %s -- %s" % (usercoursebinding, e))

def garbagedir_course_share(course):
    dir_course = Dirname.course(course)
    garbage = Filename.course_garbage(course)
    _archivedir(dir_course, garbage)

def mkdir_course_workdir(usercoursebinding):
    try:
        dir_usercourse = Dirname.courseworkdir(usercoursebinding)
        uid = 0 if usercoursebinding.is_teacher else usercoursebinding.user.profile.userid
        _mkdir(dir_usercourse, uid = uid, gid = usercoursebinding.course.groupid, mode = 0o770)
    except KeyError as e:
        logger.error("Cannot create course dir, KOOPLEX['mountpoint']['usercourse'] is missing")

def grantacl_course_workdir(usercoursebinding):
    try:
        if usercoursebinding.is_teacher:
            dir_usercourse = Dirname.courseworkdir(usercoursebinding)
            bash("setfacl -R -m u:%d:rwX %s" % (usercoursebinding.user.profile.userid, dir_usercourse))
    except Exception as e:
        logger.error("Cannot grant acl %s -- %s" % (usercoursebinding, e))

def revokeacl_course_workdir(usercoursebinding):
    try:
        if usercoursebinding.is_teacher:
            dir_usercourse = Dirname.courseworkdir(usercoursebinding)
            bash("setfacl -R -x u:%d %s" % (usercoursebinding.user.profile.userid, dir_usercourse))
    except Exception as e:
        logger.error("Cannot revoke acl %s -- %s" % (usercoursebinding, e))

def archive_course_workdir(usercoursebinding):
    if usercoursebinding.is_teacher:
        return
    dir_usercourse = Dirname.courseworkdir(usercoursebinding)
    archive = Filename.courseworkdir_archive(usercoursebinding)
    _archivedir(dir_usercourse, archive)


def rmdir_course_workdir(course):
    try:
        dir_usercourse = Dirname.course(course)
        dir_util.remove_tree(dir_usercourse)
    except KeyError as e:
        logger.error("Cannot remove course dir, KOOPLEX['mountpoint']['usercourse'] is missing")
    except Exception as e:
        logger.error("Cannot remove course %s workdir -- %s" % (course, e))

def snapshot_assignment(assignment):
    dir_source = Dirname.assignmentsource(assignment)
    archive = Filename.assignmentsnapshot(assignment)
    _archivedir(dir_source, archive, remove = False)

def garbage_assignmentsnapshot(assignment):
    try:
        archive = Filename.assignmentsnapshot(assignment)
        garbage = Filename.assignmentsnapshot_garbage(assignment)
        file_util.move_file(archive, garbage)
    except Exception as e:
        logger.error("move %s -> %s fails -- %s" % (archive, garbage, e))

def cp_assignmentsnapshot(userassignmentbinding):
    try:
        archivefile = Filename.assignmentsnapshot(userassignmentbinding.assignment)
        dir_target = Dirname.assignmentworkdir(userassignmentbinding)
        with tarfile.open(archivefile, mode='r') as archive:
            archive.extractall(path = dir_target)
        bash("setfacl -R -m u:%d:rwX %s" % (userassignmentbinding.user.profile.userid, dir_target))
    except Exception as e:
        logger.error("Cannot cp snapshot dir %s -- %s" % (userassignmentbinding, e))

def cp_userassignment(userassignmentbinding):
    dir_source = Dirname.assignmentworkdir(userassignmentbinding)
    archive = Filename.assignmentcollection(userassignmentbinding)
    _archivedir(dir_source, archive, remove = False)
        #bash("chmod -R 0 %s" % dir_target)
        #bash("setfacl -R -m u:%d:rX %s" % (userassignmentbinding.user.profile.userid, dir_target))

def cp_userassignment2correct(userassignmentbinding):
    try:
        archivefile = Filename.assignmentcollection(userassignmentbinding)
        dir_target = Dirname.assignmentcorrectdir(userassignmentbinding)
        with tarfile.open(archivefile, mode='r') as archive:
            archive.extractall(path = dir_target)
#        bash("chmod -R 0 %s" % dir_target)
        bash("setfacl -R -m u:%d:rwX %s" % (userassignmentbinding.corrector.profile.userid, dir_target))
    except Exception as e:
        logger.error("Cannot copy correct dir %s -- %s" % (userassignmentbinding, e))

def manageacl_feedback(userassignmentbinding):
    try:
        dir_target = Dirname.assignmentcorrectdir(userassignmentbinding)
#        bash("setfacl -R -x u:%d %s" % (userassignmentbinding.corrector.profile.userid, dir_target))
#        bash("setfacl -R -m u:%d:rX %s" % (userassignmentbinding.corrector.profile.userid, dir_target))
        bash("setfacl -R -m u:%d:rX %s" % (userassignmentbinding.user.profile.userid, dir_target))
    except Exception as e:
        logger.error("Cannot revoke acl from feedback dir %s -- %s" % (userassignmentbinding, e))

