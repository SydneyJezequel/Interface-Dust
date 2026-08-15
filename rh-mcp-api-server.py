import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
import httpx
from mcp.server import MCPServer
from dotenv import load_dotenv
import os






""" Initialisation """

# Initialisation du serveur MCP :
mcp = MCPServer("ServeurRH")

# Initialisation de la BDD SQLite :
DB_PATH = Path(__file__).parent / "rh_database.db"

# Initialisation de l'API des jours fériés (Nager.Date) :
load_dotenv()
NAGER_BASE_URL = os.environ["NAGER_BASE_URL"]




""" A supprimer ???????? """
# Cache mémoire très simple : { (pays_code, annee): [ {..jour ferie..}, ... ] }
# Evite de rappeler l'API à chaque question pour le même pays/année.
# Volontairement en mémoire (pas de TTL) : suffisant pour une session de
# démo/dev. A remplacer par un cache avec expiration si le serveur tourne
# en continu sur plusieurs jours (les jours fériés d'une année ne changent
# de toute façon jamais une fois publiés).
_holidays_cache: dict[tuple[str, int], list[dict]] = {}



def get_connection() -> sqlite3.Connection:
    """ Ouvre une connexion à la BDD et configure le retour des lignes. """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn



def _get_employee_row(name: str) -> sqlite3.Row | None:
    """ Renvoie la ligne brute de l'employé, ou None si introuvable. """
    name_lower = name.strip().lower()
    conn = get_connection()
    try:
        cur = conn.cursor()
        # LEFT JOIN sur la table elle-même pour récupérer le nom du manager
        # (et pas seulement son id). LEFT JOIN plutôt que JOIN classique
        # car le CEO n'a pas de manager (manager_id NULL) : un JOIN
        # simple l'aurait exclu du résultat.
        cur.execute(
            """
            SELECT e.id, e.name, e.role, e.email, e.manager_id,
                   e.pays_code, e.solde_conges_jours,
                   m.name AS manager_name
            FROM employees e
            LEFT JOIN employees m ON e.manager_id = m.id
            WHERE LOWER(e.name) = ?
            """,
            (name_lower,),
        )
        return cur.fetchone()
    finally:
        conn.close()



@mcp.tool()
def get_employee_info(name: str) -> str:
    """ Récupère les informations RH d'un employé via son prénom. """
    try:
        row = _get_employee_row(name)
    except sqlite3.Error as e:
        return f"Erreur d'accès à la base RH : {e}"

    if row is None:
        return f"Employé '{name}' introuvable dans la base de données."

    manager_display = row["manager_name"].capitalize() if row["manager_name"] else "Aucun (sommet de la hiérarchie)"

    return (
        f"Nom: {row['name'].capitalize()}, Rôle: {row['role']}, "
        f"Email: {row['email']}, Manager: {manager_display}, "
        f"Pays: {row['pays_code']}, Solde congés: {row['solde_conges_jours']} jour(s)"
    )



@mcp.tool()
def get_team_members(manager: str) -> str:
    """ Récupère la liste des employés qui rapportent directement à un manager donné. """

    manager_lower = manager.strip().lower()

    try:
        conn = get_connection()
        cur = conn.cursor()

        # Étape 1 : vérifier que le manager existe et récupérer son id :
        cur.execute(
            "SELECT id, name FROM employees WHERE LOWER(name) = ?",
            (manager_lower,),
        )
        manager_row = cur.fetchone()

        if manager_row is None:
            return f"Manager '{manager}' introuvable dans la base de données."

        # Étape 2 : récupérer les employés rattachés à ce manager_id :
        cur.execute(
            "SELECT name, role, email FROM employees WHERE manager_id = ?",
            (manager_row["id"],),
        )
        rows = cur.fetchall()
    except sqlite3.Error as e:
        return f"Erreur d'accès à la base RH : {e}"
    finally:
        conn.close()

    if not rows:
        return f"{manager_row['name'].capitalize()} n'a aucun employé sous sa responsabilité directe."

    lignes = [f"- {r['name'].capitalize()} ({r['role']}, {r['email']})" for r in rows]
    return f"Équipe de {manager_row['name'].capitalize()} ({len(rows)} personne(s)) :\n" + "\n".join(lignes)



