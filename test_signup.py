import requests

# URL of the Flask API endpoint
url = 'http://127.0.0.1:5000/signup'

# Headers for the request
headers = {'Content-Type': 'application/json'}

# Data to be sent in the request body
data = {
    "username": "gaurav",
    "password": "chindhe",
    "email": "gaurav21bce@example.com",
}

# Making a POST request to the API endpoint
response = requests.post(url, headers=headers, json=data)

# Printing the response status code and content
print(response.status_code)
print(response.json())
