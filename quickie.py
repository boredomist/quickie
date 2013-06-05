"""
Quickie is a simple script to maintain a history of runtimes of a project over
time.

This Python script will generate data to be graphed by a browser.
"""

import argparse
import json
import os
import sh
import subprocess
import tempfile
import time
import yaml

from termcolor import cprint, colored

global QUIET

### Some helpers to print in color
def fatal(msg):
    cprint('FATAL ERROR: ' + msg + '... exiting', 'red')
    exit(1)


def print_status(msg):
    print(colored('>> ', 'green') + msg)


def print_error(msg):
    cprint('!! ' + msg, 'red')


def print_warning(msg):
    cprint('!! ' + msg, 'yellow')


### Stolen from http://stackoverflow.com/questions/1685221/
class Timer(object):
    def __enter__(self):
        self.__start = time.time()

    def __exit__(self, type, value, traceback):
        # Error handling here
        self.__finish = time.time()

    def seconds(self):
        return self.__finish - self.__start


def set_repository(repo):
    """Jump to a new directory to avoid overwriting any work that might not
    have been commited yet"""

    # Copy repository verbatim
    tmp_dir = tempfile.mkdtemp(prefix='quickie-')
    sh.cd(tmp_dir)
    sh.cp('-R', repo + '/.', tmp_dir)

    return tmp_dir


def read_config(path, config_file):
    """Read the Quickie configuration file stored in `path'"""

    if not os.path.exists(config_file):
        fatal('No .quickierc here!')
        exit(1)

    with open(config_file, 'r') as stream:
        config = yaml.load(stream)
        config['repo'] = path
        return config


def create_data_dir(repo, config):
    """Build Quickie data directory (runtimes + html) if none has already been
    created"""

    try:
        data_dir = os.path.join(repo, config.get('data_dir', '.quickiedata'))
        sh.mkdir('-p', data_dir)

        config['data_dir_path'] = data_dir

        dir, _ = os.path.split(__file__)
        template = os.path.abspath(os.path.join(dir, "data"))

        # Don't overwrite the data file if it's already created.
        sh.cp('--no-clobber', template + '/data.json', data_dir)

        sh.cp(sh.glob(template + '/*.html'), data_dir)
        sh.cp(sh.glob(template + '/*.js'), data_dir)
        sh.cp(sh.glob(template + '/*.css'), data_dir)

    except sh.ErrorReturnCode as e:
        fatal("Couldn't create data directory:" + str(e))


def do_run(config):
    data_path = os.path.join(config['data_dir_path'], 'data.json')
    try:
        data = json.load(open(data_path))
    except Exception as e:
        fatal("Couldn't open the data file: " + str(e))

    data['repository'] = config['repo']
    data['first_run'] = data.get('first_run', time.time())
    data['last_run'] = time.time()
    data['run_data'] = data.get('run_data', {})

    cmds = {'run': config.get('commands', {}).get('run', []),
            'build': config.get('commands', {}).get('build', [])}

    repo_data = {}

    if os.path.exists('.git/'):
        try:
            # Grab the current branch / commit
            branch = str(sh.git('rev-parse', '--verify', '--abbrev-ref', 'HEAD'))
            branch = branch.rstrip()
            commit = str(sh.git('rev-parse', '--short', '--verify', 'HEAD'))
            commit = commit.rstrip()

            repo_data = {'branch': branch, 'commit': commit}
        except sh.ErrorReturnCode as e:
            print_warning("Couldn't get branch and commit info for repository" +
                          str(e))

    failed = True

    build_timer = Timer()
    with build_timer:
        print_status('Building...')
        for cmd in cmds['build']:
            try:
                print_status('\t' + cmd)
                if QUIET:
                    subprocess.check_call(cmd, shell=True,stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE)
                else:
                    subprocess.check_call(cmd, shell=True)
            except subprocess.CalledProcessError:
                print_warning('Command failed')
                break
        else:
            failed = False

        if failed:
            print_warning('!! Build failed, skipping run')

    print_status('Build complete ({0} s)'
                 .format(build_timer.seconds()))

    print_status('Running...')
    for cmd in cmds['run']:
        run_results = data['run_data'].get(cmd, [])

        print_status('\t' + cmd)

        start = time.time()
        run_timer = Timer()
        with run_timer:
            try:
                if QUIET:
                    subprocess.check_call(cmd, shell=True,stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE)
                else:
                    subprocess.check_call(cmd, shell=True)
            except subprocess.CalledProcessError:
                print_warning('Command failed')

        print_status('`{0}` completed in {1} seconds'
              .format(cmd, run_timer.seconds()))

        run_results.append([start, run_timer.seconds(), repo_data])
        data['run_data'][cmd] = run_results

    with open(data_path, 'w') as out:
        json.dump(data, out)



if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', help="Directory to be duplicated " +
                        "and used for profiling")
    parser.add_argument('-c', '--config', help='Configuration file to use ' +
                        'will default to <directory>/.quickierc')
    args = parser.parse_args()

    repo = os.path.abspath(args.directory)
    config_file = args.config

    if config_file == None:
        config_file = os.path.join(repo, '.quickierc')

    if not os.path.exists(repo):
        fatal(repo + " doesn't exist!")
    if not os.path.exists(config_file):
        fatal(config_file + " doesn't exist!")

    config = read_config(repo, config_file)
    create_data_dir(repo, config)

    global QUIET
    QUIET = config.get('quiet', False)

    tmpdir = set_repository(repo)

    do_run(config)

    print_status("Removing temp directory...")
    sh.rm('-r', tmpdir)
