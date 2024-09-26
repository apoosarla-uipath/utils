import requests
import os

# Replace 'YOUR_ACCESS_TOKEN' with your actual GitHub Personal Access Token
access_token = os.environ.get('GITHUB_TOKEN')

# Set up the headers with the access token
headers = {
    'Authorization': f'token {access_token}',
    'Accept': 'application/vnd.github.v3+json'
}

# Example API call: Get the authenticated user
response = requests.get('https://api.github.com/user', headers=headers)

if response.status_code == 200:
    user_data = response.json()
    print("Authenticated as:", user_data['login'])
else:
    print("Failed to authenticate:", response.status_code, response.text)
