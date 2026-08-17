from dataclasses import dataclass





@dataclass
class Employee:
    """ Employé """
    id: int
    name: str
    role: str
    email: str
    manager_id: int | None
    manager_name: str | None
    pays_code: str
    solde_conges_jours: int | None