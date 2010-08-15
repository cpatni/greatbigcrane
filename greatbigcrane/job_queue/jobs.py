"""
Copyright 2010 Jason Chu, Dusty Phillips, and Phil Schalm

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import zmq
import json
import subprocess
from project.models import Project
from notifications.models import Notification

addr = 'tcp://127.0.0.1:5555'

# FIXME: I have no idea if this is threadsafe
context = zmq.Context()
socket = context.socket(zmq.REQ)
socket.connect(addr)

def queue_job(command, **kwargs):
    '''Run the given command on the job queue, passing it any arguments as kwargs.'''
    assert command in command_map
    kwargs.update(command=command)
    serialized = json.dumps(kwargs)
    socket.send(serialized)
    assert socket.recv() == "ACK"

# Create the actual commands here and keep the command_map below up to date
def bootstrap(project_id):
    '''Run the bootstrap process inside the given project's base directory.'''
    print("running bootstrap %s" % project_id)
    project = Project.objects.get(id=project_id)
    process = subprocess.Popen(["python", "bootstrap.py"], cwd=project.base_directory,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    response = process.communicate()[0]

    Notification.objects.create(status="success" if not process.returncode else "error",
            summary="Bootstrapping '%s' %s" % (
                project.name, "success" if not process.returncode else "error"),
            message=response,
            project=project)

def buildout(project_id):
    print("running buildout %s" % project_id)
    project = Project.objects.get(id=project_id)
    process = subprocess.Popen("bin/buildout", cwd=project.base_directory,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    response = process.communicate()[0]

    Notification.objects.create(status="success" if not process.returncode else "error",
            summary="Buildouting '%s' %s" % (
                project.name, "success" if not process.returncode else "error"),
            message=response,
            project=project)

def test_buildout(project_id):
    print("running tests for %s" % project_id)
    project = Project.objects.get(id=project_id)

    bc = buildout_parse(project.buildout_filename())

    test_binaries = []

    parts = bc['buildout']['parts']
    if not isinstance(parts, list):
        parts = [parts]

    # We get to do some detection in this one
    # First look for django test
    for section, values in bc.iteritems():
        if section in parts:
            if values.get('recipe') == 'djangorecipe':
                # Django, we know what's going on
                test_script = section
                if 'control-script' in values:
                    test_script = values['control-script']
                test_binaries.append(['bin/' + test_script, 'test'])

    errors = False
    responses = []
    for binary in test_binaries:
        process = subprocess.Popen(binary, cwd=project.base_directory,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        responses.append(process.communicate()[0])
        errors = errors or process.returncode != 0

    # FIXME: Make the output a little nicer when you run multiple test suites

    Notification.objects.create(status="success" if not errors else "error",
            summary="Testing '%s' %s" % (
                project.name, "success" if not errors else "error"),
            message=('\n\n'+'*'*50+'\n\n').join(responses),
            project=project)
    if not errors:
        # TODO: Potential for race condition?
        
        project.test_status = True
        project.save()

def clone_repo(project_id):
    from greatbigcrane.job_queue.jobs import queue_job
    print("cloning repo for %s" % project_id)
    project = Project.objects.get(id=project_id)

    process = subprocess.Popen(['git', 'clone', project.git_repo, project.base_directory], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    response = process.communicate()[0]

    Notification.objects.create(status="success" if not process.returncode else "error",
            summary="Cloning '%s' %s" % (
                project.name, "success" if not process.returncode else "error"),
            message=response,
            project=project)

    queue_job('BOOTSTRAP', project_id=project_id)

def pull_repo(project_id):
    print("pulling repo for %s" % project_id)
    project = Project.objects.get(id=project_id)

    process = subprocess.Popen(['git', 'pull'], cwd=project.base_directory,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    response = process.communicate()[0]

    Notification.objects.create(status="success" if not process.returncode else "error",
            summary="Pulling '%s' %s" % (
                project.name, "success" if not process.returncode else "error"),
            message=response,
            project=project)

# Django commands
def syncdb(project_id):
    project = Project.objects.get(id=project_id)
    print("running syncdb for %s" % project.name)

    process = subprocess.Popen(['bin/django', 'syncdb'], cwd=project.base_directory,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    response = process.communicate()[0]

    Notification.objects.create(status="success" if not process.returncode else "error",
            summary="Syncdb '%s' %s" % (
                project.name, "success" if not process.returncode else "error"),
            message=response,
            project=project)



command_map = {
    'BOOTSTRAP': bootstrap,
    'BUILDOUT': buildout,
    'TEST': test_buildout,
    'GITCLONE': clone_repo,
    'GITPULL': pull_repo,
    'SYNCDB': syncdb,
}
