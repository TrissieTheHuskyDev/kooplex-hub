import logging
import os
import json
from kubernetes import client, config
from urllib.parse import urlparse

from kooplex.lib import now
from kooplex.settings import KOOPLEX
from .proxy import addroute, removeroute

logger = logging.getLogger(__name__)

def start(service):
    spawner_conf = KOOPLEX.get('spawner', {})
    mount_point = spawner_conf.get('volume_mount', '/mnt')
    project_subdir = spawner_conf.get('project_subdir', 'project')
    report_subdir = spawner_conf.get('report_subdir', 'report')
    report_prepare_subdir = spawner_conf.get('report_prepare_subdir', 'report_prepare')

    config.load_kube_config()
    v1 = client.CoreV1Api()

    pod_ports = []
    svc_ports = []
    env_variables = [
        { "name": "LANG", "value": "en_US.UTF-8" },
        { "name": "PREFIX", "value": "k8plex" },
        { "name": "SSH_AUTH_SOCK", "value": f"/tmp/{service.user.username}" },
    ]
    for env in service.env_variables:
        env_variables.append(env)
    for proxy in service.proxies:
        pod_ports.append({
            "containerPort": proxy.port,
            "name": "http", 
        })
        svc_ports.append({
            "port": proxy.port,
            "targetPort": proxy.port,
            "protocol": "TCP",
        })
    volumes = []
    volume_mounts = []
    if service.image.require_home:
        volumes.append({
            "name": "pv-k8plex-hub-home",
            "persistentVolumeClaim": { "claimName": "pvc-home-k8plex", }
        })
        volume_mounts.append({
            "name": "pv-k8plex-hub-home",
            "mountPath": os.path.join(mount_point, service.user.username),
            "subPath": service.user.username,
        })
    has_project = False
    has_report = False
    has_cache = False

    if service.image.mount_project:
        for project in service.projects:
            volume_mounts.append({
                "name": "pv-k8plex-hub-project",
                "mountPath": os.path.join(mount_point, project_subdir, project.uniquename),
                "subPath": project.uniquename
            })
            has_project = True

    if service.image.mount_report:
        for project in service.projects:
            volume_mounts.append({
                "name": "pv-k8plex-hub-report",
                "mountPath": os.path.join(mount_point, report_subdir, project.uniquename),
                "subPath": project.uniquename,
                "readOnly": True
            })
            has_report = True
            volume_mounts.append({
                "name": "pv-k8plex-hub-cache",
                "mountPath": os.path.join(mount_point, report_prepare_subdir, project.uniquename),
                "subPath": project.uniquename
            })
            has_cache = True

    for sync_lib in service.synced_libraries:
        o = urlparse(sync_lib.token.syncserver.url)
        server = o.netloc.replace('.', '_')
        volume_mounts.append({
            "name": "pv-k8plex-hub-cache",
            "mountPath": os.path.join(mount_point, 'synchron', f'{sync_lib.library_name}-{server}'),
            "subPath": os.path.join('fs', service.user.username, server, 'synchron', sync_lib.library_name),
        })
        has_cache = True

    for repo in service.repos:
        o = urlparse(repo.token.repository.url)
        server = o.netloc.replace('.', '_')
        volume_mounts.append({
            "name": "pv-k8plex-hub-cache",
            "mountPath": os.path.join(mount_point, 'git', f'{repo.clone_folder}-{server}'),
            "subPath": os.path.join('git', service.user.username, server, repo.clone_folder),
        })
        has_cache = True

    if has_project:
        volumes.append({
            "name": "pv-k8plex-hub-project",
            "persistentVolumeClaim": { "claimName": "pvc-project-k8plex", }
        })

    if has_report:
        volumes.append({
            "name": "pv-k8plex-hub-report",
            "persistentVolumeClaim": { "claimName": "pvc-report-k8plex", }
        })
    
    if has_cache:
        volumes.append({
            "name": "pv-k8plex-hub-cache",
            "persistentVolumeClaim": { "claimName": "pvc-cache-k8plex", }
        })

    pod_definition = {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {
                "name": service.label,
                "namespace": "default",
                "labels": { "lbl": f"lbl-{service.label}", }
            },
            "spec": {
                "containers": [{
                    "name": service.label,
                    "image": service.image.name,
                    "volumeMounts": volume_mounts,
                    "ports": pod_ports,
                    "imagePullPolicy": "IfNotPresent",
                    "env": env_variables,
                }],
                "volumes": volumes,
            }
        }

    svc_definition = {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "name": service.label,
            },
            "spec": {
                "selector": {
                    "lbl": f"lbl-{service.label}",
                    },
                "ports": svc_ports,
            }
        }

    try:
        msg = v1.create_namespaced_service(namespace = "default", body = svc_definition)
        logger.debug(msg)
    except client.rest.ApiException as e:
        logger.warning(e)
        if json.loads(e.body)['code'] != 409: # already exists
            logger.debug(svc_definition)
            raise
    try:
        msg = v1.create_namespaced_pod(namespace = "default", body = pod_definition)
        logger.debug(msg)
    except client.rest.ApiException as e:
        logger.warning(e)
        if json.loads(e.body)['code'] != 409: # already exists
            logger.debug(pod_definition)
            raise
    service.state = service.ST_RUNNING
    service.save()
    addroute(service)

def stop(service):
    config.load_kube_config()
    v1 = client.CoreV1Api()
    removeroute(service)
    try:
        msg = v1.delete_namespaced_pod(namespace = "default", name = service.label)
        logger.debug(msg)
    except client.rest.ApiException as e:
        logger.warning(e)
        if json.loads(e.body)['code'] != 404: # doesnt exists
            raise
    try:
        msg = v1.delete_namespaced_service(namespace = "default", name = service.label)
        logger.debug(msg)
    except client.rest.ApiException as e:
        logger.warning(e)
        if json.loads(e.body)['code'] != 404: # doesnt exists
            raise
    service.state = service.ST_NOTPRESENT
    service.save()

def check(service):
    config.load_kube_config()
    v1 = client.CoreV1Api()
    try:
        msg = v1.read_namespaced_pod_log(namespace='default', name = service.label)
        logger.debug(msg)
        try:
            msg_extract = json.loads(msg)
            message = msg['message']
        except json.decoder.JSONDecodeError:
            msg = msg.splitlines()
            while True:
                message = msg.pop().strip()
                if message:
                    break
    except client.rest.ApiException as e:
        e_extract = json.loads(e.body)
        message = e_extract['message']
        if service.state in [ service.ST_RUNNING, service.ST_NEED_RESTART ]:
            service.state = service.ST_ERROR
        logger.warning(e)
    finally:
        service.last_message = message
        service.last_message_at = now()
        service.save()