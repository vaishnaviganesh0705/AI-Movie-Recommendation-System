import requests

def run_test():
    url = "http://127.0.0.1:8011"
    print("Sending 'give tamil movies' to /chat")
    res = requests.post(f"{url}/chat", json={"prompt": "give tamil movies"})
    print("STATUS:", res.status_code)
    print("PAYLOAD:", res.text)
    
run_test()
