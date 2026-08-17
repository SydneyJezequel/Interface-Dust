


class EmployeeNotFoundError(Exception):
    """ Absence d'employé """


    def __init__(self, name: str):
        """ Constructeur """
        self.name = name
        super().__init__(f"Employé '{name}' introuvable")





class DatabaseError(Exception):
    """ Erreur de BDD """
    pass





class HolidayApiError(Exception):
    """ Erreur liée à l'API Nager """
    pass

