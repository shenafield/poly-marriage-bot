from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Mapping, Tuple


@dataclass
class Person:
    id: int
    database: "Database"
    partners: list[int] = field(default_factory=list)
    children: list[int] = field(default_factory=list)

    def dump(self):
        self.database.save_person(self)
    
    def add_partner(self, person: "Person"):
        self.partners.append(person.id)
        person.partners.append(self.id)
        self.dump()
        person.dump()
    
    def remove_partner(self, person: "Person"):
        self.partners.remove(person.id)
        person.partners.remove(self.id)
        self.dump()
        person.dump()
    
    def adopt(self, person: "Person"):
        self.children.append(person.id)
        self.dump()
    
    def disown(self, person: "Person"):
        self.children.remove(person.id)
        self.dump()
    
    def get_children(self):
        return [self.database.get_person(child) for child in self.children]
    
    def get_parents(self):
        return self.database.get_parents(self.id)
    
    def get_partners(self):
        return self.database.get_partners(self.id)

class Database(ABC):
    @abstractmethod
    def get_person(self, id: int) -> Person:
        pass

    @abstractmethod
    def save_person(self, person: Person) -> None:
        pass

    @abstractmethod
    def get_parents(self, id: int) -> List[Person]:
        pass

    def get_partner_ring(self, person: int, initial: List[int] = []) -> Tuple[Mapping[int, List[int]], List[int]]:
        output = initial + [person]
        map = {}
        immediate = self.get_person(person).partners
        map[person] = immediate
        for partner in immediate:
            if partner not in initial:
                output.append(partner)
                map_partner, distant = self.get_partner_ring(partner, output)
                output += distant
                map[partner] = distant
                for a, b in map_partner.items():
                    map[a] = b
        return map, list(set(output))

    def get_partners(self, id: int) -> Mapping[Person, List[Person]]:
        map, ring = self.get_partner_ring(id)
        return {
            id: [self.get_person(partner) for partner in partners] for id, partners in map.items()
        }, [self.get_person(id) for id in map.keys()]
