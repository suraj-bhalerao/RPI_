#!/usr/bin/env python3
import os
import subprocess
import platform
import time
from datetime import datetime

LOG_DIR = "/home/Sharukh/CIAP"
ONEDRIVE_DIR = "AEPL:/Rpi_Logs"
UPLOADED_LOGS_FILE = "/home/Sharukh/CIAP/uploaded_logs.txt"

def is_connected_to_wifi():
    try:
        ssid = subprocess.check_output(['iwgetid', '-r']).decode().strip()
        if ssid:
            print(f"Connected to network: {ssid}")
            return True
        else:
            return False
    except subprocess.CalledProcessError:
        return False
    except Exception as e:
        print(f"Error checking Wi-Fi: {e}")
        return False

def is_file_open(file_path):
    try:
        result = subprocess.run(['lsof', file_path], capture_output=True, text=True)
        return bool(result.stdout.strip())
    except Exception as e:
        print(f"Error checking if file is open: {e}")
        return False

def get_log_files():
    return [f for f in os.listdir(LOG_DIR) if f.startswith("serial_log_") and f.endswith(".log")]

def load_uploaded_logs():
    if not os.path.exists(UPLOADED_LOGS_FILE):
        return set()
    with open(UPLOADED_LOGS_FILE, 'r') as f:
        return set(line.strip() for line in f.readlines())

def mark_log_as_uploaded(log_file):
    with open(UPLOADED_LOGS_FILE, 'a') as f:
        f.write(log_file + '\n')

def upload_to_onedrive(file_path, hostname, today_date):
    if not os.path.isfile(file_path):
        print(f"File not found: {file_path}")
        return

    remote_dir = f"{ONEDRIVE_DIR}/{hostname}/{today_date}"

    try:
        result = subprocess.run([
            "/usr/bin/rclone", "copy", file_path, remote_dir
        ], capture_output=True, text=True)

        if result.returncode == 0:
            print(f"Uploaded {file_path} to {remote_dir}.")
            mark_log_as_uploaded(os.path.basename(file_path))
        else:
            print(f"Error uploading {file_path}: {result.stderr}")
    except Exception as e:
        print(f"Error during upload: {e}")

#### this functions is used to check zero size and currupted files
# def is_log_file_valid(file_path):
#     try:
#         if os.path.getsize(file_path) == 0:
#             print(f"Skipping empty file: {file_path}")
#             return False
#         with open(file_path, 'r', errors='ignore') as f:
#             content = f.read(1024)  # Read first 1KB
#             if not any(c.isprintable() for c in content):
#                 print(f"Skipping possibly corrupted file (unprintable): {file_path}")
#                 return False
#         return True
#     except Exception as e:
#         print(f"Error validating file {file_path}: {e}")
#         return False

def is_non_empty_file(file_path):
    return os.path.getsize(file_path) > 0

def main():
    if is_connected_to_wifi():
        uploaded_logs = load_uploaded_logs()
        log_files = get_log_files()
        hostname = platform.node()
        today_date = datetime.now().strftime("%Y-%m-%d")

        for log_file in log_files:
            if log_file in uploaded_logs:
                print(f"Already uploaded: {log_file}")
                continue

            log_file_path = os.path.join(LOG_DIR, log_file)

            if is_file_open(log_file_path):
                print(f"Skipping open file: {log_file}")
                continue
            # if not is_log_file_valid(log_file_path):
            #     continue
            if not is_non_empty_file(log_file_path):
                print(f"Skipping empty file: {log_file}")
                continue
            upload_to_onedrive(log_file_path, hostname, today_date)
    else:
        print("Not connected to Wi-Fi.")

def main_loop():
    while True:
        main()
        time.sleep(30)  

if __name__ == "__main__":
    main_loop()
