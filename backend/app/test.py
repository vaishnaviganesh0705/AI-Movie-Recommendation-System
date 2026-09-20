import requests

try:
    r = requests.get("https://api.themoviedb.org/3", timeout=10)
    print(r.status_code)
except Exception as e:
    print(e)