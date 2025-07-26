import requests
import os
import json
import re
import sys
from collections import defaultdict

# Load credentials from environment variables
LOGIN = os.getenv("APU_LOGIN")
PASSWORD = os.getenv("APU_PASSWORD")

SESSION_FILE = "session.json"
CAS_BASE_URL = "https://cas.apiit.edu.my/cas"
# The main service the user logs into
MAIN_SERVICE_URL = "https://apspace.apu.edu.my/"
# The attendance API service, which requires a specific and exact ticket
API_ATTENDANCE_SERVICE_URL = "https://api.apiit.edu.my/student/attendance"


def get_headers():
    """Returns the base headers for HTTP requests."""
    return {
        'Accept': 'application/json, text/plain, */*',
        'Content-type': 'application/x-www-form-urlencoded',
        'Origin': 'https://apspace.apu.edu.my',
        'Referer': 'https://apspace.apu.edu.my/',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 YaBrowser/25.4.0.0 Safari/537.36',
    }

def get_tgt(session):
    """Step 1: Get a Ticket-Granting Ticket (TGT)."""
    print("Step 1: Getting TGT...")
    url = f"{CAS_BASE_URL}/v1/tickets"
    data = {'username': LOGIN, 'password': PASSWORD}
    try:
        response = session.post(url, headers=get_headers(), data=data)
        response.raise_for_status()
        tgt = response.text
        if not tgt.startswith("TGT-"):
            raise ValueError(f"Failed to get TGT. Server response: {tgt}")
        print(f"TGT obtained: {tgt[:15]}...")
        return tgt
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            print("Error: Invalid credentials (login or password).")
        else:
            print(f"Error getting TGT: {e.response.status_code} - {e.response.text}")
        return None
    except Exception as e:
        print(f"An error occurred while getting TGT: {e}")
        return None

def get_st(session, tgt, service_url):
    """Step 2: Get a Service Ticket (ST) for the specified service."""
    print(f"Step 2: Getting ST for service {service_url}...")
    url = f"{CAS_BASE_URL}/v1/tickets/{tgt}"
    params = {'service': service_url}
    
    headers = get_headers()
    # This POST request requires an empty body. Set Content-Length: 0.
    headers['Content-Length'] = '0'

    try:
        # Pass the service_url as a request parameter (params), not in the body (data).
        response = session.post(url, headers=headers, params=params)
        response.raise_for_status()
        st = response.text
        print(f"ST obtained: {st[:15]}...")
        return st
    except requests.exceptions.RequestException as e:
        print(f"Error getting ST: {e}")
        return None

def get_attendance(session, st):
    """Fetches the attendance data."""
    print("Fetching attendance data...")
    # The intake code is hardcoded for now, as in the example
    intake_code = "UCFF2411CT"
    url = f"https://api.apiit.edu.my/student/attendance?intake={intake_code}&ticket={st}"
    
    headers = get_headers()
    # A GET request doesn't need Content-Type, so we remove it.
    headers.pop('Content-type', None)

    try:
        response = session.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching attendance data: {e}")
        return None
    except json.JSONDecodeError:
        print("Error decoding JSON response from the attendance API.")
        return None

def format_and_print_attendance(attendance_data):
    """Formats and prints the attendance data."""
    if not attendance_data:
        print("No attendance data to display.")
        return

    # Group subjects by semester
    by_semester = defaultdict(list)
    for subject in attendance_data:
        by_semester[subject['SEMESTER']].append(subject)

    print("\n" + "="*50)
    print("                ATTENDANCE REPORT")
    print("="*50)

    # Sort semesters in reverse order (newest to oldest)
    for semester in sorted(by_semester.keys(), reverse=True):
        print(f"\n--- SEMESTER {semester} ---")
        subjects = by_semester[semester]
        for subject in subjects:
            name = subject['MODULE_ATTENDANCE']
            percentage = subject['PERCENTAGE']
            total = subject['TOTAL_CLASSES']
            absent = subject['TOTAL_ABSENT']
            
            # Determine the color for the percentage
            if percentage >= 80:
                bar = "🟩" * int(percentage / 10)
            elif percentage >= 70:
                bar = "🟨" * int(percentage / 10)
            else:
                bar = "🟥" * int(percentage / 10)

            print(f"\n  {name}")
            print(f"  {bar} {percentage}%")
            print(f"  (Classes: {total}, Absences: {absent})")
    
    print("\n" + "="*50 + "\n")


def main():
    """Main function to log in and fetch data."""
    # Check if environment variables are set
    if not LOGIN or not PASSWORD:
        print("Error: APU_LOGIN and APU_PASSWORD environment variables are not set.")
        print("Please run in your terminal:")
        print("  export APU_LOGIN='your_login'")
        print("  export APU_PASSWORD='your_password'")
        sys.exit(1)

    session = requests.Session()
    tgt = None

    if os.path.exists(SESSION_FILE):
        print("Session file found. Attempting to restore...")
        try:
            with open(SESSION_FILE, 'r') as f:
                saved_session = json.load(f)
                session.cookies.update(saved_session.get("cookies"))
                tgt = saved_session.get("tgt")

            # Check if the session is valid by getting a ticket for the main site
            if not tgt:
                raise ValueError("TGT not found in session file.")

            st_for_check = get_st(session, tgt, MAIN_SERVICE_URL)
            if not st_for_check:
                 raise ValueError("Failed to get ST for session check. TGT might be expired.")
            
            print("Login with saved session was successful.")

        except (IOError, json.JSONDecodeError, ValueError) as e:
            print(f"Session restore failed: {e}. Performing a new login.")
            session = requests.Session() # Reset session
            tgt = None

    if not tgt:
        tgt = get_tgt(session)
        if not tgt:
            return # Exit if we couldn't get a TGT

    # Get an ST specifically for the attendance API
    st_for_attendance = get_st(session, tgt, API_ATTENDANCE_SERVICE_URL)
    if st_for_attendance:
        attendance_data = get_attendance(session, st_for_attendance)
        if attendance_data:
            format_and_print_attendance(attendance_data)
            # Save the successful session (cookies and TGT)
            with open(SESSION_FILE, 'w') as f:
                saved_data = {"cookies": session.cookies.get_dict(), "tgt": tgt}
                json.dump(saved_data, f)
            print(f"Session successfully updated and saved to {SESSION_FILE}")

if __name__ == "__main__":
    main()
