import requests
count=2

URL = "http://127.0.0.1:3000"
headers = {"X-FYP-MALICIOUS": "1"}
for i in range(count):
    report=requests.get(URL)
    print(f"Response {i+1}: ")