from dataclasses import dataclass


@dataclass
class Tag:
    id: int
    name: str
    description: str = ""


@dataclass
class TagToCollection:
    col_id: int
    tag_id: int