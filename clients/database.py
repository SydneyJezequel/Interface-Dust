import sqlite3
from pathlib import Path






class DatabaseManager:
    """ Gère les connexions à la BDD SQLite. """


    # Chemin par défaut de la BDD (constante de classe)
    DEFAULT_DB_PATH = Path(__file__).parent / "rh_database.db"



    def __init__(self):
        """ Constructeur """
        self.DB_PATH = self.DEFAULT_DB_PATH


    def ensure_database_exists(self) -> None:
        """ Vérifie que le fichier de base de données existe. """
        if not self.DB_PATH.exists():
            raise FileNotFoundError(
                f"Base introuvable : {self.DB_PATH}. "
                "Lance d'abord 'python init_db.py' pour la créer et la peupler."
            )


    def get_connection(self) -> sqlite3.Connection:
        """ Ouvre une connexion à la BDD et configure le retour des lignes. """
        conn = sqlite3.connect(self.DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn


