from dataclasses import dataclass
from datetime import date





@dataclass
class LeaveCalculation:
    """  """
    employee_name: str
    pays_code: str
    debut: date
    fin: date
    jours_ouvres: int
    jours_feries: list[date]
    solde_avant: int | None
    solde_apres: int | None
    avertissement: str | None = None