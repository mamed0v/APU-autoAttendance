import requests
import os
import json
import sys
import time
import argparse
import logging
from dotenv import load_dotenv

load_dotenv()

LOGIN = os.getenv("APU_LOGIN")

SESSION_FILE = "session.json"
CAS_BASE_URL = "https://cas.apiit.edu.my/cas"

API_ATTENDIX_SERVICE_URL = "https://api.apiit.edu.my/attendix"
GRAPHQL_URL = "https://attendix.apu.edu.my/graphql"
API_KEY = "da2-u4ksf3gspnhyjcokxzugo3mqr4"


def get_st(session, tgt, service_url):
    """Gets a Service Ticket (ST) for the specified service."""
    logging.info(f"Requesting ST for service: {service_url}...")
    url = f"{CAS_BASE_URL}/v1/tickets/{tgt}"
    params = {'service': service_url}
    headers = {
        'Content-type': 'application/x-www-form-urlencoded',
        'Origin': 'https://apspace.apu.edu.my',
        'Referer': 'https://apspace.apu.edu.my/',
        'Content-Length': '0',
    }

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

def submit_attendance_otp(session, st, otp):
    """Submits the attendance OTP to the GraphQL endpoint."""
    logging.info(f"Submitting OTP '{otp}'...")
    headers = {
        'accept': 'application/json, text/plain, */*',
        'content-type': 'application/json',
        'origin': 'https://apspace.apu.edu.my',
        'referer': 'https://apspace.apu.edu.my/',
        'ticket': st,
        'x-api-key': API_KEY,
        'x-amz-user-agent': 'aws-amplify/2.0.7',
    }

    query = """
    mutation updateAttendance($otp: String!) {
      updateAttendance(otp: $otp) {
        id
        attendance
        classcode
        date
        startTime
        endTime
        classType
        __typename
      }
    }
    """
    
    payload = {
        "operationName": "updateAttendance",
        "variables": {"otp": otp},
        "query": query
    }

    try:
        response = session.post(GRAPHQL_URL, headers=headers, json=payload)
        response.raise_for_status()
        response_data = response.json()

        if "errors" in response_data and response_data["errors"]:
            error_message = response_data["errors"][0].get("message", "Unknown error")
            logging.error(f"Submission failed. Server response: {error_message}")
            logging.debug(f"Full error response: {response_data}")
        elif "data" in response_data and response_data["data"].get("updateAttendance"):
            class_info = response_data["data"]["updateAttendance"]
            logging.info("\n" + "✅" * 20)
            logging.info("Attendance submitted successfully!")
            logging.info(f"  Class: {class_info.get('classcode')}")
            logging.info(f"  Time: {class_info.get('startTime')} - {class_info.get('endTime')}")
            logging.info(f"  Date: {class_info.get('date')}")
            logging.info("✅" * 20 + "\n")
        else:
            logging.warning("Submission status unknown. Full response:")
            logging.warning(response_data)

    except requests.exceptions.RequestException as e:
        logging.error(f"Error submitting attendance: {e}")
        logging.debug(f"Response body: {e.response.text}")
    except json.JSONDecodeError:
        logging.error("Error decoding JSON response from the submission API.")
        logging.debug(f"Response body: {response.text}")


def main():
    """Main function to submit attendance."""
    parser = argparse.ArgumentParser(description="Submit APU attendance OTP.")
    parser.add_argument("otp", nargs='?', default=None, help="The attendance OTP code. If not provided, it will be asked for interactively.")
    parser.add_argument(
        "-d", "--debug",
        action="store_true",
        help="Enable debug logging for detailed output."
    )
    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S')

    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    script_start_time = time.time()

    if not os.path.exists(SESSION_FILE):
        logging.error(f"Session file '{SESSION_FILE}' not found.")
        logging.error("Please run 'view_attendance.py' first to log in and create a session.")
        sys.exit(1)

    otp = args.otp
    if not otp:
        try:
            otp = input("Enter the attendance OTP code: ").strip()
        except KeyboardInterrupt:
            print("\nOperation cancelled by user.")
            sys.exit(0)

    if not otp or not otp.isdigit() or len(otp) < 3:
        logging.error("Invalid OTP format. Please enter a valid code.")
        sys.exit(1)

    session = requests.Session()
    tgt = None

    logging.info("Loading session from file...")
    try:
        with open(SESSION_FILE, 'r') as f:
            saved_session = json.load(f)
            session.cookies.update(saved_session.get("cookies"))
            tgt = saved_session.get("tgt")
        if not tgt:
            raise ValueError("TGT not found in session file.")
    except (IOError, json.JSONDecodeError, ValueError) as e:
        logging.error(f"Failed to load session: {e}")
        logging.error("Please run 'view_attendance.py' again to refresh your session.")
        sys.exit(1)

    step_time = time.time()
    st_for_attendix = get_st(session, tgt, API_ATTENDIX_SERVICE_URL)
    logging.debug(f"ST fetch took {time.time() - step_time:.2f}s")
    
    if st_for_attendix:
        step_time = time.time()
        submit_attendance_otp(session, st_for_attendix, otp)
        logging.debug(f"OTP submission took {time.time() - step_time:.2f}s")

    logging.info(f"Total execution time: {time.time() - script_start_time:.2f}s")


if __name__ == "__main__":
    main() 