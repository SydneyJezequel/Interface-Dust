from dataclasses import dataclass
from models.employee import Employee





@dataclass
class TeamInfo:
    """ Détail des membres de l'équipe (manager + surbordonnées) """
    manager: Employee
    reports: list[Employee]