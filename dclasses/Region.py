from dataclasses import dataclass


@dataclass
class Region:
    id: int
    country_id: int
    name: str
