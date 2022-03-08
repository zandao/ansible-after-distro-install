#!/usr/bin/env python3
import argparse
import logging
import os.path
import pickle
import shlex
import subprocess
import scripts.local_errors as le
from googleapiclient import errors
from googleapiclient.http import MediaFileUpload
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from typing import Final

DEFAULT_TOKEN: Final = "gdrive-token.pickle"
DEFAULT_CREDENTIALS: Final = "credentials.json"
SCOPES_UPLOAD: Final = ['https://www.googleapis.com/auth/drive']
SCOPES_DOWNLOAD: Final = ['https://www.googleapis.com/auth/drive.readonly']
MIME_FOLDER: Final = 'application/vnd.google-apps.folder'
MIME_TARGZ: Final = 'application/x-tar+gzip'
MIME_UNKNOWN: Final = '*/*'
FIELDS: Final = 'id, name, description, fileExtension, md5Checksum,\
 mimeType, parents, originalFilename, owners, quotaBytesUsed,\
 headRevisionId, version, capabilities'
CHUNK_SIZE: Final = 10*1024*1024

# functions must not have side effects, so when passing objects, lists or dictionaries
# as parameters, functions must not change its contents. Instead, functions must make
# a copy of these types os parameters, then change the copy.


def create_file(service, file_path, dest='/', mime_type=None):
    # pylint: disable=no-member
    le.debug(f"source: {file_path}, destination folder: {dest or 'parent'}")

    if not _check_local_file(file_path):
        return "error"

    if not mime_type:
        mime_type = _get_mimetype(file_path)

    file_name = os.path.basename(file_path)
    files_clones = get_files_ids(service, os.path.join(dest, file_name))
    if len(files_clones) > 0:
        le.warn(
            f"File {file_name} already exists on destiny"
            " Creating a new file with same name anyway")

    folders = get_files_info(
        service, dest, fields='id, name, mimeType, parents')
    le.debug(
        f"Folders: \n{map_field(filter_field(folders, 'mimeType', MIME_FOLDER), 'name')}")
    for folder in folders:
        file_metadata = {
            'name': os.path.basename(file_path),
            'mimeType': mime_type,
            'parents': [folder['id']]
        }
        le.debug(f"file_metadata: \n{file_metadata}")
        le.info(f"Uploading {file_path}")

        media = MediaFileUpload(
            file_path, chunksize=CHUNK_SIZE, mimetype=mime_type, resumable=True)
        uploader = service.files().create(body=file_metadata, media_body=media, fields='id')
        done = False
        while not done:
            status, done = uploader.next_chunk()
            if status:
                progress = int(status.progress() * 100)
                upload_msg = f" {os.path.basename(file_path)} uploading - {progress}%.   "
                print(upload_msg, end='\r')

        le.info(
            f"{os.path.basename(file_path)} uploaded to {folder['name']}")
    return "ok"


def download_files(service, query, dest_path=".", mime_type=None):
    if not query:
        le.error("File not found")
        return "error"

    if not _check_local_dir(dest_path):
        return "error"

    le.debug(f"Query: {query}")
    items = find_files(service, f"{query} and mimeType != '{MIME_FOLDER}'")
    if not items:
        le.warn('No files found')
    else:
        le.info('Files:')
        first = True
        for item in items:
            le.info(f"{item['name']} id:{item['id']}")
            _download_file(service, item['id'],
                           os.path.join(
                               dest_path, item['name'] + ('' if first else f"-{item['id']}")))
            first = False
    return "ok"


def filter_field(file_list, field, value):
    return list(filter(lambda item: item[field] == value, file_list))


def find_files(service, query=None, fields="id, name, mimeType, parents"):
    # Call the Drive v3 API
    # q="parents in 'id'" returns all files from specific folder
    # q="mimeType = 'application/vnd.google-apps.folder'" returns only folders
    page_token = None
    items = []
    while True:
        try:
            le.debug("Searching Google Drive...")
            results = service.files().list(
                q=f"trashed = false and {query}" if query else None,
                pageSize=1000,
                spaces='drive',
                # items(id, capabilities/canAddChildren)
                fields=f"nextPageToken, files({fields})",
                orderBy="folder,name",
                supportsAllDrives=False,
                pageToken=page_token).execute()
            items.extend(results.get('files', []))
            page_token = results.get('nextPageToken')
            if page_token is None:
                break
        except errors.HttpError as error:
            le.fail(f"A network error eccurred: {error}")
            break
    le.debug(f"Google Drive items found:\n{items}")
    return items


def get_files_ids(service, file_path):
    path_list = _split_gdrive_path(file_path)
    start_list = []
    if path_list[0] == '/':
        path_list.pop(0)
        start_list = [service.files().get(fileId='root').execute()['id']]
    return _get_files_ids(service, path_list, start_list)


