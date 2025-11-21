"""Add Faithward Advisors to the fund tracker."""

import requests
import json

url = "http://localhost:8000/api/v1/funds/"
data = {
    "cik": "1695078",
    "name": "Faithward Advisors, LLC",
    "category": "general"
}

response = requests.post(url, json=data)
print(json.dumps(response.json(), indent=2))
