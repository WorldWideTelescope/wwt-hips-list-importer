#! /usr/bin/env python
#
# Copyright 2021 the .NET Foundation
# Licensed under the MIT License

from datetime import datetime
import requests
import yaml

PLANETS_CATEGORY_NAME = "Planets & Moons"


class Folder(object):
    def __init__(self, name, name_map):
        self.name = name
        self.children = []  # each item is either a Folder or string dataset ID
        name_map[name] = self

    def add_subfolder(self, name, name_map):
        child = Folder(name, name_map)
        self.children.append(child)
        return child

    def add_subfolders(self, name_map, *names):
        for name in names:
            self.add_subfolder(name, name_map)

    def as_yaml(self):
        yaml_children = []
        d = {"_name": self.name, "children": yaml_children}

        for c in self.children:
            if isinstance(c, Folder):
                yaml_children.append(c.as_yaml())
            else:
                yaml_children.append(c)

        return d

    @classmethod
    def stub_folders(cls):
        name_map = {}

        root = Folder("HiPS Surveys", name_map)

        images = root.add_subfolder("Images", name_map)
        _catalogs = root.add_subfolder("Catalogs", name_map)
        heatmaps = root.add_subfolder("Heatmaps", name_map)

        images.add_subfolders(
            name_map,
            "Gamma",
            "XRay",
            "Ultraviolet",
            "Visible",
            "Infrared",
            "Microwave",
            "Radio",
            PLANETS_CATEGORY_NAME,
            "Uncategorized",
        )

        heatmaps.add_subfolders(
            name_map,
            "By Object Type",
            "By Date",
        )

        return name_map

    @classmethod
    def load_hierarchy(cls):
        name_map = {}
        seen_datasets = set()

        def load_one(info):
            f = Folder(info["_name"], name_map)

            for item in info["children"]:
                if isinstance(item, dict):
                    f.children.append(load_one(item))
                else:
                    seen_datasets.add(item)
                    f.children.append(item)

            return f

        with open("hierarchy.yml", "rt", encoding="utf-8") as f:
            info = yaml.load(f, yaml.SafeLoader)
            root = load_one(info)

        return name_map, seen_datasets


