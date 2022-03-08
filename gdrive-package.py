#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import configparser
import getpass
import logging
import os
import os.path
import scripts.local_errors as le
import tempfile
from googleapiclient import errors
from pathlib import Path
from scripts.gdrive import _download_file, find_files, get_files_ids
from scripts.gdrive import get_files_info, get_service, create_file
from scripts.gdrive import _get_mimetype, update_file, MIME_TARGZ
from scripts.local_errors import bcolors as c
from scripts.local_fileutils import decrypt_file, encrypt_file, extract_tarfile, make_tarfile
from typing import Final

NO_ERROR: Final = 0
NOT_FOUND_ERROR: Final = 11
OPENSSL_NOT_FOUND_ERROR: Final = 12
MAKE_TARGZ_ERROR: Final = 13
ENCRYPTION_ERROR: Final = 14
GDRIVE_UPLOAD_ERROR: Final = 15
GDRIVE_DOWNLOAD_ERROR: Final = 16
DEFAULT_PACKAGE_REPO: Final = "/workstation-package-repository"


def config(credentials):
    home = os.path.expanduser("~")
    final_path = os.path.join(home, ".config/gdrive-package")
    if not os.path.isdir(final_path):
        os.makedirs(final_path)
        le.warn(f"Put your credentials in json format at {final_path}")
        exit()

    if credentials:
        path = os.path.join(final_path, credentials)
    else:
        gitconfig = os.path.join(home, '.gitconfig')
        if os.path.exists(gitconfig):
            config = configparser.ConfigParser()
            config.read(gitconfig)
            credentials_name = config['user']['email'].split('@')[0]
            path = os.path.join(final_path, credentials_name)
        else:
            path = os.path.join(final_path, getpass.getuser())
    credentials_path = f"{path}-credentials.json"
    token_path = f"{path}-token.pickle"

    return (credentials_path, token_path)


def create_archive(package, source, encryption_key=None, exclude=None):
    tar_file = os.path.join(tempfile.gettempdir(), package) + '.tar.gz'
    error = None
    mime_type = None

    try:
        rel_path_source = list(map(
            lambda filename: os.path.relpath(
                os.path.abspath(filename), Path.home()),
            source))
        make_tarfile(tar_file, rel_path_source,
                     relative_to=Path.home(), exclude=exclude)
    except Exception as e:
        le.error("Failure during tar.gz creation.")
        print(e)
        error = MAKE_TARGZ_ERROR

    if not error:
        try:
            if encryption_key:
                mime_type = 'application/octet-stream'
                encrypt_file(tar_file, f"{tar_file}.enc", encryption_key)
                os.remove(tar_file)
                tar_file = tar_file+'.enc'
            else:
                mime_type = MIME_TARGZ
        except Exception as e:
            le.error("Failure during file encryption.")
            print(e)
            error = ENCRYPTION_ERROR
    return (error, tar_file, mime_type)


def create_package(credentials, token, package, source,
                   repository=DEFAULT_PACKAGE_REPO, encryption_key=None, exclude=None):
    for source_file in source:
        if not os.path.exists(source_file):
            le.error(f"{source_file} not found.")
            exit(NOT_FOUND_ERROR)
    error, tar_file, mime_type = create_archive(
        package, source, encryption_key, exclude)
    if error:
        exit(error)
    else:
        upload_package(credentials, token, tar_file, repository, mime_type)


def download_file(credentials, token, repository_path, filename):
    try:
        service = get_service(token, credentials)
        dest_dir, basename = os.path.split(filename)
        files_info = get_files_info(
            service, os.path.join(repository_path, basename))
    except errors.Error:
        le.error('Error during download')
        exit(GDRIVE_DOWNLOAD_ERROR)
    try:
        if files_info:
            first = True
            for gdrive_file in files_info:
                _download_file(service, gdrive_file['id'], os.path.join(
                    dest_dir, gdrive_file['name'] + ('' if first else f"-{gdrive_file['id']}")))
                first = False
        else:
            le.error('No files found')
    except errors.Error:
        le.error('Error during download')
        exit(GDRIVE_DOWNLOAD_ERROR)


def download_package(credentials, token, tar_file, repository_path, dest_dir):
    try:
        service = get_service(token, credentials)
        files_info = get_files_info(
            service, os.path.join(repository_path, tar_file))
    except errors.Error:
        le.error('Error during download')
        exit(GDRIVE_DOWNLOAD_ERROR)
    try:
        first = True
        for gdrive_file in files_info:
            _download_file(service, gdrive_file['id'], os.path.join(
                dest_dir, gdrive_file['name'] + ('' if first else f"-{gdrive_file['id']}")))
            first = False
    except errors.Error:
        le.error('Error during download')
        exit(GDRIVE_DOWNLOAD_ERROR)


