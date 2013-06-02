"""
Quickie is a simple script to maintain a history of runtimes of a project over
time.

This Python script will generate data to be graphed by a browser.
"""

import json
import os
import sh
import sys
import tempfile
import yaml
import subprocess
import time

from termcolor import cprint, colored


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

    # Remove any uncommited changes
    git = sh.git.bake(_cwd=tmp_dir)
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


def do_run(git, config):
    data_path = os.path.join(config['data_dir_path'], 'data.json')
    try:
        data = json.load(open(data_path))
    except Exception as e:
        fatal("Couldn't open the data file: " + str(e))

    data['repository'] = config['repo']
    data['branches'] = data.get('branches', {})
    data['first_run'] = data.get('first_run', time.strftime('%X %x %Z'))
    data['last_run'] = time.strftime('%X %x %Z')

    cmds = {'run': config.get('commands', {}).get('run', []),
            'build': config.get('commands', {}).get('build', [])}

    for branch in config['branches']:
        print_status("Switching to branch {0}...".format(branch))

        branch_dict = data['branches'].get(branch, {})

        try:
            git.checkout('-f', branch)
        except sh.ErrorReturnCode as e:
            print_warning("Skipping branch, git errored on checkout: " +
                          str(e.stderr))
            continue

        failed = True

        timer = Timer()
        with timer:
            print_status('Building...')
            for cmd in cmds['build']:
                try:
                    print(cmd)
                    subprocess.check_call(cmd, shell=True)
                except subprocess.CalledProcessError:
                    print_warning('Command failed')
                    break
            else:
                failed = False

            if failed:
                print_warning('!! Build failed, skipping run')
                continue

        print_status('Build complete ({0} s)'
                     .format(timer.seconds()))

        print_status('Running...')
        for cmd in cmds['run']:
            run_results = branch_dict.get(cmd, [])

            print(cmd)
            timer = Timer()
            with timer:
                try:
                    subprocess.check_call(cmd, shell=True)
                except subprocess.CalledProcessError:
                    print_warning('Command failed')

            print('`{}` completed in {} seconds'.format(cmd, timer.seconds()))

            run_results.append(timer.seconds())
            branch_dict[cmd] = run_results

        data['branches'][branch] = branch_dict

    with open(data_path, 'w') as out:
        json.dump(data, out)

    print(data)


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
    create_data_dir(repo, config)

    git, tmpdir = set_repository(repo)

    do_run(git, config)

    print_status("Removing temp directory...")
    sh.rm('-r', tmpdir)
