import os
import requests
from dotenv import load_dotenv
import time



""" Chargement des clés d'API. """
load_dotenv()
DUST_API_KEY = os.environ["DUST_API_KEY"]
DUST_WORKSPACE_ID = os.environ["DUST_WORKSPACE_ID"]
DUST_AGENT_SID = os.environ["DUST_AGENT_SID"]



""" Chargement de l'URL de base. """
BASE_URL = f"https://eu.dust.tt/api/v1/w/{DUST_WORKSPACE_ID}/assistant/conversations"

HEADERS = {
    "Authorization": f"Bearer {DUST_API_KEY}",
    "Content-Type": "application/json",
}



def send_message(question: str, conversation_id: str = None) -> dict:
    """Envoie un message (nouvelle conv ou existante) et attend la réponse."""

    # Payload pour le message
    message_payload = {
        "content": question,
        "mentions": [{"configurationId": f"{DUST_AGENT_SID}"}],
        "context": {
            "timezone": "Europe/Paris",
            "username": "User"
        }
    }

    # Si on a déjà une conversation, on poste un nouveau message dedans :
    if conversation_id:
        url = f"{BASE_URL}/{conversation_id}/messages"
        payload = message_payload
    # Sinon, on crée une nouvelle conversation :
    else:
        url = BASE_URL
        payload = {
            "message": message_payload,
            "blocking": True
        }

    # 1. Envoi du message
    response = requests.post(url, headers=HEADERS, json=payload, timeout=30)
    response.raise_for_status()
    data = response.json()

    # On récupère le sId de la conversation (soit depuis la création, soit on le connaissait déjà)
    current_conv_id = data.get("conversation", {}).get("sId") or data.get("message", {}).get("sId")
    if not current_conv_id:
        current_conv_id = conversation_id

    status_url = f"{BASE_URL}/{current_conv_id}"

    # 2. Boucle d'attente de la réponse
    for _ in range(40):
        time.sleep(1.5)
        status_res = requests.get(status_url, headers=HEADERS, timeout=10)
        status_res.raise_for_status()
        status_data = status_res.json()

        content = status_data["conversation"]["content"]

        # On cherche le dernier message de l'assistant :
        for message_info in reversed(content):
            if message_info.get("role") == "assistant":
                if message_info.get("status") == "succeeded":
                    return {
                        "answer": message_info.get("content"),
                        "conversation_id": current_conv_id
                    }
                elif message_info.get("status") == "errored":
                    raise Exception("L'agent a rencontré une erreur lors de la génération.")
                break

    raise TimeoutError("L'agent Dust a mis trop de temps à répondre.")


def main() -> None:
    """ Interface """
    print("Dust API Console")
    print("Tape 'exit' pour quitter.\n")

    # Stockage de l'ID pour garder l'historique :
    current_conversation_id = None

    while True:
        question = input("Vous : ").strip()

        if question.lower() == "exit":
            break
        if not question:
            continue

        try:
            # On passe l'ID de conversation actuel. Si = None, on en crée un :
            result = send_message(question, current_conversation_id)
            current_conversation_id = result["conversation_id"]

            print(f"\nDust : {result['answer']}\n")

        except requests.HTTPError as error:
            print(f"\nErreur HTTP Dust : {error}")
            if error.response is not None:
                print(f"Détails de l'erreur : {error.response.text}\n")
        except Exception as error:
            print(f"\nErreur : {error}\n")


if __name__ == "__main__":
    main()