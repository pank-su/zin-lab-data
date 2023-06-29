from dataclasses import dataclass


@dataclass
class Gender:
    id: int
    name: str

    def __hash__(self):
        return hash(self.name)