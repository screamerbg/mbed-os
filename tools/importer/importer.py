import os
import json
import sys
import subprocess
import logging
import argparse
import re
from os.path import dirname, abspath, join, isdir, isfile
from shutil import copyfile

# Be sure that the tools directory is in the search path
ROOT = abspath(join(dirname(__file__), "../.."))
sys.path.insert(0, ROOT)

from tools.utils import run_cmd, delete_dir_files, mkdir

def find_and_del_file(name):
    """ Delete the file in RTOS/CMSIS/features directory of mbed-os
    Args:
    name - name of the file
    """
    result = []
    search_path = [join(ROOT, 'rtos'), join(ROOT, 'cmsis'), join(ROOT, 'features')]
    for path in search_path:
        for root, dirs, files in os.walk(path):
            if name in files:
                result.append(os.path.join(root, name))
    for file in result:
        os.remove(file)
        rel_log.debug("Deleted file: %s", os.path.relpath(file, ROOT))

def copy_file(src, dst, regs = None):
    """ Implement the behaviour of "shutil.copy(src, dst)" without copying the
    permissions (this was causing errors with directories mounted with samba)

    Positional arguments:
    src - the source of the copy operation
    dst - the destination of the copy operation
    """
    if isdir(dst):
        _, base = split(src)
        dst = join(dst, base)
    copyfile(src, dst)

    if regs:
        with open(dst, 'rb+') as f:
            content = f.read()
            for reg in regs:
                content = re.sub(reg['ptr'], reg['rpl'], content)
            f.seek(0)
            f.write(content)
            f.truncate()

def copy_folder(src, dest, regs = None):
    """ Copy contents of folder in mbed-os listed path
    Args:
    src - src folder path
    dest - destination folder path
    """
    files = os.listdir(src)
    for file in files:
        abs_src_file = os.path.join(src, file)
        if os.path.isfile(abs_src_file):
            abs_dst_file = os.path.join(dest, file)
            mkdir(os.path.dirname(abs_dst_file))
            copy_file(abs_src_file, abs_dst_file, regs)

def run_cmd_with_output(command, exit_on_failure=False):
    """ Passes a command to the system and returns a True/False result once the
        command has been executed, indicating success/failure. If the command was
        successful then the output from the command is returned to the caller.
        Commands are passed as a list of tokens.
        E.g. The command 'git remote -v' would be passed in as ['git', 'remote', '-v']

    Args:
    command - system command as a list of tokens
    exit_on_failure - If True exit the program on failure (default = False)

    Returns:
    result - True/False indicating the success/failure of the command
    output - The output of the command if it was successful, else empty string
    """
    rel_log.debug('[Exec] %s' % command)
    returncode = 0
    output = ""
    try:
        output = subprocess.check_output(command, shell=True)
    except subprocess.CalledProcessError as e:
        returncode = e.returncode

        if exit_on_failure:
            rel_log.error("The command %s failed with return code: %s",
                        (' '.join(command)), returncode)
            sys.exit(1)
    return returncode, output

def get_curr_sha(repo_path):
    """ Gets the latest SHA for the specified repo
    Args:
    repo_path - path to the repository

    Returns:
    sha - last commit SHA
    """
    cwd = os.getcwd()
    os.chdir(abspath(repo_path))

    cmd = "git log --pretty=format:%h -n 1"
    _, sha = run_cmd_with_output(cmd, exit_on_failure=True)

    os.chdir(cwd)
    return sha

def branch_exists(name):
    """ Check if branch already exists in mbed-os local repository.
    It will not verify if branch is present in remote repository.
    Args:
    name - branch name
    Returns:
    True - If branch is already present
    """

    cmd = "git branch"
    _, output = run_cmd_with_output(cmd, exit_on_failure=False)
    if name in output:
        return True
    return False

def branch_checkout(name):
    """
    Checkout the required branch
    Args:
    name - branch name
    """
    cmd = "git checkout " + name
    run_cmd_with_output(cmd, exit_on_failure=False)

