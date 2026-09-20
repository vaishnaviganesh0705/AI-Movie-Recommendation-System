import requests
import json

def run_test():
    url = "http://127.0.0.1:8000"
    print("Testing user's live server at", url)
    
    # 1. Register/Login to get Token
    req = requests.post(f"{url}/users/register", json={"email": "ping@ex.com", "password": "pass", "name": "ping"})
    login_res = requests.post(f"{url}/users/login", data={"username": "ping@ex.com", "password": "pass"})
    
    if login_res.status_code != 200:
        print("COULD NOT LOGIN:", login_res.text)
        return
        
    token = login_res.json().get("access_token")
    
    # 2. Ping Chat Endpoint Exactly Like Axios
    print("Sending 'hi' to /chat")
    res = requests.post(f"{url}/chat", json={"prompt": "hi"}, headers={"Authorization": f"Bearer {token}"})
    print("STATUS:", res.status_code)
    print("PAYLOAD:", res.text)
    
run_test()
