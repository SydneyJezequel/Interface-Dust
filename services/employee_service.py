from repositories.employee_repository import Employee, EmployeeRepository
from exceptions import EmployeeNotFoundError
from models.team_info import TeamInfo






class EmployeeService:
    """ Service en charge des employés. Retourne des objets Employee / TeamInfo. """



    def __init__(self, employee_repo: EmployeeRepository):
        """ Constructeur """
        self._employee_repo = employee_repo



    def get_employee(self, name: str) -> Employee:
        """ Récupère un employé par son nom. """

        if not name or not name.strip():
            raise EmployeeNotFoundError(name)

        employe = self._employee_repo.find_by_name(name)
        if employe is None:
            raise EmployeeNotFoundError(name)
        return employe



    def get_team(self, manager_name: str) -> TeamInfo:
        """ Récupère un manager et la liste de ses employés. """
        manager = self.get_employee(manager_name)
        reports = self._employee_repo.find_direct_reports(manager.id)
        return TeamInfo(manager=manager, reports=reports)



    def get_manager_chain(self, name: str, max_depth: int = 10) -> list[Employee]:
        """ Retourne la liste des managers d'un employé, du plus proche au plus haut placé. """

        chain: list[Employee] = []
        current = self.get_employee(name)
        for _ in range(max_depth):
            if current.manager_id is None:
                break
            manager = self._employee_repo.find_by_id(current.manager_id)
            if manager is None:
                break
            chain.append(manager)
            current = manager
        return chain

