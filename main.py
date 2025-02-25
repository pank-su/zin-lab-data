from dataclasses import dataclass
import re
from datetime import date, datetime
from os import chdir
from typing import List, Dict, Tuple
from time import sleep

from geopy.geocoders import Nominatim

from pysondb import db

from dataclass_csv import DataclassReader, DataclassWriter

# import dataclasses
from dclasses.Tag import Tag, TagToCollection
from dclasses.Age import Age
from dclasses.CollectionExcelData import CollectionExcelData
from dclasses.Collection import Collection
from dclasses.Collector import Collector
from dclasses.CollectorToCollection import CollectorToCollection
from dclasses.Country import Country
from dclasses.Family import Family
from dclasses.Sex import Sex
from dclasses.Genus import Genus
from dclasses.Kind import Kind
from dclasses.Order import Order
from dclasses.Region import Region
from dclasses.SubRegion import SubRegion
from dclasses.Tissue import Tissue
from dclasses.VoucherInstitute import VoucherInstitute

geolocator = Nominatim(user_agent="zin-data-lab")

posDb = db.getDb("./cache/poscache.json")
geocodeDb = db.getDb("./cache/geocodecache.json")

# вауч. институты
institutes: Dict[str, VoucherInstitute] = {}
# авторы
collectors: Dict[str, Collector] = {}
# коллекция
collection: List[Collection] = []
# коллектор к коллекции
collectors_to_collection: List[CollectorToCollection] = []
# отряды
orders: Dict[str, Order] = {}
# семейства
families: Dict[Tuple[int, str], Family] = {}
# рода
genuses: Dict[Tuple[int, str], Genus] = {}
# виды
kinds: Dict[Tuple[int, str], Kind] = {}
# страны
countries: Dict[str, Country] = {}
# регионы
regions: Dict[Tuple[int, str], Region] = {}
# субрегионы
subregions: Dict[Tuple[int, str], SubRegion] = {}

# ткань, сейчас не используется
tissues: Dict[str, Tissue] = {}

# Эти данные неизменны, поэтому захардкодим
# пол
sexes = {
    "0": Sex(1, "female"),
    "1": Sex(2, "male"),
    "f": Sex(1, "female"),
    "m": Sex(2, "male"),
    "m?": Sex(3, "male?"),
    "m??": Sex(3, "male?"),
    "": None,
    "?": None,
    "_": None,
    "--": None,
    "female": Sex(1, "female"),
    "male": Sex(2, "male"),
}

# возраста
ages = {
    "1": Age(1, "juvenile"),
    "2": Age(2, "subadult"),
    "3": Age(3, "adult"),
    "juv": Age(1, "juvenile"),
    "sad": Age(2, "subadult"),
    "subad": Age(2, "subadult"),
    "ad": Age(3, "adult"),
    "a": Age(3, "adult"),
    "subad/ad": Age(4, "subadult or adult"),
    "": None,
    "_": None,
}

tags = {"rna": Tag(1, "rna")}

tags_to_collection: List[TagToCollection] = []

# плохие значения
invalid_values: List[str] = ["неизвестен", "?", ""]


def get_collection(filename: str) -> List[CollectionExcelData]:
    """Получение коллекции, с помощью списка из csv"""
    with open(filename, "r", encoding="utf-8") as f:
        dt = DataclassReader(f, CollectionExcelData)
        dt.map("ID taxon").to("id_taxon")
        dt.map("CatalogueNumber").to("catalog_number")
        dt.map("Collect_ID").to("collect_id")
        dt.map("Страна").to("country")
        dt.map("Регион").to("region")
        dt.map("Субрегион").to("subregion")
        dt.map("Мест.1").to("place_1")
        dt.map("Мест.2").to("place_2")
        dt.map("Мест.3").to("place_3")
        dt.map("GEN_BANK").to("gen_bank")
        dt.map("Latitude").to("latitude")
        dt.map("Longitude").to("longitude")
        dt.map("Отряд").to("order")
        dt.map("Семейство").to("family")
        dt.map("Род").to("genus")
        dt.map("Вид").to("kind")
        dt.map("Вауч. Инст.").to("vauch_inst")
        dt.map("Вауч. Код").to("vauch_code")
        dt.map("Дата Сбора").to("date_of_collect")
        dt.map("Коллектор").to("collectors")
        dt.map("RNA").to("rna")
        dt.map("Comments").to("comments")
        dt.map("Ткань").to("tissue")
        dt.map("Пол").to("sex")
        dt.map("Возраст").to("age")
        return list(dt)


def process_value(value: str):
    """Обрабатывает значение: если оно недопустимо – возвращает пустую строку,
    иначе удаляет пробелы и приводит к заглавным буквам."""
    return "" if value in invalid_values else value.strip().lower()


def get_or_create(container: map, key, create_func):
    """Если ключа key в словаре container нет – создаёт объект с помощью create_func и добавляет его,
    затем возвращает объект по этому ключу."""
    if key not in container:
        container[key] = create_func()
    return container[key]


@dataclass
class GeoData:
    country: str
    region: str

    def to_json(self):
        return {"country": self.country, "region": self.region}


def geo_data_from_json(obj) -> GeoData:
    return GeoData(obj["country"], obj["region"])


def retry(fun):
    """
    Бесконечный повтор при ошибке с экспоненциальным таймаутом
    """
    secs = 0.8
    while True:
        try:
            sleep(secs)
            data = fun()
            return data
        except Exception as e:
            secs *= 2
            print(e)


def get_geodata_by_raw(raw: dict) -> GeoData:
    """
    Получение GeoData на основе данных из OSM
    """
    # Определяем порядок получения полей для получения "региона"
    location_fields = [
        "state",
        "county",
        "province",
        "region",
        "city",
        "town",
        "village",
    ]

    address = raw["address"]

    # Получаем первую попавшуюся часть иначе пустоту
    sub = ""
    for field in location_fields:
        if field in address:
            sub = address[field]
            break

    return GeoData(address["country"], sub)


def get_geo_by_position(lat: float, lon: float) -> GeoData:
    """Получение геоданных на основе координат с кеширование"""
    obj = {"type": "position", "lat": lat, "lon": lon}
    cached = posDb.getByQuery(obj)
    if len(cached) != 0:
        return geo_data_from_json(cached[0]["data"])
    data = retry(lambda: geolocator.reverse(f"{lat}, {lon}", language="ru"))
    geodata = get_geodata_by_raw(data.raw)
    obj["data"] = geodata.to_json()
    posDb.add(obj)
    return geodata


def get_geo_by_geocode(geocode: str) -> GeoData:
    """Получение геоданных на основе описания с кешированием"""
    obj = {"type": "geocode", "geocode": geocode}
    cached = geocodeDb.getByQuery(obj)
    if len(cached) != 0:
        return geo_data_from_json(cached[0]["data"])
    data = retry(
        lambda: geolocator.geocode(geocode, addressdetails=True, language="ru")
    )
    print(geocode)
    print(data.raw)
    geodata = get_geodata_by_raw(data.raw)
    obj["data"] = geodata.to_json()
    geocodeDb.add(obj)
    return geodata


def normalize_region(region: str):
    """
    Нормализуем данные региона
    """

    if region.endswith(", Республика"):
        return region[:-12]
    if region.startswith("Респ."):
        return region[5:]
    if region == "Восточный Казахстан":
        return "Восточно-Казахстанская область"
    if region.endswith("р-н") or region.endswith("р-он"):
        return region[:-4]

    # синонимы названий
    region_mapping = {
        "x": "",
        "X": "",
        "неизвестно": "",
        "хр. Хан-Ху-Хэя": "",  # хребет, не понятно где может быть
        "Дэгэл-Гол": "",  # не понятно где (очень старая запись)
        "Западный Хэнтей": "Хэнтий",
        "Гоби-Алтайский аймак": "Говь-Алтай",
        "Булганский аймак": "Булган",
        "Араратская долина": "Армавирская область",
        "Зандижан": "Зенджан",
        "Алма-Атинская обл.": "Алматинская область",
        "Зандиван": "Зангилан",
        "Баян-Хонгорский аймак": "Баянхонгор",
        "окр.Улан-Батора": "Улан-Батор",
        "окр. кишлака Зебон": "Зебон",
        "Chamadan": "Хамадан",
        "Саадат-Шах": "Saadat Shahr",
        "Havcheshme": "Hawizeh Marshes",
        "Алайская долина": "Алайский район",
        "окрестности Бишкека": "Бишкек",
        "Халабский хребет": "Лорийская область",
        "Памбакский хр.": "Котайкская область",
        "вост. горы Агарац": "Ширакская область",
        "Кобдосский аймак": "Ховд",
        "Каракаралинский уезд": "Карагандинская область",  # Российская империя
        "Хэнтей": "Хэнтий",
        "кишлак Ташахур": "Шахринавский район",  # это что
        "горный Бадахшан, Памир": "Горно-Бадахшанская автономная область",
        "Убсунурский аймак": "Увс",
        "Сухэ-Баторский аймак": "Сухэ-Батор",
        "Хэнтэйский аймак": "Хэнтий",
        "Зайсанская котловина": "Восточно-Казахстанская область",
        "окр. кишлака Похтакор": "Пахтакор",
        "окр. оз. Косогол": "Хубсугул",
    }
    if region in region_mapping:
        return region_mapping[region]
    if "Пенджикент" in region or "Пенджакент" in region:
        return "Пенджикент"
    if "Худжанда" in region:
        return "Худжанд"
    return region