def get_last_cherry_pick_sha(branch):
    """
    SHA of last cherry pick commit is returned. SHA should be added to all
    cherry-pick commits with -x option.

    Args:
    branch - Hash to be verified.
    Returns - SHA if found, else None
    """
    cmd = "git checkout " + branch
    run_cmd_with_output(cmd, exit_on_failure=False)

    sha = None
    get_commit = "git log -n 1"
    _, output = run_cmd_with_output(get_commit, exit_on_failure=True)
    lines = output.split('\n')
    for line in lines:
        if 'cherry picked from' in line:
            sha = line.split(' ')[-1]
            return sha[:-1]
    return sha

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-l', '--log-level',
                        help="Level for providing logging output",
                        default='INFO')
    parser.add_argument('-r', '--repo-path',
                        help="Git Repository to be imported",
                        default=None,
                        required=True)
    parser.add_argument('-c', '--config-file',
                        help="Configuration file",
                        default=None,
                        required=True)
    parser.add_argument('-n', '--no-git',
                        help="No Git operations - only process folders/files.",
                        action="store_true",
                        default=False,
                        required=False)
    args = parser.parse_args()
    level = getattr(logging, args.log_level.upper())

    # Set logging level
    logging.basicConfig(level=level)
    rel_log = logging.getLogger("IMPORTER")

    if (args.repo_path is None) or (args.config_file is None):
        rel_log.error("Repository path and config file required as input. Use \"--help\" for more info.")
        exit(1)

    json_file = os.path.abspath(args.config_file)
    if not os.path.isfile(json_file):
        rel_log.error("%s not found.", args.config_file)
        exit(1)

    repo = os.path.abspath(args.repo_path)
    if not os.path.exists(repo):
        rel_log.error("%s not found.", args.repo_path)
        exit(1)

    sha = get_curr_sha(repo)
    if not sha:
        rel_log.error("Could not obtain latest SHA")
        exit(1)
    rel_log.info("%s SHA = %s", os.path.basename(repo), sha)

    branch = 'feature_' + os.path.basename(repo) + '_' + sha
    commit_msg = "[" + os.path.basename(repo) + "]" + ": Updated to " + sha

    # Read configuration data
    with open(json_file, 'r') as config:
        json_data = json.load(config)

    data_files = json_data["files"]
    data_folders = json_data["folders"]
    data_remove = json_data["remove"]
    data_regs = json_data["regs"] if "regs" in json_data.keys() else None

    '''
    Check if branch exists already, in case branch is present
    we will skip all file transfer and merge operations and will
    jump to cherry-pick
    '''
    if args.no_git or not branch_exists(branch):
        ## Remove all files listed in .json from mbed-os repo to avoid duplications
        for file in data_files:
            dest_file = file['dest_file']
            if os.path.isfile(dest_file):
                os.remove(dest_file)
                rel_log.debug("Deleted file: %s" % dest_file)

        for folder in data_folders:
            dest_folder = folder['dest_folder']
            delete_dir_files(dest_folder)
            rel_log.debug("Deleted folder: %s" % dest_folder)

        rel_log.info("Removed files/folders listed in json file")

        ## Copy all the CMSIS files listed in json file to mbed-os
        for file in data_files:
            repo_file = os.path.join(repo, file['src_file'])
            mbed_path = os.path.join(ROOT, file['dest_file'])
            mkdir(os.path.dirname(mbed_path))
            copy_file(repo_file, mbed_path, data_regs)
            rel_log.debug("Copied file: %s -> %s" % (repo_file, mbed_path))

        for folder in data_folders:
            repo_folder = os.path.join(repo, folder['src_folder'])
            mbed_path = os.path.join(ROOT, folder['dest_folder'])
            copy_folder(repo_folder, mbed_path, data_regs)
            rel_log.debug("Copied folder: %s -> %s" % (repo_folder, mbed_path))

        for remove in data_remove:
            mbed_path = os.path.join(ROOT, remove['dest'])
            if isdir(mbed_path):
                rel_log.debug("Removed folder (config): %s" % mbed_path)
                os.rmdir(mbed_path)
            elif isfile(mbed_path):
                rel_log.debug("Removed file (config): %s" % mbed_path)
                os.remove(mbed_path)

        if args.no_git:
            rel_log.debug("Skipped Git operations due to --no-git used.")
            sys.exit()

        ## Create new branch with all changes
        run_cmd_with_output("git checkout -b %s" % branch, exit_on_failure=True)
        rel_log.info("Branch created: %s" % branch)

        run_cmd_with_output("git add -A", exit_on_failure=True)

        run_cmd_with_output("git commit -m \"%s\"" % commit_msg, exit_on_failure=True)
        rel_log.info("Commit added: %s" % mbed_path)
    else:
        rel_log.info("Branch present: %s" % branch)

    ## Checkout the feature branch
    branch_checkout(branch)
    commit_sha = json_data["commit_sha"]
    last_sha = get_last_cherry_pick_sha(branch)
    if not last_sha:
        ## Apply commits specific to mbed-os changes
        for sha in commit_sha:
            cherry_pick_sha = "git cherry-pick -x " + sha
            run_cmd_with_output(cherry_pick_sha, exit_on_failure=True)
            rel_log.info("Commit added: %s" % cherry_pick_sha)
    ## Few commits are already applied, check the next in sequence
    ## and skip to last applied
    else:
        found = False
        for sha in commit_sha:
            if sha == last_sha:
                found = True
                continue
            if found is True:
                cherry_pick_sha = "git cherry-pick -x " + sha
                run_cmd_with_output(cherry_pick_sha, exit_on_failure=True)
