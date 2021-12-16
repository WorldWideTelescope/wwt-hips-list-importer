#! /usr/bin/env python
#
# Copyright 2021 the .NET Foundation
# Licensed under the MIT License

import argparse
from datetime import datetime
from xml.etree.ElementTree import Element
import xml.etree.ElementTree as et
import requests
import yaml

PLANETS_CATEGORY_NAME = "Planets & Moons"


class Convert:
    toc = False
    "If true, emit table-of-contents rather than WTML."

    yaml = False
    "If true, emit flat YAML file rather than WTML."

    def __init__(self, toc=False, yaml=False):
        self.toc = toc
        self.yaml = yaml

        self.root = et.Element("Folder", self.get_default_attributes("HIPS Surveys"))
        self.images = et.SubElement(
            self.root, "Folder", self.get_default_attributes("Images")
        )
        self.catalogs = et.SubElement(
            self.root, "Folder", self.get_default_attributes("Catalogs")
        )
        self.heatmaps = et.SubElement(
            self.root, "Folder", self.get_default_attributes("Heatmaps")
        )

        self.images_gamma = et.SubElement(
            self.images, "Folder", self.get_default_attributes("Gamma")
        )
        self.images_xray = et.SubElement(
            self.images, "Folder", self.get_default_attributes("XRay")
        )
        self.images_uv = et.SubElement(
            self.images, "Folder", self.get_default_attributes("Ultraviolet")
        )
        self.images_visible = et.SubElement(
            self.images, "Folder", self.get_default_attributes("Visible")
        )
        self.images_ir = et.SubElement(
            self.images, "Folder", self.get_default_attributes("IR")
        )
        self.images_microwave = et.SubElement(
            self.images, "Folder", self.get_default_attributes("Microwave")
        )
        self.images_radio = et.SubElement(
            self.images, "Folder", self.get_default_attributes("Radio")
        )
        self.images_planets = et.SubElement(
            self.images, "Folder", self.get_default_attributes(PLANETS_CATEGORY_NAME)
        )
        self.images_uncategorized = et.SubElement(
            self.images, "Folder", self.get_default_attributes("Uncategorized")
        )

        self.heatmaps_by_object = et.SubElement(
            self.heatmaps, "Folder", self.get_default_attributes("By Object Type")
        )
        self.heatmaps_by_date = et.SubElement(
            self.heatmaps, "Folder", self.get_default_attributes("By Date")
        )

        self.add_version_dependent(self.root, False)
        self.add_version_dependent(self.images, False)
        self.add_version_dependent(self.catalogs, False)
        self.add_version_dependent(self.images_gamma, False)
        self.add_version_dependent(self.images_xray, False)
        self.add_version_dependent(self.images_radio, False)
        self.add_version_dependent(self.images_ir, False)
        self.add_version_dependent(self.images_uv, False)
        self.add_version_dependent(self.images_visible, False)
        self.add_version_dependent(self.images_microwave, False)
        self.add_version_dependent(self.images_planets, False)
        self.add_version_dependent(self.images_uncategorized, False)
        self.add_version_dependent(self.heatmaps, False)
        self.add_version_dependent(self.heatmaps_by_date, False)
        self.add_version_dependent(self.heatmaps_by_object, False)

        if toc:
            self.toc_data = {}
        if yaml:
            self.yaml_data = []

    def add_version_dependent(self, parent: Element, is_dependent: bool):
        version_dependent = et.Element("VersionDependent")
        version_dependent.text = str(is_dependent).lower()
        parent.insert(0, version_dependent)

    def write_file(self, out_file: str):
        tree = et.ElementTree(self.root)
        et.indent(tree, space="  ", level=0)
        tree.write(out_file, encoding="utf-8", xml_declaration=True)

    def get_default_attributes(self, name: str):
        return {
            "MSRCommunityId": "0",
            "MSRComponentId": "0",
            "Permission": "0",
            "Name": name,
            "Group": "Explorer",
            "Searchable": "False",
            "Type": "Sky",
        }

    def get_element_attribute(self, element: Element, attribute: str):
        if attribute in element:
            return element[attribute]
        else:
            return ""

    def get_credits_url(self, element: Element):
        credits_url = self.get_element_attribute(element, "obs_copyright_url")
        if isinstance(credits_url, list):
            return (
                self.get_element_attribute(element, "hips_service_url").strip("/")
                + "/properties"
            )
        else:
            return credits_url

    def get_credits(self, element: Element):
        credits = self.get_element_attribute(element, "obs_copyright")
        if isinstance(credits, list):
            return ", ".join(credits)
        else:
            return credits

    def get_name(self, element: Element):
        name = self.get_element_attribute(element, "obs_title")
        if not name:
            name = self.get_element_attribute(element, "ID")

        return name

    def get_file_type(self, element: Element):
        file_formats = self.get_element_attribute(element, "hips_tile_format")

        file_formats_arr = file_formats.split(" ")

        if "fits" in file_formats_arr and len(file_formats_arr) > 1:
            file_formats_arr.remove("fits")
            file_formats = " ".join(file_formats_arr)
            file_formats += " fits"

        return file_formats

    def get_bandpass_name(self, element: Element):
        regime = self.get_element_attribute(element, "obs_regime")

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
            return "IR"
        elif "uv" in regime or "ultraviolet" in regime:
            return "Ultraviolet"
        elif "optical" in regime:
            return "Visible"
        elif "millimeter" in regime or "microwave" in regime:
            return "Microwave"
        else:
            hips_frame = self.get_element_attribute(element, "hips_frame").lower()
            if (
                "galactic" in hips_frame
                or "ecliptic" in hips_frame
                or "equatorial" in hips_frame
            ):
                return "Uncategorized"
            else:
                return PLANETS_CATEGORY_NAME

    def convert(self, json_object):
        for element in json_object:
            type = self.get_element_attribute(element, "dataproduct_type")
            id = self.get_element_attribute(element, "ID")

            if id == "CDS/P/DM/simbad-biblio/allObjects":
                self.add_heatmap_container(element)
            elif "heatmap" in self.get_element_attribute(element, "client_category"):
                self.add_heatmap(element)
            elif type == "cube":
                continue
            elif type == "image":
                self.add_image(element)
            elif type == "catalog":
                self.add_catalog(element)

        return self

    def add_catalog(self, element: Element):
        self.add_image_set(element, self.catalogs)

    def add_image(self, element: Element):
        regime = self.get_element_attribute(element, "obs_regime")

        if isinstance(regime, list):
            regime = regime[0]

        regime = regime.lower()

        if "radio" in regime:
            self.add_image_set(element, self.images_radio)
        elif "gamma-ray" in regime or "gamma" in regime:
            self.add_image_set(element, self.images_gamma)
        elif "x-ray" in regime or "xray" in regime:
            self.add_image_set(element, self.images_xray)
        elif "infrared" in regime or "ir" in regime:
            self.add_image_set(element, self.images_ir)
        elif "uv" in regime or "ultraviolet" in regime:
            self.add_image_set(element, self.images_uv)
        elif "optical" in regime:
            self.add_image_set(element, self.images_visible)
        elif "millimeter" in regime or "microwave" in regime:
            self.add_image_set(element, self.images_microwave)
        else:
            hips_frame = self.get_element_attribute(element, "hips_frame").lower()
            if (
                "galactic" in hips_frame
                or "ecliptic" in hips_frame
                or "equatorial" in hips_frame
            ):
                self.add_image_set(element, self.images_uncategorized)
            else:
                self.add_image_set(element, self.images_planets)

    def add_heatmap(self, element: Element):
        category = self.get_element_attribute(element, "client_category")

        if "heatmaps by object types" in category:
            self.add_image_set(element, self.heatmaps_by_object)
        else:
            self.add_image_set(element, self.heatmaps_by_date)

    def add_heatmap_container(self, element: Element):
        self.add_image_set(element, self.heatmaps)

    def add_image_set(self, element: Element, parent: Element):
        if self.toc:
            self.toc_data[element["ID"]] = self.get_name(element)
            return

        bandpass_name = self.get_bandpass_name(element)

        dataset_type = "Sky"
        if self.get_bandpass_name(element) == PLANETS_CATEGORY_NAME:
            if "panorama" in self.get_element_attribute(element, "obs_title").lower():
                dataset_type = "Panorama"
            else:
                dataset_type = "Planet"

        url = (
            self.get_element_attribute(element, "hips_service_url").strip("/")
            + "/Norder{0}/Dir{1}/Npix{2}"
        )

        tile_levels = self.get_element_attribute(element, "hips_order")
        name = self.get_name(element)
        file_type = self.get_file_type(element)
        credits = self.get_credits(element)
        credits_url = self.get_credits(element)
        thumbnail_url = (
            self.get_element_attribute(element, "hips_service_url").strip("/")
            + "/preview.jpg"
        )

        if self.yaml:
            info = {
                "_id": element["ID"],
                "_name": name,
                "bandpass": bandpass_name,
                "credits": credits,
                "credits_url": credits_url,
                "file_type": file_type,
                "tile_levels": tile_levels,
                "thumbnail_url": thumbnail_url,
                "type": dataset_type,
                "url": url,
            }
            self.yaml_data.append(info)
            return

        image_set = et.SubElement(
            parent,
            "ImageSet",
            DemUrl="",
            MSRCommunityId="0",
            MSRComponentId="0",
            Permission="0",
            Generic="False",
            DataSetType=dataset_type,
            BandPass=bandpass_name,
            Url=url,
            TileLevels=tile_levels,
            WidthFactor="1",
            Sparse="False",
            Rotation="0",
            QuadTreeMap="0123",
            Projection="Healpix",
            Name=name,
            FileType=file_type,
            CenterY="0",
            CenterX="0",
            BottomsUp="False",
            StockSet="False",
            ElevationModel="False",
            OffsetX="0",
            OffsetY="0",
            BaseTileLevel="0",
            BaseDegreesPerTile="180",
            ReferenceFrame="Sky",
            MeanRadius="1",
        )

        et.SubElement(image_set, "Credits").text = credits
        et.SubElement(image_set, "CreditsUrl").text = credits_url
        et.SubElement(image_set, "ThumbnailUrl").text = thumbnail_url

    def emit_toc(self, stream):
        print(f"updated: {datetime.utcnow().isoformat()}\n", file=stream)

        for id, name in sorted(self.toc_data.items(), key=lambda t: t[0]):
            print(f"{id}\t{name}", file=stream)

    def emit_yaml(self, stream):
        yaml.dump_all(
            sorted(self.yaml_data, key=lambda r: r["_id"]),
            stream=stream,
            allow_unicode=True,
            sort_keys=True,
            indent=2,
        )


def entrypoint():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--toc",
        action="store_true",
        help="Emit table-of-contents file rather than WTML",
    )
    parser.add_argument(
        "--yaml",
        action="store_true",
        help="Emit flat YAML data file rather than WTML",
    )

    settings = parser.parse_args()

    conv = Convert(toc=settings.toc, yaml=settings.yaml)

    hips_list_json = requests.get(
        "http://aladin.u-strasbg.fr/hips/globalhipslist?fmt=json"
    ).json()
    conv.convert(hips_list_json)

    if settings.toc:
        with open("toc.txt", "wt") as f:
            conv.emit_toc(f)
    elif settings.yaml:
        with open("datasets.yml", "wt") as f:
            conv.emit_yaml(f)
    else:
        conv.write_file("hips-list.wtml")


if __name__ == "__main__":
    entrypoint()
