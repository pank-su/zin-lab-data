from dataclasses import dataclass


@dataclass
class SubRegion:
    id: int
    region_id: int
    name: str
