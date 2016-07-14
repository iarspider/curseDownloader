import argparse
import copy
from pathlib import Path

import requests
import simplejson as json

__author__ = 'james'

parser = argparse.ArgumentParser(description="Update Curse modpack manifest")
parser.add_argument("--manifest", help="manifest.json file from unzipped pack")
parser.add_argument("--overwrite", help="replace manifest.json with updated version", action='store_true')
# parser.add_argument("--nogui", dest="gui", action="store_false", help="Do not use gui to to select manifest")
args, unknown = parser.parse_known_args()

aliases = {'1.10.2': ['1.10.2', '1.10.1', '1.10', '1.9.4'], '1.10.1': ['1.10.1', '1.10', '1.9.4'],
           '1.10': ['1.10', '1.9.4']}


def parse_manifest(manifest):
    manifest_path = Path(manifest)

    manifest_text = manifest_path.open().read()
    manifest_text = manifest_text.replace('\r', '').replace('\n', '')

    manifest_json = json.loads(manifest_text)
    return manifest_json


def get_name_for_numerical_id(session, numericalid):
    project_response = session.get("http://minecraft.curseforge.com/mc-mods/%s" % numericalid, stream=True)
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


def get_files_for_version(session, mcversion, modid, modname):
    files_json_response = session.get("http://widget.mcf.li/mc-mods/minecraft/%s.json" % modname)
    if files_json_response.status_code != 200:
        files_json_response = session.get("http://widget.mcf.li/mc-mods/minecraft/%d-%s.json" % (modid, modname))
    try:
        files_json = files_json_response.json()
    except json.scanner.JSONDecodeError:
        print("! Invalid json downloaded from %s" % files_json_response.url)
        return []

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
    target_types = types
    if ignore_less_stable and file_type in types:
        target_types = types[types.index(file_type):]

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
    manifest = parse_manifest(args.manifest)
    new_manifest = copy.copy(manifest)

    for i, mod in enumerate(manifest["files"]):
        print("Project %d" % mod['projectID'])
        try:
            v = get_name_for_numerical_id(sess, mod['projectID'])
        except IndexError:
            print("Failed to get name for id %s" % (mod['projectID']))
            continue

        print("* Project name is %s" % v)
        try:
            mc_versions = aliases[manifest['minecraft']['version']]
        except KeyError:
            mc_versions = [manifest['minecraft']['version']]

        fs = None
        for mc_version in mc_versions:
            try:
                # print("** Checking MC version: %s" % mc_version)
                fs = get_files_for_version(sess, mc_version, mod['projectID'], v)
                if len(fs) > 0:
                    break
            except KeyError:
                # print("! Failed to get files for MC %s" % mc_version)
                continue

        if fs is None or len(fs) < 1:
            print("! No files found for this mod")
            continue

        # print("** Found %d files" % len(fs))
        # for f in fs:
        #     print("*** %s" % f)
        # print("** Current file ID: %d" % mod['fileID'])
        print("* Current file version is %s" % get_file_version(mod['fileID'], fs))
        ffs = get_newer_files(get_filtered_files(fs), mod['fileID'])
        if len(ffs) < 1:
            print("* Project already up-to-date")
            continue

        x = ffs[0]['id']
        print("* Found new version: %s" % get_file_version(x, fs))
        new_manifest["files"][i]['fileID'] = x

    if args.overwrite:
        new_filename = args.manifest
    else:
        manifest_path = Path(args.manifest).resolve().parent
        manifest_name = 'new_' + str(Path(args.manifest).resolve().name)
        new_filename = manifest_path / manifest_name

    with open(str(new_filename), "w") as newF:
        newF.write(json.dumps(new_manifest, indent=2 * ' '))


if __name__ == '__main__':
    main()
