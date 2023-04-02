from dataclass_csv import DataclassReader, DataclassWriter
from typing import List, Dict, Tuple

from dclasses.BadData import BadData
from dclasses.Collection import Collection
from dclasses.Collector import Collector
from dclasses.CollectorToCollection import CollectorToCollection
from dclasses.Family import Family
from dclasses.Genus import Genus
from dclasses.Order import Order
from dclasses.VoucherInstitute import VoucherInstitute
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
            vauch_inst_id: int = institutes[el.vauch_inst].id
        # получение коллекторов
        if el.collectors != '':
            cols = re.findall(r"[А-ЯA-Z]\w+", el.collectors)
            for collector in cols:
                if collector not in collectors.keys():
                    collectors[collector] = Collector(len(collectors) + 1, collector, '', '')
        # получение точки
        if el.latitude == 0 and el.longitude == 0:
            pass


    print(collectors)

    print(institutes)

    print(orders)

    print(families)

    print(kindes)