def install_package(credentials, token, package_name, cache_directory=Path.home(),
                    repository=DEFAULT_PACKAGE_REPO, encryption_key=None, base_dir=Path.home()):
    le.debug(f"repository: {repository}")
    le.debug(f"credentials: {credentials}")
    le.debug(f"token: {token}")
    if not os.path.exists(cache_directory):
        le.error(f"{cache_directory} not found")
        exit(NOT_FOUND_ERROR)
    if not os.path.isdir(cache_directory):
        le.error(f"{cache_directory} is not a directory")
        exit(NOT_FOUND_ERROR)
    if package_name == 'ALL':
        packages = list_packages(
            credentials, token, repository, print_output=False)
    else:
        packages = [f"{package_name}.tar.gz{'.enc' if encryption_key else ''}"]
    for filename in packages:
        le.debug(
            f"Downloading {filename} from {repository} to {cache_directory}")
        download_package(credentials, token, filename,
                         repository, cache_directory)
        if encryption_key:
            tar_file_enc = os.path.join(cache_directory, filename)
            tar_file = os.path.splitext(tar_file_enc)[0]
            decrypt_file(tar_file_enc, tar_file, encryption_key)
            os.remove(tar_file_enc)
        else:
            tar_file = os.path.join(cache_directory, filename)
        le.debug(f"Downloaded {tar_file}")
        le.debug(f"Extracting {tar_file} to {Path.home()}")
        extract_tarfile(tar_file, base_dir)
        le.debug(f"Removing downloaded file ({tar_file})")
        os.remove(tar_file)


def list_packages(credentials, token, repository_path, long_output=False, print_output=True):

    packages = []
    try:
        service = get_service(token, credentials)
        if long_output and print_output:
            le.info(f"Listing packages from {repository_path}")
        repos = get_files_ids(service, repository_path)
        for repo in repos:
            files = find_files(
                service, query=f"'{repo}' in parents", fields="name, size, version")
            package_files = list(filter(
                lambda file: 'tar.gz' in file['name'], files))
            last_filename = ''
            for file_info in package_files:
                name = file_info['name'].split('.')
                if file_info['name'] == last_filename:
                    color = f"{c.FAIL}DUPLICATED "
                else:
                    color = c.OKGREEN
                if name[-1] == 'gz' or name[-2] == 'gz':
                    if long_output and print_output:
                        le.info(
                            f"{color}{'S' if name[-1] == 'enc' else '-'} "
                            f"{pretty_size(file_info['size'])} {name[0]} v{file_info['version']}")
                    elif print_output:
                        print(name[0])
                    packages.append(file_info['name'])
                last_filename = file_info['name']
            if long_output:
                le.info(
                    "───────────────────────────────────────────────────────────────")
                num_packages = len(
                    list(filter(lambda file_info: '.tar.gz' in file_info['name'], package_files)))
                if num_packages == 1:
                    le.info(f"{num_packages} package")
                else:
                    le.info(f"{num_packages} packages")
    except errors.Error:
        le.error('Error during download')
        exit(GDRIVE_DOWNLOAD_ERROR)
    return packages


def pretty_size(bytes):
    """Get human-readable file sizes.
    simplified version of https://pypi.python.org/pypi/hurry.filesize/
    """
    units = [
        (1 << 50, 'PB'),
        (1 << 40, 'TB'),
        (1 << 30, 'GB'),
        (1 << 20, 'MB'),
        (1 << 10, 'KB'),
        (1, 'B')]

    if isinstance(bytes, str):
        bytes = int(bytes)

    for factor, suffix in units:
        if bytes >= factor:
            break
    amount = int(bytes / factor)

    if isinstance(suffix, tuple):
        singular, multiple = suffix
        if amount == 1:
            suffix = singular
        else:
            suffix = multiple
    return f"{(str(amount) + suffix):>5}"


