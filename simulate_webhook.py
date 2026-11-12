import httpx
import json

# Le payload exact que Meta enverrait si quelqu'un vous envoyait un message
payload = {
    "object": "whatsapp_business_account",
    "entry": [{
        "id": "123456789",
        "changes": [{
            "value": {
                "messaging_product": "whatsapp",
                "metadata": {
                    "display_phone_number": "22990000000",
                    "phone_number_id": "123456"
                },
                "contacts": [{
                    "profile": {"name": "Test User"},
                    "wa_id": "22990000000"
                }],
                "messages": [{
                    "from": "22990000000",
                    "id": "wamid.test",
                    "timestamp": "1670000000",
                    "text": {
                        # On envoie une phrase qui devrait matcher avec nos 500 données fictives
                        "body": "ALERTE : attaque à Abidjan, ne sortez pas" 
                    },
                    "type": "text"
                }]
            },
            "field": "messages"
        }]
    }]
}

# On envoie la requête à notre serveur local
url = "http://localhost:8000/api/webhook"
headers = {"Content-Type": "application/json"}

try:
    response = httpx.post(url, json=payload)
    print(f"Statut HTTP : {response.status_code}")
    print(f"Réponse du serveur : {response.json()}")
except Exception as e:
    print(f"Erreur : {e}")