def get_files_info(service, file_path, fields=FIELDS):
    result = []
    for id in get_files_ids(service, file_path):
        result.append(service.files().get(fileId=id, fields=fields).execute())
    return result


def get_service(token_path=DEFAULT_TOKEN,
                credentials_path=DEFAULT_CREDENTIALS,
                scopes=SCOPES_UPLOAD):
    creds = None
    # Disable a lot of erroneous WARNINGS when using oauth2
    logging.getLogger(
        'googleapiclient.discovery_cache').setLevel(logging.ERROR)

    # The file upload-token.pickle stores the user's access and refresh
    # tokens, and is created automatically when the authorization flow
    # completes for the first time.
    if os.path.exists(token_path):
        le.debug("Token found. Loading...")
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if not creds:
            le.debug("Credentials unavailable in token")
        elif not creds.valid:
            le.debug("Credentials found but not valid anymore")
        if creds and creds.expired and creds.refresh_token:
            le.debug("Refreshing credentials")
            creds.refresh(Request())
        else:
            le.debug("Requesting permission to access Google Drive")
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_path, scopes)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        le.debug("Saving acquired token")
        with open(token_path, 'wb', 33554432) as token:
            pickle.dump(creds, token)
    le.debug("Accessing Google Drive")
    service = build('drive', 'v3', credentials=creds)
    return service


def map_field(file_list, field):
    return list(map(lambda item: item[field], file_list))


def update_file(service, file_path, dest='/', mime_type=None):
    # pylint: disable=no-member
    le.debug(f"source: {file_path}, destination folder: {dest or 'parent'}")

    if not _check_local_file(file_path):
        return "error"

    if not mime_type:
        mime_type = _get_mimetype(file_path)

    dest_file = os.path.join(dest, os.path.basename(file_path))
    files = get_files_info(
        service, dest_file, fields='id, name, mimeType, parents')
    le.debug(
        f"Folders: \n{map_field(filter_field(files, 'mimeType', MIME_FOLDER), 'name')}")
    if len(files) > 1:
        le.fail('MORE THEN ONE PACKAGE WITH SAME NAME')
        exit("error")

    file_info = files[0]

    le.info(f"Uploading {file_path}")
    media = MediaFileUpload(
        file_path, chunksize=CHUNK_SIZE, mimetype=mime_type, resumable=True)
    uploader = service.files().update(fileId=file_info['id'], media_body=media)
    done = False
    while not done:
        status, done = uploader.next_chunk()
        if status:
            progress = int(status.progress() * 100)
            upload_msg = f" {os.path.basename(file_path)} uploading - {progress}%.   "
            print(upload_msg, end='\r')

    le.debug(f"updated_file: {file_info['name']}")
    le.info(
        f"{os.path.basename(file_path)} uploaded to {dest.split('/')[-1]}")
    return "ok"


def _check_local_dir(dir_path):
    if not os.path.exists(dir_path):
        le.error(f"Directory {dir_path} not found")
        return False
    elif not os.path.isdir(dir_path):
        le.error(f"{dir_path} is not a regular directory")
        return False
    else:
        return True


def _check_local_file(file_path):
    if not os.path.exists(file_path):
        le.error(f"File {file_path} not found")
        return False
    elif not os.path.isfile(file_path):
        le.error(f"{file_path} is not a regular file")
        return False
    else:
        return True


def _download_file(service, source_id, dest_file_name):
    request = service.files().get_media(fileId=source_id)
    done = False
    with open(dest_file_name, "wb") as fh:
        filename = os.path.basename(dest_file_name)
        downloader = MediaIoBaseDownload(fh, request, chunksize=CHUNK_SIZE)
        while done is False:
            status, done = downloader.next_chunk()
            progress = int(status.progress() * 100)
            download_msg = f" {filename} downloading - {progress}%.   "
            print(download_msg, end='\r')
    le.info(f"{filename} downloaded")


def _get_files_ids(service, path_list, start_list):
    if not path_list:
        return start_list

    dir_or_file = path_list[0]
    # make a *COPY* of path_list without first element
    path_list = path_list[1:]

    search_result = []
    if start_list:
        for id in start_list:
            files_in_folder = find_files(
                service, query=f"name = '{dir_or_file}' and '{id}' in parents")
            search_result.extend(map_field(files_in_folder, 'id'))
    else:
        files_in_folder = find_files(service, query=f"name = '{dir_or_file}'")
        search_result.extend(map_field(files_in_folder, 'id'))
    return _get_files_ids(service, path_list, search_result)


