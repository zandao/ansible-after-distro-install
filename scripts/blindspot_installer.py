#!/bin/env python3
import io
import logging
import os
import os.path
import re
import tarfile
import zipfile
from collections import namedtuple

import magic
import requests
import yaml
from github import Github
from requests.exceptions import ConnectionError
from semver import VersionInfo

Asset = namedtuple('Asset', ['name', 'browser_download_url'])  # NOSONAR
AssetWithPriority = namedtuple('AssetWithPriority', ['asset', 'priority'])  # NOSONAR
Release = namedtuple('Release', ['release', 'assets'])  # NOSONAR

VALID_EXECUTABLE_MIMES = [
    'application/x-executable', 'application/x-sharedlib', 'text/x-java', 'text/x-lisp', 'text/x-lua', 'text/x-perl',
    'text/x-python', 'text/x-ruby', 'text/x-shellscript', 'text/x-tcl'
]
MIN_ASSET_PRIORITY = 999
empty_asset_with_lowest_priority = AssetWithPriority(Asset(None, None), MIN_ASSET_PRIORITY)


def install_package_from_repo(repo):
    releases = [
        Release(release, [asset
                          for asset in release.get_assets()])
        for release in repo.get_releases()
        if valid_release(release)
    ]
    sorting_key = lambda item: get_semver(item.release.tag_name)
    sorted_releases = sorted(releases, key=sorting_key, reverse=True)
    asset_to_download = get_preferred_asset(sorted_releases[0].assets)
    logging.info(f"    Chosen: {asset_to_download.name}")
    logging.info(f"      Size: {asset_to_download.size // 1024 / 1024:.2f}MB")
    logging.debug(f"      URL: {asset_to_download.browser_download_url}")
    install_package(asset_to_download.browser_download_url, "/tmp")


def valid_release(release):
    return not (release.prerelease or release.draft) and type(get_semver(release.tag_name)) is VersionInfo


def get_semver(version):
    search_ver = re.search(r'^v?(?P<ver>\d+(\.\d+)+.*)', version, re.IGNORECASE)
    if (search_ver):
        try:
            ver = VersionInfo.parse(search_ver.group('ver'))
            logging.debug(f'    valid release: {ver}')
        except (ValueError, TypeError, AttributeError):
            ver = None
    else:
        ver = None
    return ver


def get_preferred_asset(valid_assets, asset_with_priority=empty_asset_with_lowest_priority):
    if len(valid_assets) == 0:
        return asset_with_priority.asset

    head, *tail = valid_assets
    if any(exclusion.search(head.name) for exclusion in exclusion_regexes()):
        return get_preferred_asset(tail, asset_with_priority)
    else:
        return get_preferred_asset(tail, get_highest_priority_asset(head, asset_with_priority))


def exclusion_regexes():
    # Singleton function, initializes static variable regex_list only in the first call
    if getattr(exclusion_regexes, 'regex_list', None) is None:
        exclusion_regexes.regex_list = [
            re.compile(r'\.(sig|deb|txt|yaml|exe|des|md5|sha[1-8]{1,3})$', re.I),
            re.compile(r'^(AUTHOR|README|LICENSE|completions|md5|sha[1-8]{1,3})', re.I),
            re.compile(r'(win(dows)?|darwin|mac(os)?|netbsd|android|source|arm)', re.I)
        ]
    return exclusion_regexes.regex_list


def get_highest_priority_asset(asset, asset_with_priority=empty_asset_with_lowest_priority):
    valid_asset_with_priority = asset_with_priority

    matches = list(
        map(lambda expr_list: 'priority' if all(expr.search(asset.name) != None for expr in expr_list) else 'no match',
            inclusion_regexes()))
    asset_priority = matches.index('priority') if 'priority' in matches else MIN_ASSET_PRIORITY
    logging.debug(f"    priority: {asset_priority:3d} name: {asset.name} size: {asset.size}")

    if asset_priority < asset_with_priority.priority:
        valid_asset_with_priority = AssetWithPriority(asset, asset_priority)
    return valid_asset_with_priority


