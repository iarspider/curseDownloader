import argparse
import copy
import simplejson as json
from pathlib import Path
import re

import requests


__author__ = 'james'

parser = argparse.ArgumentParser(description="Update Curse modpack manifest")
parser.add_argument("--manifest", help="manifest.json file from unzipped pack")
parser.add_argument("--nogui", dest="gui", action="store_false", help="Do not use gui to to select manifest")
args, unknown = parser.parse_known_args()


def parseManifest(manifest):
    manifestPath = Path(manifest)

    manifestText = manifestPath.open().read()
    manifestText = manifestText.replace('\r', '').replace('\n', '')

    manifestJson = json.loads(manifestText)
    return manifestJson


def getNameForNumericalId(session, numericalid):
    project_response = session.get("http://minecraft.curseforge.com/mc-mods/%s" % (numericalid), stream=True)
    url = project_response.url
    # name_id_parts = re.split("\d+-([^/]*)", url, 1)
    # try:
    #     result = name_id_parts[-2]
    # except IndexError:
    #     result = None

    # if result is None:
    url.rstrip('/')
    result = url.rsplit('/', 1)[1]

    return result


def getFilesForVersion(session, mcversion, modid, modname):
    files_json_response = session.get("http://widget.mcf.li/mc-mods/minecraft/%s.json" % modname)
    if files_json_response.status_code != 200:
        files_json_response = session.get("http://widget.mcf.li/mc-mods/minecraft/%d-%s.json" % (modid, modname))
    files_json = files_json_response.json()
    versions = files_json["versions"]
    if mcversion in versions:
        return versions[mcversion]
    else:
        return []


def get_newer_files(file_list, target_file):
    newer_files = []
    for test_file in file_list:
        if test_file["id"] != target_file:
            newer_files += [test_file]
        else:
            break

    return newer_files


def get_filtered_files(file_list):
    remaining_alpha = 3
    remaining_beta = 2
    remaining_release = 2

    filtered_list = []
    for test_file in file_list:
        if test_file["type"] == "release" and remaining_release > 0:
            remaining_release -= 1
        elif test_file["type"] == "beta" and remaining_beta > 0:
            remaining_beta -= 1
        elif test_file["type"] == "alpha" and remaining_alpha > 0:
            remaining_alpha -= 1
        else:
            continue

        filtered_list += [test_file]

    return filtered_list


def get_selectable_options(options):
    release_type_lookup = {"release": "Release", "beta": "Beta", "alpha": "Alpha"}

    selectable_options = []
    for option in options:
        new_val = dict()
        new_val["text"] = "[%s] %s (id %s)" % (release_type_lookup[option["type"]], option["name"], option["id"])
        new_val["value"] = option["id"]
        selectable_options.append(new_val)

    return selectable_options


def is_up_to_date(file_id, file_type, file_list, ignore_less_stable=True):
    types = ['alpha', 'beta', 'release']
    # Get more stable/better files release > beta > alpha
    target_types = None
    if ignore_less_stable and file_type in types:
        target_types = types[types.index(file_type):]
    else:
        target_types = types
    for file_item in file_list:
        if file_item['type'] in target_types:
            return file_item['id'] == file_id

    return False


def get_file_version(file_id, file_list):
    for test_file in file_list:
        if test_file['id'] == file_id:
            return test_file['name']

    return "N/A"

def main():
    sess = requests.session()
    manifest = parseManifest(r"e:\Games\allTheMods 1.10.2\manifest.json")
    newManifest = copy.copy(manifest)

    for i, mod in enumerate(manifest["files"]):
        print("Project %d" % mod['projectID'])
        try:
            v = getNameForNumericalId(sess, mod['projectID'])
        except IndexError as e:
            print("Failed to get name for id %s" % (mod['projectID']))
            continue

        print("* Project name is %s" % v)
        try:
            fs = getFilesForVersion(sess, "1.10.2", mod['projectID'], v)
        except KeyError:
            print("! Failed to get files for MC 1.10.2")
            continue

        if len(fs) < 1:
            print("? No files for 1.10.2 found, checking 1.10.1")
            try:
                fs = getFilesForVersion(sess, "1.10.1", mod['projectID'], v)
            except KeyError:
                print("! Failed to get files for MC 1.10.1")
                continue

        if len(fs) < 1:
            print("? No files for 1.10.1 found, checking 1.10 - this may cause problems...")
            try:
                fs = getFilesForVersion(sess, "1.10", mod['projectID'], v)
            except KeyError:
                print("! Failed to get files for MC 1.10")
                continue

        if len(fs) < 1:
            print("? No files for 1.10 found, checking 1.9.4 - this may cause problems!")
            try:
                fs = getFilesForVersion(sess, "1.9.4", mod['projectID'], v)
            except KeyError:
                print("! Failed to get files for MC 1.9.4")
                continue

        if len(fs) < 1:
            print("? No files found for this mod")
            continue

        print("* Current file version is %s" % get_file_version(mod['fileID'], fs))
        # print("** Filtered files:")
        # for ff in get_filtered_files(fs):
        #     print("** %s" % ff)
        ffs = get_newer_files(get_filtered_files(fs), mod['fileID'])
        # print("** Possible new IDs: ")
        # for opt in get_selectable_options(ffs):
        #     print ("** %s" % opt)
        if len(ffs) < 1:
            print("* Project already up-to-date")
            continue
        x = ffs[0]['id']
        print("* Found new version: %s" % get_file_version(x, fs))
        newManifest["files"][i]['fileID'] = x

    with open(r"e:\Games\allTheMods 1.10.2\new_manifest.json", "w") as newF:
        newF.write(json.dumps(newManifest, indent=2 * ' '))

if __name__ == '__main__':
    main()