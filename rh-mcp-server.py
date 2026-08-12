from mcp.server import MCPServer

# Initialisation du serveur MCP
mcp = MCPServer("ServeurRH")

# Notre "base de données" simulée
EMPLOYEES = {
    "alice": {"role": "Développeuse Backend", "email": "alice@entreprise.com", "manager": "Bob"},
    "bob": {"role": "CTO", "email": "bob@entreprise.com", "manager": "CEO"},
    "charlie": {"role": "Designer", "email": "charlie@entreprise.com", "manager": "Alice"}
}

# Définition de l'outil qui sera exposé à Dust
@mcp.tool()
def get_employee_info(name: str) -> str:
    """Récupère les informations RH d'un employé via son prénom."""
    name_lower = name.lower()
    if name_lower in EMPLOYEES:
        emp = EMPLOYEES[name_lower]
        return f"Nom: {name}, Rôle: {emp['role']}, Email: {emp['email']}, Manager: {emp['manager']}"
    return f"Employé '{name}' introuvable dans la base de données."

if __name__ == "__main__":
    # Lancement du serveur avec le protocole SSE (Server-Sent Events)
    mcp.run(transport="sse", host="0.0.0.0", port=8000)