def inclusion_regexes():
    # Singleton function, initializes static variable regex_list only in the first call
    if getattr(inclusion_regexes, 'regex_list', None) is None:
        accepted_architectures = [
            re.compile(expression, re.I) for expression in [r'(x86_64|amd64)', r'.*(?!x86_64|amd64).*$']
        ]
        accepted_os = [
            re.compile(expression, re.I)
            for expression in [r'[_.-]linux-gnu([_.-]|$)', r'[_.-]linux-musl([_.-]|$)', r'[_.-]linux([_.-]|$)']
        ]
        accepted_extensions = [
            re.compile(expression, re.I)
            for expression in [r'^(?!.*\.(tar\.gz|zip)$).*$', r'\.tar(\.gz)?$', r'\.zip$']
        ]
        inclusion_regexes.regex_list = []
        for architecture in accepted_architectures:
            for os_name in accepted_os:
                for extension in accepted_extensions:
                    inclusion_regexes.regex_list.append(
                        [re.compile(architecture),
                         re.compile(os_name), re.compile(extension)])
    return inclusion_regexes.regex_list


def install_package(url, dest):
    logging.debug(f"      Dest: {dest}")

    fname = url[url.rfind('/') + 1:]
    try:
        response = requests.get(url)
        logging.info(f"      Mime: {mimetype(response.content)}")
        extracted_files = extracted_content(fname, response.content)
    except ConnectionError as e:
        logging.error(e.strerror)
        extracted_files = []
    return extracted_files


def extracted_content(fname, content):
    files = []
    compressed_stream = io.BytesIO(content)
    mime = mimetype(content)
    if mime in ['application/x-compressed-tar', 'application/x-tar'] or (mime == 'application/gzip' and
                                                                         fname.endswith('tar.gz')):
        mode = 'r:' if mime == 'application/x-tar' else 'r:gz'
        files = generic_unpack(compressed_stream=compressed_stream,
                               get_package_handle=lambda stream: tarfile.open(fileobj=stream, mode=mode),
                               get_files=lambda tar: tar.getmembers(),
                               is_file=lambda tarinfo: tarinfo.isfile(),
                               get_fd=lambda tar, file: tar.extractfile(file),
                               get_file_name=lambda file: file.name)
    elif mime == 'application/zip':
        files = generic_unpack(compressed_stream=compressed_stream,
                               get_package_handle=lambda stream: zipfile.ZipExtFile(stream, mode='r'),
                               get_files=lambda zip: zip.infolist(),
                               is_file=lambda zipinfo: not zipinfo.is_dir(),
                               get_fd=lambda zip, file: zip.open(file),
                               get_file_name=lambda file: file.filename)
    elif mime in VALID_EXECUTABLE_MIMES:
        files.append({'name': fname, 'mime': mime, 'content': content})
    return files


def generic_unpack(compressed_stream, get_package_handle, get_files, is_file, get_fd, get_file_name):
    files = []
    with get_package_handle(compressed_stream) as package:
        for file in [fileinfo for fileinfo in get_files(package) if is_file(fileinfo)]:
            logging.info(f'\t  name: {get_file_name(file)}')
            with get_fd(package, file) as file_descriptor:
                if file_descriptor:
                    file_content = file_descriptor.read()
                    mime_type = mimetype(file_content)
                    files.append({'name': get_file_name(file), 'mime': mime_type, 'content': file_content})
                    logging.debug(f'\t  name: {get_file_name(file)}, mime: {mime_type}')
                else:
                    logging.error(f'\t  error extracting file {get_file_name(file)}')
    return files


def mimetype(it):
    return magic.from_descriptor(it, mime=True) if type(it) is file else magic.from_buffer(it, mime=True)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    with open(os.path.expanduser('~/workstation-install/packages.yml')) as file:
        packages = yaml.load(file.read(), Loader=yaml.SafeLoader)

    github_connection = Github(os.environ['GITHUB_TOKEN'])

    for repo in (github_connection.get_repo(repo_name) for repo_name in packages['blindspot_packages']):
        logging.info(f'### {repo.name}')
        install_package_from_repo(repo)
