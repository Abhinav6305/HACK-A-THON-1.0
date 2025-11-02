import requests
import os
from werkzeug.utils import secure_filename

# Microsoft Azure app credentials (set these as environment variables)
CLIENT_ID = os.getenv('ONEDRIVE_CLIENT_ID', 'your_client_id_here')
CLIENT_SECRET = os.getenv('ONEDRIVE_CLIENT_SECRET', 'your_client_secret_here')
TENANT_ID = os.getenv('ONEDRIVE_TENANT_ID', 'your_tenant_id_here')

def get_access_token():
    url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    data = {
        'grant_type': 'client_credentials',
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'scope': 'https://graph.microsoft.com/.default'
    }
    response = requests.post(url, data=data)
    if response.status_code == 200:
        return response.json()['access_token']
    else:
        raise Exception("Failed to get access token")

def upload_to_onedrive(file):
    try:
        access_token = get_access_token()
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/octet-stream'
        }
        json_headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

        filename = secure_filename(file.filename)

        # Get drive ID for the root site (for OneDrive for Business)
        drive_url = "https://graph.microsoft.com/v1.0/sites/root/drive"
        drive_response = requests.get(drive_url, headers=json_headers)
        if drive_response.status_code != 200:
            raise Exception("Failed to get drive ID")
        drive_id = drive_response.json()['id']

        # Create folder if not exists
        folder_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root/children"
        folder_data = {
            "name": "Hackathon_Payments",
            "folder": {},
            "@microsoft.graph.conflictBehavior": "rename"
        }
        requests.post(folder_url, headers=json_headers, json=folder_data)

        # Upload the file
        upload_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/Hackathon_Payments/{filename}:/content"
        response = requests.put(upload_url, headers=headers, data=file.read())
        if response.status_code == 201:
            item_id = response.json()['id']
            # Get shareable link
            link_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{item_id}/createLink"
            link_data = {
                "type": "view",
                "scope": "anonymous"
            }
            link_response = requests.post(link_url, headers=json_headers, json=link_data)
            if link_response.status_code == 201:
                return link_response.json()['link']['webUrl']
            else:
                raise Exception("Failed to create shareable link")
        else:
            raise Exception("Failed to upload file")
    except Exception as e:
        print(f"OneDrive upload error: {e}")
        return None
