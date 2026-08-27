from clients.database import DatabaseManager
import sqlite3
from models.employee import Employee






class EmployeeRepository:
    """ Repository en charge des employés. """



    """ Queries SQL pour appeler la BDD """
    _SELECT_EMPLOYEE_BASE = """
           SELECT e.id, e.name, e.role, e.email, e.manager_id,
                  e.pays_code, e.solde_conges_jours,
                  m.name AS manager_name
           FROM employees e
           LEFT JOIN employees m ON e.manager_id = m.id
       """

    FIND_BY_NAME = _SELECT_EMPLOYEE_BASE + " WHERE LOWER(e.name) = ?"

    FIND_BY_ID = _SELECT_EMPLOYEE_BASE + " WHERE e.id = ?"

    FIND_DIRECT_REPORTS = "SELECT id, name, role, email, manager_id, pays_code, solde_conges_jours FROM employees WHERE manager_id = ?"



    def __init__(self):
        """ Constructeur """
        self.databaseManager = DatabaseManager()



    def ensure_database_exists(self) -> None:
        """ Vérifie que la base de données sous-jacente existe. """
        self.databaseManager.ensure_database_exists()



    def find_by_name(self, name: str) -> Employee | None:
        """ Récupération d'un employé en BDD via son nom. """
        conn = self.databaseManager.get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                self.FIND_BY_NAME,
                (name.strip().lower(),),
            )
            row = cur.fetchone()
            return self._to_employee(row) if row else None
        finally:
            conn.close()



    def find_direct_reports(self, manager_id: int) -> list[Employee]:
        """ Récupère les informations des employés en BDD via l'Id de son manager. """
        conn = self.databaseManager.get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                self.FIND_DIRECT_REPORTS,
                (manager_id,),
            )
            return [self._to_employee(r) for r in cur.fetchall()]
        finally:
            conn.close()



    def find_by_id(self, id: int) -> Employee | None:
        """ Récupération d'un employé en BDD via son id. """
        conn = self.databaseManager.get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                self.FIND_BY_ID,
                (id,),
            )
            row = cur.fetchone()
            return self._to_employee(row) if row else None
        finally:
            conn.close()



    @staticmethod
    def _to_employee(row: sqlite3.Row) -> Employee:
        """ Renvoi les informations des employés dans un objet employé. """
        return Employee(
            id=row["id"], name=row["name"], role=row["role"], email=row["email"],
            manager_id=row["manager_id"],
            manager_name=row["manager_name"] if "manager_name" in row.keys() else None,
            pays_code=row["pays_code"], solde_conges_jours=row["solde_conges_jours"],
        )


