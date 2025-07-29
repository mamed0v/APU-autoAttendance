import requests
import os
import json
import re
import sys
import time
import argparse
import logging
from collections import defaultdict
from dotenv import load_dotenv

# ANSI escape codes for colors
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    ENDC = '\033[0m'

# Load environment variables from .env file
load_dotenv()

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
    logging.info("Step 1: Getting TGT...")
    url = f"{CAS_BASE_URL}/v1/tickets"
    data = {'username': LOGIN, 'password': PASSWORD}
    try:
        response = session.post(url, headers=get_headers(), data=data)
        response.raise_for_status()
        tgt = response.text
        if not tgt.startswith("TGT-"):
            raise ValueError(f"Failed to get TGT. Server response: {tgt}")
        logging.info(f"TGT obtained: {tgt[:15]}...")
        return tgt
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            logging.error("Invalid credentials (login or password).")
        else:
            logging.error(f"Error getting TGT: {e.response.status_code}")
            logging.debug(f"Response body: {e.response.text}")
        return None
    except Exception as e:
        logging.error(f"An error occurred while getting TGT: {e}")
        return None

def get_st(session, tgt, service_url):
    """Step 2: Get a Service Ticket (ST) for the specified service."""
    logging.info(f"Step 2: Getting ST for service {service_url}...")
    url = f"{CAS_BASE_URL}/v1/tickets/{tgt}"
    params = {'service': service_url}
    
    headers = get_headers()
    headers['Content-Length'] = '0'

    try:
        response = session.post(url, headers=headers, params=params)
        response.raise_for_status()
        st = response.text
        logging.info(f"ST obtained: {st[:15]}...")
        return st
    except requests.exceptions.RequestException as e:
        logging.error(f"Error getting ST: {e}")
        logging.debug(f"Response body: {e.response.text}")
        return None

def get_attendance(session, st):
    """Fetches the attendance data."""
    logging.info("Step 3: Fetching attendance data...")
    intake_code = "UCFF2411CT"
    url = f"https://api.apiit.edu.my/student/attendance?intake={intake_code}&ticket={st}"
    
    headers = get_headers()
    headers.pop('Content-type', None)

    try:
        response = session.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching attendance data: {e}")
        logging.debug(f"Response body: {e.response.text}")
        return None
    except json.JSONDecodeError:
        logging.error("Error decoding JSON response from the attendance API.")
        logging.debug(f"Response body: {response.text}")
        return None

def format_and_print_attendance(attendance_data):
    """Formats and prints the attendance data in a clean, colorful table."""
    if not attendance_data:
        logging.warning("No attendance data to display.")
        return

    # Use a list to build the report string
    report_lines = []
    
    report_lines.append(f"{Colors.BOLD}{'='*70}{Colors.ENDC}")
    report_lines.append(f"{Colors.BOLD}{'ATTENDANCE REPORT'.center(70)}{Colors.ENDC}")
    report_lines.append(f"{Colors.BOLD}{'='*70}{Colors.ENDC}")

    by_semester = defaultdict(list)
    for subject in attendance_data:
        by_semester[subject['SEMESTER']].append(subject)

    for semester in sorted(by_semester.keys(), reverse=True):
        report_lines.append(f"\n{Colors.BLUE}{Colors.BOLD}--- SEMESTER {semester} ---{Colors.ENDC}")
        subjects = by_semester[semester]
        
        # Find the maximum length of subject names for alignment
        try:
            max_len = max(len(s['MODULE_ATTENDANCE']) for s in subjects)
        except ValueError:
            max_len = 0 # Handle case where a semester might have no subjects

        for subject in subjects:
            name = subject['MODULE_ATTENDANCE']
            percentage = subject['PERCENTAGE']
            total = subject['TOTAL_CLASSES']
            absent = subject['TOTAL_ABSENT']
            
            if percentage >= 80:
                color = Colors.GREEN
            elif percentage >= 70:
                color = Colors.YELLOW
            else:
                color = Colors.RED
            
            # Left-align the subject name, right-align the percentage for a clean look
            padded_name = name.ljust(max_len)
            
            report_lines.append(
                f"  {padded_name}  |  {color}{Colors.BOLD}{percentage:>3}%{Colors.ENDC}  |  "
                f"Classes: {total:<2}, Absences: {absent:<2}"
            )

    report_lines.append(f"\n{Colors.BOLD}{'='*70}{Colors.ENDC}")
    
    # Print the entire report at once to the console, without logging prefixes
    print("\n" + "\n".join(report_lines) + "\n")


def main():
    """Main function to log in and fetch data."""
    parser = argparse.ArgumentParser(description="Fetch and display APU attendance.")
    parser.add_argument(
        "-d", "--debug",
        action="store_true",
        help="Enable debug logging for detailed output."
    )
    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S')
    
    # Suppress verbose logging from libraries
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    script_start_time = time.time()

    if not LOGIN or not LOGIN.strip() or not PASSWORD or not PASSWORD.strip():
        logging.error("APU_LOGIN and APU_PASSWORD environment variables are not set or are empty.")
        logging.error("Please create a '.env' file with your credentials or export them.")
        sys.exit(1)

    session = requests.Session()
    tgt = None
    st_for_attendance = None 

    if os.path.exists(SESSION_FILE):
        logging.info("Session file found. Attempting to restore...")
        try:
            with open(SESSION_FILE, 'r') as f:
                saved_session = json.load(f)
                session.cookies.update(saved_session.get("cookies"))
                tgt = saved_session.get("tgt")

            if not tgt:
                raise ValueError("TGT not found in session file.")

            step_time = time.time()
            st_for_attendance = get_st(session, tgt, API_ATTENDANCE_SERVICE_URL)
            logging.debug(f"ST fetch took {time.time() - step_time:.2f}s")
            if not st_for_attendance:
                 raise ValueError("Failed to get ST for attendance API. TGT might be expired.")
            
            logging.info("Session is valid, proceeding to fetch data.")

        except (IOError, json.JSONDecodeError, ValueError) as e:
            logging.warning(f"Session restore failed: {e}. Performing a new login.")
            session = requests.Session()
            tgt = None
            st_for_attendance = None

    if not tgt:
        step_time = time.time()
        tgt = get_tgt(session)
        logging.debug(f"TGT fetch took {time.time() - step_time:.2f}s")
        if not tgt:
            sys.exit(1)

    if not st_for_attendance:
        step_time = time.time()
        st_for_attendance = get_st(session, tgt, API_ATTENDANCE_SERVICE_URL)
        logging.debug(f"ST fetch took {time.time() - step_time:.2f}s")
    
    if st_for_attendance:
        step_time = time.time()
        attendance_data = get_attendance(session, st_for_attendance)
        logging.debug(f"Attendance data fetch took {time.time() - step_time:.2f}s")
        if attendance_data:
            format_and_print_attendance(attendance_data)
            with open(SESSION_FILE, 'w') as f:
                saved_data = {"cookies": session.cookies.get_dict(), "tgt": tgt}
                json.dump(saved_data, f)
            logging.info(f"Session successfully updated and saved to {SESSION_FILE}")

    logging.info(f"Total execution time: {time.time() - script_start_time:.2f}s")

if __name__ == "__main__":
    main()
