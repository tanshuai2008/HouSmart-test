import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import datetime

# Mocking st.secrets simply to check if the file is loaded by Streamlit when running pages
# Actually, for a standalone script, we can't use st.secrets unless we use 'streamlit run' or load toml manually.
# But 'streamlit run' is hard to capture output from.
# I will interpret the TOML file manually or just rely on the user running this with 'streamlit run'.
# Better: I will create a script that reads .streamlit/secrets.toml if it exists.

import toml
import os

def test_connection():
    try:
        if os.path.exists(".streamlit/secrets.toml"):
            secrets = toml.load(".streamlit/secrets.toml")
        else:
            print("ERROR: .streamlit/secrets.toml not found.")
            return

        if "gcp_service_account" not in secrets:
            print("ERROR: [gcp_service_account] section missing in secrets.")
            return

        print("Secrets loaded. Attempting connection...")
        
        scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        # Convert TOML dict to standard dict if needed, typically it's fine.
        creds_dict = secrets["gcp_service_account"]
        
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        
        print("Auth successful. Accessing Sheet...")
        sheet_name = secrets.get("GSHEET_NAME", "HouSmart_Logs")
        try:
            sheet = client.open(sheet_name).sheet1
            print(f"SUCCESS: Connected to sheet '{sheet_name}'.")
            
            # Try appending a test row
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            sheet.append_row([timestamp, "debug_test@example.com", "Test Connection"])
            print("SUCCESS: Appended test row.")
            
        except gspread.exceptions.SpreadsheetNotFound:
            print(f"ERROR: Spreadsheet '{sheet_name}' not found. Please create it or check the name.")
        except Exception as e:
             print(f"ERROR opening/writing to sheet: {e}")
            
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")

if __name__ == "__main__":
    test_connection()
