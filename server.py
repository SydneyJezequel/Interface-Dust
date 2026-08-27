from mcp.server import MCPServer
from datetime import datetime
from repositories.employee_repository import EmployeeRepository
from services.employee_service import EmployeeService
from services.leave_service import LeaveService
from clients.nager_client import NagerHolidayClient
from exceptions import EmployeeNotFoundError, DatabaseError
import os
from dotenv import load_dotenv



""" Initialisation du serveur MCP """
mcp = MCPServer("ServeurRH")



""" Initialisation de l'API des jours fériés (Nager.Date) """
load_dotenv()
NAGER_BASE_URL = os.environ["NAGER_BASE_URL"]



""" Initialisation des services """
employee_repo = EmployeeRepository()
holiday_client = NagerHolidayClient(NAGER_BASE_URL)
employee_service = EmployeeService(employee_repo)
leave_service = LeaveService(employee_repo, holiday_client)



@mcp.tool()
def get_employee_info(name: str) -> str:
    """ Récupère les informations RH d'un employé via son prénom. """

    try:
        emp = employee_service.get_employee(name)
    except EmployeeNotFoundError as e:
        return f"Employé '{e.name}' introuvable dans la base de données."
    except DatabaseError as e:
        return f"Erreur d'accès à la base RH : {e}"

    manager = emp.manager_name.capitalize() if emp.manager_name else "Aucun (sommet de la hiérarchie)"
    return (
        f"Nom: {emp.name.capitalize()}, Rôle: {emp.role}, Email: {emp.email}, "
        f"Manager: {manager}, Pays: {emp.pays_code}, Solde congés: {emp.solde_conges_jours} jour(s)"
    )



@mcp.tool()
async def calculer_jours_ouvres_conges(nom: str, date_debut: str, date_fin: str) -> str:
    """ Calcule le nombre réel de jours ouvrés consommés par une demande de congés. """

    # Contrôle des dates de début et fin :
    try:
        debut = datetime.strptime(date_debut, "%Y-%m-%d").date()
        fin = datetime.strptime(date_fin, "%Y-%m-%d").date()
    except ValueError:
        return "Format de date invalide. Utilise le format AAAA-MM-JJ (ex: 2026-12-20)."
    if fin < debut:
        return "La date de fin ne peut pas être antérieure à la date de début."

    # Calcul des jours ouvrés entre les dates de début et fin :
    try:
        resultat = await leave_service.calculer_jours_ouvres(nom, debut, fin)
    except EmployeeNotFoundError as e:
        return f"Employé '{e.name}' introuvable dans la base de données."

    # Formatage :
    lignes = [
        f"Employé : {resultat.employee_name.capitalize()} (pays : {resultat.pays_code})",
        f"Période demandée : du {debut.isoformat()} au {fin.isoformat()} ({(fin - debut).days + 1} jour(s) calendaires)",
        f"Jours ouvrés réellement consommés : {resultat.jours_ouvres}",
    ]
    if resultat.jours_feries:
        lignes.append("Jour(s) férié(s) dans la période : " + ", ".join(j.isoformat() for j in resultat.jours_feries))
    else:
        lignes.append("Aucun jour férié dans la période.")
    if resultat.solde_avant is not None:
        lignes.append(f"Solde de congés avant demande : {resultat.solde_avant} jour(s)")
        lignes.append(f"Solde restant estimé après validation : {resultat.solde_apres} jour(s)")
    if resultat.avertissement:
        lignes.append(f"⚠️ Attention : {resultat.avertissement} — calcul potentiellement incomplet.")

    return "\n".join(lignes)




@mcp.tool()
def get_team_members(manager_name: str) -> str:
    """ Récupère la liste des employés qui rapportent directement à un manager donné. """

    manager_name_lower = manager_name.strip().lower()

    try:
        team = employee_service.get_team(manager_name_lower)
    except EmployeeNotFoundError as e:
        return f"Employé '{e.name}' introuvable dans la base de données."

    if not team.reports:
        return f"{team.manager.name.capitalize()} n'a aucun employé sous sa responsabilité."

    lignes = [
        f"- {r.name.capitalize()} ({r.role}, {r.email})"
        for r in team.reports
    ]
    return (
        f"Équipe de {team.manager.name.capitalize()} "
        f"({len(team.reports)} personne(s)) :\n" + "\n".join(lignes)
    )




if __name__ == "__main__":
    employee_repo.ensure_database_exists()
    # Lancement du serveur :
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)