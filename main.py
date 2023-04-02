from dataclass_csv import DataclassReader, DataclassWriter
from typing import List, Dict, Tuple

from dclasses.Age import Age
from dclasses.BadData import BadData
from dclasses.Collection import Collection
from dclasses.Collector import Collector
from dclasses.CollectorToCollection import CollectorToCollection
from dclasses.Country import Country
from dclasses.Family import Family
from dclasses.Gender import Gender
from dclasses.Genus import Genus
from dclasses.Order import Order
from dclasses.Region import Region
from dclasses.SubRegion import SubRegion
from dclasses.VoucherInstitute import VoucherInstitute
from datetime import date, datetime
import re

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
kindes: Dict[Tuple[int, str], Genus] = {}
# страны
countries: Dict[str, Country] = {"Россия": Country(1, "Россия")}
# регионы
regions: Dict[Tuple[int, str], Region] = {}
# субрегионы
subregions: Dict[Tuple[int, str], SubRegion] = {}
# возраст животного
ages: Dict[int, Age]
# пол
genders = {
    "0": Gender(1, "")
}


def get_collection(filename: str) -> List[BadData]:
    """Получение коллекции, с помощью списка из csv"""
    with open(filename, "r", encoding="utf-8") as f:
        dt = DataclassReader(f, BadData)
        dt.map('ID taxon').to('id_taxon')
        dt.map('CatalogueNumber').to('catalog_number')
        dt.map('Collect_ID').to('collect_id')
        dt.map("Род").to("genus")
        dt.map("Вид").to("kind")
        dt.map("Страна").to("country")
        dt.map("Регион").to("region")
        dt.map("Субрегион").to("subregion")
        dt.map("Мест.1").to("place_1")
        dt.map("Мест.2").to("place_2")
        dt.map("Мест.3").to("place_3")
        dt.map("GEN_BANK").to("gen_bank")
        dt.map("Latitude").to("latitude")
        dt.map("Longitude").to("longitude")
        dt.map("Семейство").to("family")
        dt.map("Отряд").to("order")
        dt.map("Вауч. Инст.").to("vauch_inst")
        dt.map("Вауч. Код").to("vauch_code")
        dt.map("Дата Сбора").to("date_of_collect")
        dt.map("Коллектор").to("collectors")
        dt.map("RNA").to("rna")
        dt.map("Comments").to("comments")
        dt.map("Ткань").to("tissue")
        dt.map("Пол").to("gender")
        dt.map("Возраст").to("age")
        return list(dt)


if __name__ == '__main__':
    bad_data_collection = get_collection("input_data/collection.csv")
    for el in bad_data_collection:
        year: int = 0
        month: int = 0
        day: int = 0
        country_id = 0
        vauch_inst_id: int = 0
        # получение отряда
        if el.order.lower() not in orders.keys():
            orders[el.order.lower()] = Order(len(orders) + 1, el.order.lower())
        order_id = orders[el.order.lower()].id
        # получение семейства
        if (order_id, el.family.lower()) not in families.keys():
            families[(order_id, el.family.lower())] = Family(len(families) + 1, order_id, el.family.lower())
        family_id = families[(order_id, el.family.lower())].id

        # получение рода
        if (family_id, el.genus.lower()) not in genuses.keys():
            genuses[(family_id, el.genus.lower())] = Genus(len(genuses) + 1, family_id, el.genus.lower())
        genus_id = genuses[(family_id, el.genus.lower())].id

        # получение видов
        if (genus_id, el.kind.lower()) not in kindes.keys():
            kindes[(genus_id, el.kind.lower())] = Genus(len(kindes) + 1, genus_id, el.kind.lower())
        kind_id = kindes[(genus_id, el.kind.lower())].id

        # получение института
        if el.vauch_inst != '':
            if el.vauch_inst not in institutes.keys():
                institutes[el.vauch_inst] = VoucherInstitute(len(institutes) + 1, el.vauch_inst)
            vauch_inst_id = institutes[el.vauch_inst].id
        # получение коллекторов
        if el.collectors != '':
            cols = re.findall(r"[А-ЯA-Z]\w+", el.collectors)
            for collector in cols:
                if collector not in collectors.keys():
                    collectors[collector] = Collector(len(collectors) + 1, collector, '', '')

        # корректировка значения точки
        point = ""
        if el.latitude != 0 and el.longitude != 0:
            point = f"Point({el.latitude}, {el.longitude})"
        if el.date_of_collect != '':
            datesStr = re.findall(r"\d{1,2}[./]\d{1,2}[./]\d{2,4}|\d{1,2}.\d{4}|\d{4}|28-31\. 07\.2019",
                                  el.date_of_collect)
            # if для debug патерна
            if len(datesStr) == 0:
                pass
            else:
                dateStr = datesStr[0]
                if re.fullmatch(r"\d{1,2}[./]\d{1,2}[./]\d{2,4}", dateStr):
                    delim = re.findall(r"[./]", dateStr)[0]
                    date_: date

                    if delim == "/":
                        date_ = datetime.strptime(dateStr, f"%m{delim}%d{delim}%Y").date()
                    else:
                        try:
                            date_ = datetime.strptime(dateStr, f"%d{delim}%m{delim}%Y").date()
                        except ValueError:
                            date_ = datetime.strptime(dateStr, f"%d{delim}%m{delim}%y").date()
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
                    pass  # to debug
        # Получение страны
        if el.country == "":
            country_id = countries["Россия"].id
        else:
            if el.country not in countries.keys():
                countries[el.country] = Country(len(countries) + 1, el.country)
            country_id = countries[el.country].id
        # получение региона
        if (country_id, el.region) not in regions.keys():
            regions[(country_id, el.region)] = Region(len(regions) + 1, order_id, el.region)
        region_id = regions[(country_id, el.region)].id

        # получение субрегиона
        if (region_id, el.subregion) not in subregions.keys():
            subregions[(region_id, el.subregion)] = SubRegion(len(subregions) + 1, region_id, el.subregion)
        subregion_id = subregions[(region_id, el.subregion)].id

        collection.append(
            Collection(el.id_taxon, el.catalog_number, el.collect_id, kind_id, subregion_id, el.gen_bank, point,
                       vauch_inst_id, el.vauch_code, day, month, year, el.rna != "", 0, 0, el.comments,
                       ", ".join([el.place_1, el.place_2, el.place_3])))

    print(subregions)
    print(collectors)

    print(institutes)

    print(orders)

    print(families)

    print(kindes)
