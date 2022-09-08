from dataclasses import asdict
from typing import Iterable, List
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

from database import Person
from database import Database


class FirestoreConnector:
    def __init__(self, credentials_file="credentials.json"):
        self.cred = credentials.Certificate(credentials_file)
        firebase_admin.initialize_app(self.cred)

        self.db = firestore.client()

    def get_person(self, id: int, database: Database) -> Person:
        doc_ref = self.db.collection("people").document(str(id))
        doc = doc_ref.get()
        return self.from_dict(doc.to_dict(), id, database)

    def set_person(self, id, person: Person) -> None:
        doc_ref = self.db.collection("people").document(str(id))
        doc_ref.set(self._prepare(person))
    
    def all_people(self, database: Database) -> Iterable[Person]:
        doc_refs = self.db.collection("people").list_documents()
        return (self.from_dict(doc_ref.get().to_dict(), doc_ref.id, database) for doc_ref in doc_refs)
    
    def _prepare(self, person: Person):
        return {
            "partners": [str(x) for x in person.partners],
            "children": [str(x) for x in person.children]
        }
    
    def from_dict(self, dictionary: dict, id: int, database: Database) -> Person:
        if dictionary is None:
            dictionary = {}
        return Person(
            id=int(id),
            database=database,
            partners=[int(partner) for partner in dictionary.get("partners", [])],
            children=[int(child) for child in dictionary.get("children", [])]
        )


class FirestoreDatabase(Database):
    def __init__(self, credentials_file="credentials.json"):
        self.connector = FirestoreConnector(credentials_file)
        super(FirestoreDatabase, self).__init__()
    
    def get_person(self, id: int) -> Person:
        return self.connector.get_person(id, self)
    
    def save_person(self, person: Person) -> None:
        return self.connector.set_person(person.id, person)

    def get_parents(self, id: int) -> List[Person]:
        parents = []
        for person in self.connector.all_people(self):
            if id in person.children:
                parents.append(person)
        return parents
