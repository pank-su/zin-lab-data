from dataclasses import dataclass


@dataclass
class Collection:
    id: int
    collect_id: str
    kind_id: int
    region_id: int
    gen_bank_id: str
    point: str
    vouch_inst_id: int
    vouch_id: str
    day: int
    month: int
    year: int
    sex_id: int
    age_id: int
    comment: str
    geo_comment: str
