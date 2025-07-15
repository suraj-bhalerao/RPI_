#!/usr/bin/env python3
import os
import subprocess
import platform
import time
from datetime import datetime

BASE_LOG_DIR = "/home/Sharukh/CIAP/logs"
ONEDRIVE_ROOT = "AEPL:/Rpi_Logs"
UPLOADED_LOGS_FILE = f"{BASE_LOG_DIR}/uploaded_logs.txt"

def is_connected_to_wifi():
    try:
        ssid = subprocess.check_output(['iwgetid', '-r']).decode().strip()
        if ssid == False:
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

def get_all_log_files():
    log_files = []
    for root, dirs, files in os.walk(BASE_LOG_DIR):
        for file in files:
            if file.endswith(".log") and file.startswith("serial_log_"):
                full_path = os.path.join(root, file)
                date_part = os.path.basename(os.path.dirname(full_path))
                log_files.append((full_path, date_part))
    return log_files

def load_uploaded_logs():
    if not os.path.exists(UPLOADED_LOGS_FILE):
        return set()
    with open(UPLOADED_LOGS_FILE, 'r') as f:
        return set(line.strip() for line in f.readlines())

def mark_log_as_uploaded(log_file):
    with open(UPLOADED_LOGS_FILE, 'a') as f:
        f.write(log_file + '\n')

def upload_to_onedrive(file_path, hostname, date_part):
    if not os.path.isfile(file_path):
        print(f"File not found: {file_path}")
        return

    remote_dir = f"{ONEDRIVE_ROOT}/{hostname}/{date_part}"
    try:
        result = subprocess.run(
            ["/usr/bin/rclone", "copy", file_path, remote_dir],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print(f"Uploaded: {file_path} → {remote_dir}")
            mark_log_as_uploaded(os.path.basename(file_path))
        else:
            print(f"Upload error: {result.stderr}")
    except Exception as e:
        print(f"Upload failed: {e}")

def main():
    if is_connected_to_wifi():
        uploaded_logs = load_uploaded_logs()
        hostname = platform.node()

        for file_path, date_part in get_all_log_files():
            file_name = os.path.basename(file_path)

            if file_name in uploaded_logs:
                print(f"Already uploaded: {file_name}")
                continue
            if is_file_open(file_path):
                print(f"Skipping open file: {file_name}")
                continue

            upload_to_onedrive(file_path, hostname, date_part)
    else:
        print("Wi-Fi not connected. Skipping upload.")

def main_loop():
    while True:
        main()
        time.sleep(30) 

if __name__ == "__main__":
    main_loop()