def _get_mimetype(file_path):
    result = subprocess.run(shlex.split(
        f"file --mime-type -b '{file_path}'"), capture_output=True)
    if result.returncode < 0:
        le.error(
            f"'file --mime-type -b {file_path}' terminated by signal {result.returncode}")
        mime_type = MIME_UNKNOWN
    elif result.returncode > 0:
        le.error(f"{result.stderr}")
        mime_type = MIME_UNKNOWN
    else:
        # discard complete path and gets filename and last file extension
        filename, extension = os.path.splitext(os.path.basename(file_path))
        # gets mimetype from stdout (except \n char) and converts to utf-8
        mime_type = result.stdout[:-1].decode("utf-8")
        if mime_type == 'application/gzip':
            # get only extension, discards filename
            subextension = os.path.splitext(filename)[1]
            if extension == '.tgz' or (subextension == '.tar' and extension == '.gz'):
                mime_type = MIME_TARGZ
    return mime_type


def _split_gdrive_path(path):
    folders = []
    while 1:
        path, folder = os.path.split(path)
        if folder != "":
            folders.insert(0, folder)
        else:
            if path != "":
                folders.insert(0, path)
            break
    return folders


def main():
    # Create the top-level parser
    parser = argparse.ArgumentParser(
        description="Uploading and downloading files to Google Drive folder")
    parser.add_argument("-v", "--verbosity", action="count",
                        help="increase output verbosity")
    parser.add_argument("-t", "--token", default=DEFAULT_TOKEN,
                        help="Google Drive authorization token file")
    parser.add_argument("-c", "--credentials", default=DEFAULT_CREDENTIALS,
                        help="Google Drive application credentials file")
    subparsers = parser.add_subparsers(dest="command", help='sub-command help')

    # Create the parser for the "upload" command
    parser_upload = subparsers.add_parser(
        'upload', help="uploads file to Google Drive")
    parser_upload.add_argument(
        "source", help="local file to upload to Google Drive", metavar="SOURCEFILE")
    parser_upload.add_argument("dest", nargs="?", default=None,
                               help="Google Drive folder to copy file to", metavar="DESTFOLDER")

    # Create the parser for the "download" command
    parser_download = subparsers.add_parser(
        "download", help="downloads file from Google Drive")
    parser_download.add_argument(
        "source", help="Google Drive file to download", metavar="GDRIVEFILE")
    parser_download.add_argument(
        "dest", help="local directory to download file to", metavar="DESTDIR")

    # Initialize command line arguments
    args = parser.parse_args()

    if args.verbosity == 2:
        verbosity = logging.DEBUG
    elif args.verbosity == 1:
        verbosity = logging.INFO
    else:
        verbosity = logging.WARNING
    logging.basicConfig(level=verbosity)

    le.debug(f"source: '{args.source}' dest:'{args.dest}'")
    if args.command == "upload":
        le.debug(f"SCOPE: {SCOPES_UPLOAD}")
        service = get_service(args.token, args.credentials, SCOPES_UPLOAD)
        create_file(service, args.source, args.dest)
    elif args.command == "download":
        le.debug(f"SCOPE: {SCOPES_DOWNLOAD}")
        service = get_service(args.token, args.credentials, SCOPES_DOWNLOAD)
        download_files(service, f"name = '{args.source}'", args.dest)


if __name__ == "__main__":
    main()

# Example of Google Drive file metadata in json
# {'files': [{'id': '1vEeXzxVMIOh9729PfIw3eGD-iv0elY26',
# 'name': 'file_example',
# 'parents': ['0BDSDQCj-gkqGUk9ABS'],
# 'version': '15',
# 'owners': [{'kind': 'drive#user',
# 'displayName': 'My name',
# 'photoLink': 'https://lh3.googleusercontent.com/a-/ASDFG-hiJk1l_m-2=n34',
# 'me': True,
# 'permissionId': '12345678901234567890',
# 'emailAddress': 'my.name@gmail.com'}],
# 'capabilities': {'canAddChildren': True,
# 'canAddMyDriveParent': False,
# 'canChangeCopyRequiresWriterPermission': False,
# 'canChangeViewersCanCopyContent': False,
# 'canComment': True,
# 'canCopy': False,
# 'canDelete': True,
# 'canDownload': True,
# 'canEdit': True,
# 'canListChildren': True,
# 'canModifyContent': True,
# 'canMoveChildrenWithinDrive': True,
# 'canMoveItemIntoTeamDrive': True,
# 'canMoveItemOutOfDrive': True,
# 'canMoveItemWithinDrive': True,
# 'canReadRevisions': False,
# 'canRemoveChildren': True,
# 'canRemoveMyDriveParent': True,
# 'canRename': True,
# 'canShare': True,
# 'canTrash': True,
# 'canUntrash': True},
# 'quotaBytesUsed': '65536'}]}
