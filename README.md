# 🚀 APU Auto Attendance Tools 🚀

A collection of command-line tools to supercharge your APU student portal experience for viewing and submitting attendance.

---

## 🛑 IMPORTANT: Academic Integrity & Risks

**This project is for educational and experimental purposes ONLY.**

Think of it as a fun way to learn about APIs, web requests, and scripting. But remember, with great power comes great responsibility!

Using these tools, especially `find_attendance_code.py`, might be a **direct violation** of APU's academic integrity policies. Automating this stuff can be detected by the university's IT department and might lead to serious consequences:

-   **Suspension of your student account** 😱
-   **An IP address ban** from university services 🚫
-   **Disciplinary action** from the university 📄

The author is not responsible for how you use these tools. **USE AT YOUR OWN RISK.** Be smart, be honest.

---

## ✨ Features

This project packs three main scripts:

1.  **`view_attendance.py` 📊**: Securely logs in, caches your session, and displays a slick, formatted attendance report grouped by semester.
2.  **`submit_attendance.py` ✅**: Lets you manually submit a 3-digit attendance OTP code right from your terminal. No more frantic clicking!
3.  **`find_attendance_code.py` 🤖**: The experimental script that attempts to find the correct 3-digit attendance code by brute-forcing all 1000 possibilities. (Seriously, read the warning above before touching this).

## 📋 Prerequisites

-   Python 3.8+
-   `pip` and `venv` (usually come with Python)

## 🛠️ Installation

1.  **Clone the repo 🤘**
    ```bash
    git clone https://github.com/mamed0v/APU-autoAttendance.git
    cd APU-autoAttendance
    ```

2.  **Set up your virtual environment 🌿**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```
    *(On Windows, the command depends on your shell):*
    **Command Prompt:**
    ```cmd
    .venv\Scripts\activate.bat
    ```
    **PowerShell:**
    ```powershell
    .venv\Scripts\Activate.ps1
    ```

3.  **Install the dependencies 📦**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Create your `.env` file 🔑**
    This is where you'll store your secrets. Create a file named `.env` and add your credentials. Don't worry, it's in `.gitignore`, so it will never be uploaded.
    ```env
    APU_LOGIN="YOUR_TP_NUMBER"
    APU_PASSWORD="YOUR_PORTAL_PASSWORD"
    ```

---

## 🎮 How to Use

### 1. View Your Attendance Report 📜

This is your starting point. Run this first to log in and create the `session.json` file needed by the other scripts.

```bash
python3 view_attendance.py
```

Want to see all the nitty-gritty details? Use the `--debug` flag:
```bash
python3 view_attendance.py --debug
```

### 2. Submit Attendance Manually ✍️

Got the code? Submit it instantly.

Run the script, and it'll ask for the code:
```bash
python3 submit_attendance.py
```

Or, for lightning-fast submission, pass the code as an argument:
```bash
python3 submit_attendance.py 123
```

### 3. Find the Code (Experimental) 🕵️

**Again, read the disclaimer before proceeding.** This script is the main event. It will try to find the correct code for you.

```bash
python3 find_attendance_code.py
```
A progress bar will appear, and hopefully, you'll see a success message with the found code! 🎉