def upload_file(credentials, token, repository_path, filename):
    error = None
    mime_type = _get_mimetype(filename)
    try:
        service = get_service(token, credentials)
        basename = os.path.basename(filename)
        dest_file_name = os.path.join(repository_path, basename)
        num_files = len(get_files_ids(service, dest_file_name))
        if num_files > 1:
            le.error(
                f"Many clones of file {basename} already exists"
                " at repository {repository}")
            error = 1
        elif num_files == 0:
            create_file(service, filename, repository_path, mime_type)
            le.info("File creation successful")
        else:
            update_file(service, filename, repository_path, mime_type)
            le.info("File update successful")
    except errors.Error:
        le.error("Failure during file upload.")
        error = GDRIVE_UPLOAD_ERROR
    return error


def upload_package(credentials, token, tar_file, repository_path, mime_type=MIME_TARGZ):
    error = None
    try:
        service = get_service(token, credentials)
        basename = os.path.basename(tar_file)
        package_name = tar_file.split('.')[0]
        dest_file_name = os.path.join(repository_path, basename)
        num_files = len(get_files_ids(service, dest_file_name))
        if num_files > 1:
            le.error(
                f"Many clones of package {package_name} already exists"
                " at repository {repository_path}")
            error = 1
        elif num_files == 0:
            le.info("Creating package...")
            create_file(service, tar_file, repository_path, mime_type)
            le.info("Package creation successful")
        else:
            le.info("Updating package...")
            update_file(service, tar_file, repository_path, mime_type)
            le.info("Package update successful")
    except errors.Error:
        le.error("Failure during file upload.")
        error = GDRIVE_UPLOAD_ERROR
    else:
        os.remove(tar_file)
    return error


def main():
    # pylint: disable=unused-variable
    parser = argparse.ArgumentParser(
        description='Manages workstation packages in Google Drive.')
    parser.add_argument('-c', '--credentials', action='store', default=None,
                        help='Google Drive credentials name', metavar='NAME')
    parser.add_argument('-k', '--encryption-key', default=None,
                        help='if set, encrypt before upload using this key', metavar="KEY")
    parser.add_argument('-r', '--repository', default=DEFAULT_PACKAGE_REPO,
                        help='Google Drive path of repository of packages',
                        metavar="GDRIVE_DIR")
    parser.add_argument("-v", "--verbosity", action="count",
                        help="increase output verbosity")
    subparsers = parser.add_subparsers(dest="command", help='sub-command help')

    parser_create = subparsers.add_parser(
        'create', help="creates package file at Google Drive")
    parser_create.add_argument(
        '-e', '--exclude', default=None,
        help='comma separated list of files to be excluded from package', metavar='FILESLIST')
    parser_create.add_argument(
        'package', help='name of the package to be created and uploaded')
    parser_create.add_argument(
        'source', nargs='+', help='list of files and directories to create package from')

    parser_install = subparsers.add_parser(
        'install', help='intalls package from Google Drive repository')
    parser_install.add_argument(
        '-b', '--base-dir', default=Path.home(), help='base directory')
    parser_install.add_argument(
        'package', help='name of the package to be installed')
    parser_install.add_argument(
        'dir', nargs='?', default="/tmp", help='temporary directory to cache package')

    parser_list = subparsers.add_parser(
        'list', help="list packages from Google Drive repository")
    parser_list.add_argument(
        '--long', '-l', dest="long", default=False, action='store_true', help='long output')

    parser_upload_file = subparsers.add_parser(
        'upload-file', help="copy files to Google Drive")
    parser_upload_file.add_argument(
        'file', help='name of the file to be uploaded')

    parser_download_file = subparsers.add_parser(
        'download-file', help="copy files from Google Drive")
    parser_download_file.add_argument(
        'file', help='name of the file to be downloaded')

    # creating credentials:
    # https://o7planning.org/en/11917/create-credentials-for-google-drive-api#a20585804

    args = parser.parse_args()
    if args.verbosity and args.verbosity > 0:
        verbosity = logging.DEBUG
    else:
        verbosity = logging.INFO
    logging.basicConfig(level=verbosity)

    credentials, token = config(args.credentials)

    if args.command == 'create':
        create_package(credentials, token, args.package,
                       args.source, args.repository, args.encryption_key, args.exclude)
    elif args.command == 'install':
        install_package(credentials, token, args.package,
                        args.dir, args.repository, args.encryption_key, base_dir=args.base_dir)
    elif args.command == 'list':
        list_packages(credentials, token, args.repository, args.long)
    elif args.command == 'upload-file':
        upload_file(credentials, token, args.repository, args.file)
    elif args.command == 'download-file':
        download_file(credentials, token, args.repository, args.file)


if __name__ == "__main__":
    main()
