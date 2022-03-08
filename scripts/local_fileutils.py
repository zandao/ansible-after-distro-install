#!/usr/bin/env python3
import os
import os.path
import shlex
import subprocess
import tarfile
from functools import reduce

import scripts.local_errors as le


def decrypt_file(input, output, key):
    le.info(f"Decrypting {input}")
    return openssl_call('d', input, output, key)


def encrypt_file(input, output, key):
    le.info(f"Encrypting {input}")
    return openssl_call('e', input, output, key)


def extract_tarfile(input_filename, dest_dir='.'):
    if not os.path.exists(dest_dir):
        le.error(f"Directory {dest_dir} not found.")
        exit(2)
    if not os.path.isdir(dest_dir):
        le.error(f"{dest_dir} is not a directory.")
    if not os.path.exists(input_filename):
        le.error(f"File not found: {input_filename}")
        exit(2)
    if not tarfile.is_tarfile(input_filename):
        le.error(f"{input_filename} does not appear to be a tarfile")
    # call tar command - WARNING: don't use tarfile python library because
    # it doesn't work well with extended attributes and selinux
    try:
        le.info("Extracting tarball")
        output = os.popen(
            f"tar --extract -f {input_filename} --preserve-permissions --preserve-order "
            f"--directory='{dest_dir}' --acls --xattrs --ungzip --recursive").read()
        le.debug(output)
    except IOError:
        exit(2)


def make_tarfile(output_filename, input, relative_to=None, exclude=None):
    if relative_to:
        dir = f"--directory={relative_to}"
    else:
        dir = ""
    # put each file name in single quotes
    if type(input) != list:
        input = [f"'{input}'"]
    else:
        input = map(lambda filename: f"'{filename}'", input)
    # call tar command - WARNING: don't use tarfile python library because
    # it doesn't work well with extended attributes and selinux
    try:
        if exclude:
            le.debug(f"exclude: {exclude}")
            excludes = exclude.split(',')
            le.debug(f"excludes: {excludes}")
            exclude = ""
            for item in excludes:
                exclude = f"{exclude} --exclude='{item}'"
            le.debug(f"tar excludes: {exclude}")
        else:
            le.debug("No exclusions")
            exclude = ""
        file_list = reduce((lambda head, tail: f"{head} {tail}"), input)
        command = (
            f"tar --create -f {output_filename} {dir} --acls --xattrs --gzip "
            f"--one-file-system --exclude-caches{exclude} --recursion {file_list}")
        le.info("Creating tarball...")
        le.debug(command)
        output = os.popen(command).read()
        le.debug(output)
    except IOError:
        exit(2)


def openssl_call(command, file_in, file_out, key):
    encryption_config = "enc -aes-256-cbc -md sha512 -pbkdf2 -iter 100000 -salt"
    cmd_line = (f"openssl {encryption_config} -in '{file_in}' "
                f"-out '{file_out}' -{command} -pass 'pass:{key}'")
    bashCmd = shlex.split(cmd_line)
    result = subprocess.run(bashCmd, capture_output=True)  # run bash command
    if result.returncode < 0:
        le.fail(f" Terminated by signal {result.returncode}")
        exit(result.returncode)
    elif result.returncode > 0:
        le.error(f"{result.stderr}")
        exit(result.returncode)
    return result.stdout