@mcp.tool()
async def get_public_holidays(pays_code: str, annee: int) -> list[dict]:
    """ Récupère la liste des jours fériés d'un pays pour une année donnée,
    via l'API publique Nager.Date. Le résultat est mis en cache en mémoire
    par (pays_code, année) pour éviter les appels réseau redondants. """
    pays_code = pays_code.strip().upper()
    cache_key = (pays_code, annee)

    if cache_key in _holidays_cache:
        return _holidays_cache[cache_key]

    url = f"{NAGER_BASE_URL}/{annee}/{pays_code}"
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as e:
            return [{"error": f"Code pays invalide ou API indisponible ({e.response.status_code})"}]
        except httpx.RequestError:
            return [{"error": "Impossible de joindre l'API des jours fériés"}]

    _holidays_cache[cache_key] = data
    return data



@mcp.tool()
async def calculer_jours_ouvres_conges(nom: str, date_debut: str, date_fin: str) -> str:
    """ Croise la bdd RH (employé + pays) avec l'API des jours fériés pour
    calculer le nombre réel de jours ouvrés consommés par une demande de
    congés. """


    # 1. Validation des dates :
    try:
        debut = datetime.strptime(date_debut, "%Y-%m-%d").date()
        fin = datetime.strptime(date_fin, "%Y-%m-%d").date()
    except ValueError:
        return "Format de date invalide. Utilise le format AAAA-MM-JJ (ex: 2026-12-20)."
    if fin < debut:
        return "La date de fin ne peut pas être antérieure à la date de début."


    # 2. Récupération des données de l'employé :
    try:
        employe = _get_employee_row(nom)
    except sqlite3.Error as e:
        return f"Erreur d'accès à la base RH : {e}"
    if employe is None:
        return f"Employé '{nom}' introuvable dans la base de données."
    pays_code = employe["pays_code"] or "FR"


    # 3. Récupération des jours fériés :
    feries_dates: set[date] = set()
    erreur_api = None
    for annee in range(debut.year, fin.year + 1):
        feries = await get_public_holidays(pays_code, annee)
        if feries and isinstance(feries[0], dict) and "error" in feries[0]:
            # On garde une trace de l'erreur mais on continue : mieux vaut
            # un calcul dégradé (sans certains jours fériés) qu'un échec
            # total de l'outil.
            erreur_api = feries[0]["error"]
            continue
        for jour in feries:
            try:
                feries_dates.add(datetime.strptime(jour["date"], "%Y-%m-%d").date())
            except (KeyError, ValueError):
                continue


    # 4. Calcul des jours ouvrés (hors week-ends + jours fériés) :
    jours_ouvres = 0
    feries_dans_periode = []
    jour_courant = debut
    while jour_courant <= fin:
        est_weekend = jour_courant.weekday() >= 5  # 5 = samedi, 6 = dimanche
        est_ferie = jour_courant in feries_dates
        if est_ferie:
            feries_dans_periode.append(jour_courant.isoformat())
        if not est_weekend and not est_ferie:
            jours_ouvres += 1
        jour_courant += timedelta(days=1)


    # 5. Construction de la réponse :
    nom_affiche = employe["name"].capitalize()
    solde = employe["solde_conges_jours"]
    solde_restant = (solde - jours_ouvres) if solde is not None else None

    lignes = [
        f"Employé : {nom_affiche} (pays : {pays_code})",
        f"Période demandée : du {debut.isoformat()} au {fin.isoformat()} "
        f"({(fin - debut).days + 1} jour(s) calendaires)",
        f"Jours ouvrés réellement consommés : {jours_ouvres}",
    ]

    if feries_dans_periode:
        lignes.append(f"Jour(s) férié(s) dans la période : {', '.join(feries_dans_periode)}")
    else:
        lignes.append("Aucun jour férié dans la période.")

    if solde is not None:
        lignes.append(f"Solde de congés avant demande : {solde} jour(s)")
        lignes.append(f"Solde restant estimé après validation : {solde_restant} jour(s)")

    if erreur_api:
        lignes.append(
            f"⚠️ Attention : {erreur_api} — le calcul ci-dessus peut ne pas "
            "exclure tous les jours fériés pour une des années concernées."
        )

    return "\n".join(lignes)






if __name__ == "__main__":
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Base introuvable : {DB_PATH}. "
            "Lance d'abord 'python init_db.py' pour la créer et la peupler."
        )
    # Lancement du serveur avec le protocole SSE (Server-Sent Events)
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)


