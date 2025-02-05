from dataclasses import dataclass

from dataclass_csv import accept_whitespaces


@accept_whitespaces
@dataclass
class CollectionExcelData:
    """Класс, который описывает данные из исходной таблицы"""
    id_taxon: int
    catalog_number: str = '' # для новых данных нужно значение по умолчанию
    family: str = ''
    order: str = ''
    vauch_inst: str = ''
    vauch_code: str = ''
    date_of_collect: str = ''
    collectors: str = ''
    rna: str = ''
    comments: str = ''
    sex: str = '?'
    age: str = ''
    tissue: str = ''  # Ткань
    collect_id: str = ''
    genus: str = '?'
    kind: str = '?'
    country: str = 'Россия'
    region: str = ''
    subregion: str = ''
    place_1: str = ''
    place_2: str = ''
    place_3: str = ''
    gen_bank: str = ''
    latitude: float = 0
    longitude: float = 0
