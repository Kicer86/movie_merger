
import argparse
import json
import logging
import requests

from collections import defaultdict
from typing import Dict, List

from . import utils


class DuplicatesSource:
    def __init__(self, interruption: utils.InterruptibleProcess):
        self.interruption = interruption

    def collect_duplicates(self) -> Dict[str, List[str]]:
        pass


class JellyfinSource(DuplicatesSource):
    def __init__(self, interruption: utils.InterruptibleProcess, url: str, token: str, storage: str):
        super().__init__(interruption)

        self.url = url
        self.token = token
        self.storage = storage

    def collect_duplicates(self) -> Dict[str, List[str]]:
        endpoint = f"{self.url}"
        headers = {
            "X-Emby-Token": self.token
        }

        paths_by_id = defaultdict(lambda: defaultdict(list))

        def fetchItems(params: Dict[str, str] = {}):
            self.interruption._check_for_stop()
            params.update({"fields": "Path,ProviderIds"})

            response = requests.get(endpoint + "/Items", headers=headers, params=params)
            if response.status_code != 200:
                raise RuntimeError("No access")

            responseJson = response.json()
            items = responseJson["Items"]

            for item in items:
                name = item["Name"]
                id = item["Id"]
                type = item["Type"]

                if type == "Folder":
                    fetchItems(params={"parentId": id})
                elif type == "Movie":
                    providers = item["ProviderIds"]
                    path = item["Path"]

                    for provider, id in providers.items():
                        # ignore collection ID
                        if provider != "TmdbCollection":
                            paths_by_id[provider][id].append((name, path))

        fetchItems()
        duplicates = {}
        warnings = False

        for provider, ids in paths_by_id.items():
            for id, data in ids.items():
                if len(data) > 1:
                    names, paths = zip(*data)

                    # all names should be the same
                    same = all(x == names[0] for x in names)

                    if not same:
                        logging.warning(f"Different names for the same movie ({provider}: {id}):\n{'\n'.join(names)}.\nJellyfin files:\n{'\n'.join(paths)}")
                        warnings = True

                    name = names[0]
                    duplicates[name] = paths

        if warnings:
            raise RuntimeError("Warnings above need to be fixed before continuing")

        return duplicates


class Melter():
    def __init__(self, interruption: utils.InterruptibleProcess, duplicates_source: DuplicatesSource):
        self.interruption = interruption
        self.duplicates_source = duplicates_source

    def melt(self):
        duplicates = self.duplicates_source.collect_duplicates()
        print(json.dumps(duplicates, indent=4))


class RequireJellyfinServer(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if getattr(namespace, "jellyfin_server", None) is None:
            parser.error(
                f"{option_string} requires --jellyfin-server to be specified")
        setattr(namespace, self.dest, values)


def setup_parser(parser: argparse.ArgumentParser):

    jellyfin_group = parser.add_argument_group("Jellyfin source")
    jellyfin_group.add_argument('--jellyfin-server',
                                help='URL to the Jellyfin server which will be used as a source of video files duplicates')
    jellyfin_group.add_argument('--jellyfin-token',
                                action=RequireJellyfinServer,
                                help='Access token (http://server:8096/web/#/dashboard/keys)')
    jellyfin_group.add_argument('--jellyfin-storage',
                                action=RequireJellyfinServer,
                                help='Path to video files base directory')

def run(args):
    interruption = utils.InterruptibleProcess()

    data_source = None
    if args.jellyfin_server:
        data_source = JellyfinSource(interruption=interruption,
                                     url=args.jellyfin_server,
                                     token=args.jellyfin_token,
                                     storage=args.jellyfin_storage)

    melter = Melter(interruption, data_source)
    melter.melt()