def add_geodata(countries, regions, data: GeoData):
    """
    Добавляет географические данные в предоставленные словари стран и регионов.
    """

    if data.country not in countries.keys():
        countries[data.country] = Country(len(countries) + 1, data.country)
    country_id = countries[data.country].id
    if (country_id, data.region) not in regions.keys():
        regions[(country_id, data.region)] = Region(
            len(regions) + 1, country_id, data.region
        )
    region_id = regions[(country_id, data.region)].id
    return region_id


if __name__ == "__main__":
    bad_data_collection = get_collection("input_data/collection.csv")
    for row in bad_data_collection:
        year: int = None
        month: int = None
        day: int = None
        country_id = 0
        vauch_inst_id: int = None

        # получение отряда
        order = process_value(row.order)
        order_id = get_or_create(
            orders, order, lambda: Order(len(orders) + 1, order)
        ).id

        # получение семейства
        family = process_value(row.family)
        family_id = get_or_create(
            families,
            (order_id, family),
            lambda: Family(len(families) + 1, order_id, family),
        ).id

        # получение рода
        genus = process_value(row.genus)
        genus_id = get_or_create(
            genuses,
            (family_id, genus),
            lambda: Genus(len(genuses) + 1, family_id, genus),
        ).id

        kind = process_value(row.kind)
        kind_id = get_or_create(
            kinds,
            (genus_id, kind),
            lambda: Kind(len(kinds) + 1, genus_id, kind),
        ).id

        # получение института
        if row.vauch_inst != "":
            if row.vauch_inst not in institutes.keys():
                institutes[row.vauch_inst] = VoucherInstitute(
                    len(institutes) + 1, row.vauch_inst
                )
            vauch_inst_id = institutes[row.vauch_inst].id
        # получение коллекторов
        if row.collectors != "":
            cols = re.findall(
                r"[А-ЯA-Z][а-яА-Яa-z\-]+\s[А-ЯA-Z][а-яА-Яa-z\-]+|[А-ЯA-Z][а-яА-Яa-z\-]+",
                row.collectors,
            )
            for collector in cols:

                if collector not in collectors.keys():
                    if len(collector.split()) > 1:
                        collectors[collector] = Collector(
                            len(collectors) + 1,
                            collector.split()[0],
                            collector.split()[1],
                            "",
                        )
                    else:
                        collectors[collector] = Collector(
                            len(collectors) + 1, collector, "", ""
                        )

                collectors_to_collection.append(
                    CollectorToCollection(collectors[collector].id, row.id_taxon)
                )

        # корректировка значения точки
        point = ""

        if row.latitude != 0 and row.longitude != 0:
            point = f"Point({row.longitude} {row.latitude})"
            print(row.id_taxon)
            data = get_geo_by_position(row.latitude, row.longitude)

            region_id = add_geodata(countries, regions, data)
        else:
            print(row.id_taxon)

            region = (
                row.region
                if row.region.strip() != ""
                else (row.place_2 if (row.place_1 == row.country) else row.place_1)
            )
            query = f"{row.country} {normalize_region(region)}"
            if query == "Грузия Лаго-Наки":
                query = "Россия Лаго-Наки"
            if query == "Россия Виварная":  # 6069
                query = "Россия"
            data = get_geo_by_geocode(query)
            region_id = add_geodata(countries, regions, data)

        # обработка даты
        if row.date_of_collect != "":
            datesStr = re.findall(
                r"\d{1,2}[./]\d{1,2}[./]\d{2,4}|\d{1,2}.\d{4}|\d{4}|28-31\. 07\.2019",
                row.date_of_collect,
            )
            # debug
            if len(datesStr) == 0:
                pass
            else:
                dateStr = datesStr[0]
                if re.fullmatch(r"\d{1,2}[./]\d{1,2}[./]\d{2,4}", dateStr):
                    delim = re.findall(r"[./]", dateStr)[0]
                    date_: date

                    if delim == "/":
                        date_ = datetime.strptime(
                            dateStr, f"%m{delim}%d{delim}%Y"
                        ).date()
                    else:
                        try:
                            date_ = datetime.strptime(
                                dateStr, f"%d{delim}%m{delim}%Y"
                            ).date()
                        except ValueError:
                            date_ = datetime.strptime(
                                dateStr, f"%d{delim}%m{delim}%y"
                            ).date()
                    # print(el)
                    day, month, year = (date_.day, date_.month, date_.year)
                elif len(dateStr) == 4:
                    year = int(dateStr)
                elif re.fullmatch(r"\d{1,2}.\d{4}", dateStr):
                    month, year = map(int, dateStr.split("."))
                elif re.fullmatch(r"28-31\. 07\.2019", dateStr):
                    month = 7
                    year = 2019
                    # Добавить комментарий в поле
                else:
                    pass  # debug

        # получение пола
        sex = sexes[row.sex.lower().strip()]
        sex_id = sexes[row.sex.lower().strip()].id if (sex != None) else None

        # получение возраста экземпляра
        age = ages[row.age.lower()]
        age_id = ages[row.age.lower()].id if (age != None) else None

        if row.vauch_code == "б/н":
            row.vauch_code = ""

        # ТКАНЬ
        if row.tissue.strip() not in tissues.keys():
            tissues[row.tissue.strip()] = Tissue(len(tissues), row.tissue.strip())

        if row.rna != "":
            tags_to_collection.append(TagToCollection(row.id_taxon, tags["rna"].id))

        collection.append(
            Collection(
                row.id_taxon,
                row.collect_id,
                kind_id,
                region_id,
                # subregion_id,
                row.gen_bank,
                point,
                vauch_inst_id,
                row.vauch_code,
                day,
                month,
                year,
                sex_id,
                age_id,
                row.comments,
                ", ".join(
                    [row.place_2, row.place_3]
                ),  # теперь сохраняем только последнии данные о позиции
            )
        )

    # запись всех данных

    chdir("./output")

    def write_to_csv(filename: str, data, data_class):
        """
        Запись CSV в файл
        """
        with open(filename, "w", encoding="utf-8", newline="") as f:
            DataclassWriter(f, data, data_class).write()
    
    write_to_csv("collectors.csv", list(collectors.values()), Collector)
    write_to_csv("countries.csv", list(countries.values()), Country)
    write_to_csv("regions.csv", list(regions.values()), Region)
    write_to_csv("subregions.csv", list(subregions.values()), SubRegion)
    write_to_csv("orders.csv", list(orders.values()), Order)
    write_to_csv("families.csv", list(families.values()), Family)
    write_to_csv("genuses.csv", list(genuses.values()), Genus)
    write_to_csv("kinds.csv", list(kinds.values()), Kind)
    write_to_csv("collection.csv", collection, Collection)
    write_to_csv("collectors_to_collection.csv", collectors_to_collection, CollectorToCollection)
    write_to_csv("institutes.csv", list(institutes.values()), VoucherInstitute)
    write_to_csv("tissues.csv", list(tissues.values()), Tissue)
    write_to_csv("ages.csv", list(filter(lambda age: age != None, set(ages.values()))), Age)
    write_to_csv("sex.csv", list(filter(lambda sex: sex != None, set(sexes.values()))), Sex)
    write_to_csv("tags.csv", list(tags.values()), Tag)
    write_to_csv("tags_to_collection.csv", tags_to_collection, TagToCollection)
