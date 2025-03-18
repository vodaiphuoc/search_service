import json
import requests
text = "Một con hổ"

_reponse = requests.post(url = "http://127.0.0.1:8080/", 
                         json = json.dumps({'query': text},ensure_ascii= False), 
                         headers= {'Content-Type': 'application/json'}
)

if _reponse.status_code == 200:
    print(_reponse.json()['translated_text'])