class Convert(object):
    def __init__(self):
        self.folders_by_name, self.seen_datasets = Folder.load_hierarchy()
        self.image_data = []

        self.root = self.folders_by_name["HiPS Surveys"]
        self.images = self.folders_by_name["Images"]
        self.catalogs = self.folders_by_name["Catalogs"]
        self.heatmaps = self.folders_by_name["Heatmaps"]
        self.images_gamma = self.folders_by_name["Gamma"]
        self.images_xray = self.folders_by_name["XRay"]
        self.images_uv = self.folders_by_name["Ultraviolet"]
        self.images_visible = self.folders_by_name["Visible"]
        self.images_ir = self.folders_by_name["Infrared"]
        self.images_microwave = self.folders_by_name["Microwave"]
        self.images_radio = self.folders_by_name["Radio"]
        self.images_planets = self.folders_by_name[PLANETS_CATEGORY_NAME]
        self.images_uncategorized = self.folders_by_name["Uncategorized"]
        self.heatmaps_by_object = self.folders_by_name["By Object Type"]
        self.heatmaps_by_date = self.folders_by_name["By Date"]

    # High-level processing of the input list

    def convert(self, json_object: list):
        for info in json_object:
            type = info.get("dataproduct_type", "")
            id = info.get("ID", "")

            if id == "CDS/P/DM/simbad-biblio/allObjects":
                self.add_heatmap_container(info)
            elif "heatmap" in info.get("client_category", ""):
                self.add_heatmap(info)
            elif type == "cube":
                continue
            elif type == "image":
                self.add_image(info)
            elif type == "catalog":
                self.add_catalog(info)

        return self

    def add_catalog(self, info: dict):
        self.add_image_set(info, self.catalogs)

    def add_image(self, info: dict):
        regime = info.get("obs_regime", "")

        if isinstance(regime, list):
            regime = regime[0]

        regime = regime.lower()

        if "radio" in regime:
            self.add_image_set(info, self.images_radio)
        elif "gamma-ray" in regime or "gamma" in regime:
            self.add_image_set(info, self.images_gamma)
        elif "x-ray" in regime or "xray" in regime:
            self.add_image_set(info, self.images_xray)
        elif "infrared" in regime or "ir" in regime:
            self.add_image_set(info, self.images_ir)
        elif "uv" in regime or "ultraviolet" in regime:
            self.add_image_set(info, self.images_uv)
        elif "optical" in regime:
            self.add_image_set(info, self.images_visible)
        elif "millimeter" in regime or "microwave" in regime:
            self.add_image_set(info, self.images_microwave)
        else:
            hips_frame = info.get("hips_frame", "").lower()
            if (
                "galactic" in hips_frame
                or "ecliptic" in hips_frame
                or "equatorial" in hips_frame
            ):
                self.add_image_set(info, self.images_uncategorized)
            else:
                self.add_image_set(info, self.images_planets)

    def add_heatmap(self, info: dict):
        category = info.get("client_category", "")

        if "heatmaps by object types" in category:
            self.add_image_set(info, self.heatmaps_by_object)
        else:
            self.add_image_set(info, self.heatmaps_by_date)

    def add_heatmap_container(self, info: dict):
        self.add_image_set(info, self.heatmaps)

    def add_image_set(self, info: dict, folder: Folder):
        ident = info["ID"]

        bandpass_name = self.get_bandpass_name(info)

        dataset_type = "Sky"
        if bandpass_name == PLANETS_CATEGORY_NAME:
            bandpass_name = "Uncategorized"

            if "panorama" in info.get("obs_title", "").lower():
                dataset_type = "Panorama"
            else:
                dataset_type = "Planet"

        url = info.get("hips_service_url", "").strip("/") + "/Norder{0}/Dir{1}/Npix{2}"
        tile_levels = info.get("hips_order", "")
        name = self.get_name(info)
        file_type = self.get_file_type(info)
        credits = self.get_credits(info)
        credits_url = self.get_credits_url(info)
        thumbnail_url = info.get("hips_service_url", "").strip("/") + "/preview.jpg"

        # Record the information in three ways:
        #
        # - Simple table-of-contents record
        # - Metadata of interest in `datasets.yml` for manual review and editing
        # - Add into folder hierarchy if not already there

        self.image_data.append(
            {
                "_id": ident,
                "_name": name,
                "bandpass": bandpass_name,
                "credits": credits,
                "credits_url": credits_url,
                "file_type": file_type,
                "tile_levels": int(tile_levels),
                "thumbnail_url": thumbnail_url,
                "type": dataset_type,
                "url": url,
            }
        )

        if ident not in self.seen_datasets:
            folder.children.append(ident)

    # Low-level data munging helpers

    def get_credits_url(self, info: dict):
        credits_url = info.get("obs_copyright_url", "")
        if isinstance(credits_url, list):
            return info.get("hips_service_url", "").strip("/") + "/properties"
        else:
            return credits_url

    def get_credits(self, info: dict):
        credits = info.get("obs_copyright", "")
        if isinstance(credits, list):
            return ", ".join(credits)
        else:
            return credits

    def get_name(self, info: dict):
        name = info.get("obs_title", "")
        if not name:
            name = info.get("ID", "")

        return name

    def get_file_type(self, info: dict):
        file_formats = info.get("hips_tile_format", "")

        file_formats_arr = file_formats.split(" ")

        if "fits" in file_formats_arr and len(file_formats_arr) > 1:
            file_formats_arr.remove("fits")
            file_formats = " ".join(file_formats_arr)
            file_formats += " fits"

        return file_formats

    def get_bandpass_name(self, info: dict):
        regime = info.get("obs_regime", "")

        if isinstance(regime, list):
            regime = regime[0]

        regime = regime.lower()

        if "radio" in regime:
            return "Radio"
        elif "gamma-ray" in regime or "gamma" in regime:
            return "Gamma"
        elif "x-ray" in regime or "xray" in regime:
            return "XRay"
        elif "infrared" in regime or "ir" in regime:
            return "Infrared"
        elif "uv" in regime or "ultraviolet" in regime:
            return "Ultraviolet"
        elif "optical" in regime:
            return "Visible"
        elif "millimeter" in regime or "microwave" in regime:
            return "Microwave"
        else:
            hips_frame = info.get("hips_frame", "").lower()
            if (
                "galactic" in hips_frame
                or "ecliptic" in hips_frame
                or "equatorial" in hips_frame
            ):
                return "Uncategorized"
            else:
                return PLANETS_CATEGORY_NAME

    # Writing out the processed data

    def emit_toc(self, stream):
        print(f"updated: {datetime.utcnow().isoformat()}\n", file=stream)

        for info in sorted(self.image_data, key=lambda d: d["_id"]):
            print(f"{info['_id']}\t{info['_name']}", file=stream)

    def emit_image_data(self, stream):
        yaml.dump_all(
            sorted(self.image_data, key=lambda r: r["_id"]),
            stream=stream,
            allow_unicode=True,
            sort_keys=True,
            indent=2,
        )

    def emit_hierarchy(self, stream):
        yaml.dump(
            self.root.as_yaml(),
            stream=stream,
            allow_unicode=True,
            indent=2,
        )


def entrypoint():
    hips_list_json = requests.get(
        "http://aladin.u-strasbg.fr/hips/globalhipslist?fmt=json"
    ).json()

    conv = Convert()
    conv.convert(hips_list_json)

    with open("toc.txt", "wt", encoding="utf-8") as f:
        conv.emit_toc(f)

    with open("datasets.yml", "wt", encoding="utf-8") as f:
        conv.emit_image_data(f)

    with open("hierarchy.yml", "wt", encoding="utf-8") as f:
        conv.emit_hierarchy(f)


if __name__ == "__main__":
    entrypoint()
