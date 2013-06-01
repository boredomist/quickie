"""
Quickie is a simple script to maintain a history of runtimes of a project over
time.

This Python script will generate data to be graphed by a browser.
"""

import yaml
import logging
import os
import sh
import sys
import tempfile

log = logging.getLogger(__name__)


def fatal(msg):
    log.error('ERROR: ' + msg + '... exiting')
    exit(1)


def set_repository(repo):
    """Jump to a new directory to avoid overwriting any work that might not
    have been commited yet"""

    # Copy repository verbatim
    tmp_dir = tempfile.mkdtemp(prefix='quickie-')
    log.info(sh.cd(tmp_dir))
    log.info(sh.cp('-R', repo + '/.', tmp_dir))

    # Remove any uncommited changes
    git = sh.git.bake()
    try:
        git.reset('--hard', 'HEAD')
        git.clean('--force', '-x', '-d')
    except sh.ErrorReturnCode:
        fatal('Are you sure this is a git repo?')

    return git, tmp_dir


def read_config(path):
    """Read the Quickie configuration file stored in `path'"""

    conf = os.path.join(path, '.quickierc')

    if not os.path.exists(conf):
        fatal('No .quickierc here!')
        exit(1)

    with open(conf, 'r') as stream:
        return yaml.load(stream)


def print_usage(error=False):
    print('Usage: quickie DIRECTORY')
    if error:
        exit(1)
    else:
        exit(0)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print_usage(error=True)

    repo = os.path.abspath(sys.argv[1])
    if not os.path.exists(repo):
        fatal(repo + " doesn't exist!")

    config = read_config(repo)
    git, dir = set_repository(repo)

    sys.stdin.read(1)

    log.info(sh.rm('-r', dir))
