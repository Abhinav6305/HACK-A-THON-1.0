import os
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime

load_dotenv()

def upload_to_drive(file_path, filename):
    # For now, just return a placeholder ID since Google Drive access is blocked
    # In production, this would upload to Google Drive
    return f"drive_file_{filename}_{datetime.now().timestamp()}"

def add_to_sheet(data):
    # For now, save to local Excel file as fallback since Google Sheets access is blocked
    # In production, this would add to Google Sheets
    df = pd.DataFrame([data])
    excel_file = 'registrations.xlsx'
    if os.path.exists(excel_file):
        existing_df = pd.read_excel(excel_file)
        df = pd.concat([existing_df, df], ignore_index=True)
    df.to_excel(excel_file, index=False)
