import xml.etree.ElementTree as ET
from functools import lru_cache
from .utilities import get_gamedata_path
from typing import Optional, Dict


class ItemListEntry:
    def __init__(
        self, item_id: int, name: str, quality: int, achievement_id: Optional[int], tags: list, is_active: bool
    ):
        self.item_id = item_id
        self.name = name
        self.quality = quality
        self.achievement_id = achievement_id
        self.tags = tags
        self.is_active = is_active

    @property
    def quality_str(self) -> str:
        return "★" * self.quality + "☆" * (4 - self.quality)

    def has_tag(self, tag: str) -> bool:
        return tag in self.tags

    @staticmethod
    @lru_cache()
    def load_item_list(platform: str, game_version: str) -> Dict[int, "ItemListEntry"]:
        items_xml_path = get_gamedata_path(platform, game_version, "items.xml")
        stringtable_sta_path = get_gamedata_path(platform, game_version, "stringtable.sta")
        items_metadata_xml_path = get_gamedata_path(platform, game_version, "items_metadata.xml")

        output = {}
        item_achievement_id_mapping = {}
        item_active_mapping = {}
        item_id_to_name_mapping = {}

        with open(items_xml_path, "r", encoding="utf-8") as f, open(
            stringtable_sta_path, "r", encoding="utf-8"
        ) as g:
            items = ET.fromstring(f.read())
            string_table = ET.fromstring(g.read())
            assert items.tag == "items"
            for item in items:
                if item.tag in ["passive", "familiar", "active"]:
                    item_id = int(item.attrib["id"])
                    if "achievement" in item.attrib:
                        assert item_id not in item_achievement_id_mapping
                        item_achievement_id_mapping[item_id] = int(
                            item.attrib["achievement"]
                        )
                    if item.tag == "active":
                        item_active_mapping[item_id] = True
                    else:
                        item_active_mapping[item_id] = False

                    item_name_string_tag = string_table.find(
                        f"./category[@name='Items']/key[@name='{item.attrib['name'][1:]}']"
                    )[0]
                    item_id_to_name_mapping[item_id] = item_name_string_tag.text
                else:
                    assert item.tag in ["trinket", "null"]

        with open(items_metadata_xml_path, "r", encoding="utf-8") as f:
            items_metadata = ET.fromstring(f.read())
            assert items_metadata.tag == "items"

            for item in items_metadata:
                if item.tag == "item":
                    item_id = int(item.attrib["id"])
                    item_name = item_id_to_name_mapping[item_id]
                    item_quality = int(item.attrib["quality"])
                    if item.attrib.__contains__("craftquality"):
                        item_quality = int(item.attrib["craftquality"])
                    item_achievement_id = item_achievement_id_mapping.get(item_id)
                    item_tags = item.attrib["tags"].split(" ")
                    item_is_active = item_active_mapping[item_id]
                    output[item_id] = ItemListEntry(
                        item_id, item_name, item_quality, item_achievement_id, item_tags, item_is_active
                    )

        return output
