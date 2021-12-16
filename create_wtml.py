#! /usr/bin/env python
#
# Copyright 2021 the .NET Foundation
# Licensed under the MIT License

"""
Combine ``datasets.yml`` and ``hierarchy.yml`` to create ``hips.wtml``.
"""

import yaml

from wwt_data_formats import write_xml_doc
from wwt_data_formats.enums import Bandpass, DataSetType, ProjectionType
from wwt_data_formats.folder import Folder
from wwt_data_formats.imageset import ImageSet


def realize_imageset(info: dict):
    imgset = ImageSet()

    if info["bandpass"] != "Uncategorized":
        imgset.band_pass = Bandpass[info["bandpass"].upper()]

    imgset.base_degrees_per_tile = 180
    imgset.credits = info["credits"]
    imgset.credits_url = info["credits_url"]

    if info["type"] != "Uncategorized":
        imgset.data_set_type = DataSetType[info["type"].upper()]

    # Note that "description" is referenced in docs but not actually available
    # in the app, so it's a useful place for us to stash some helpful metadata:
    imgset.description = f"HiPS List ID: {info['_id']}"
    imgset.file_type = info["file_type"]
    imgset.mean_radius = 1
    imgset.name = info["_name"]
    imgset.projection = ProjectionType.HEALPIX
    imgset.quad_tree_map = "0123"
    imgset.reference_frame = "Sky"
    imgset.thumbnail_url = info["thumbnail_url"]
    imgset.tile_levels = int(info["tile_levels"])
    imgset.width_factor = 1
    imgset.url = info["url"]
    return imgset


def realize_folder(info: dict, imagesets: dict):
    f = Folder(name=info["_name"])
    # TODO: FolderType
    f.group = "Explorer"
    f.searchable = False

    for item in info["children"]:
        if isinstance(item, dict):
            f.children.append(realize_folder(item, imagesets))
        else:
            f.children.append(imagesets[item])

    return f


def entrypoint():
    imagesets_by_id = {}

    with open("datasets.yml", "rt", encoding="utf-8") as f:
        for info in yaml.load_all(f, yaml.SafeLoader):
            imagesets_by_id[info["_id"]] = realize_imageset(info)

    with open("hierarchy.yml", "rt", encoding="utf-8") as f:
        hier = yaml.load(f, yaml.SafeLoader)
        folder = realize_folder(hier, imagesets_by_id)

    with open("hips.wtml", "wt", encoding="utf-8") as f:
        write_xml_doc(
            folder.to_xml(), indent=True, dest_stream=f, dest_wants_bytes=False
        )


if __name__ == "__main__":
    entrypoint()
