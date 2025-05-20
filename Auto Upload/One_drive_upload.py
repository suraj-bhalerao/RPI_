# import os

# import subprocess                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               		    

# LOG_DIR = "/home/sharukh/CIAP"  
# ONEDRIVE_DIR = "onedrive:/Rpi_Logs" 
# HOME_NETWORKS = ["AEPL-R&D"] 
# UPLOADED_LOGS_FILE = "/home/sharukh/CIAP/uploaded_logs.txt" 
# API_ENDPOINT = "http://atcu-qadata.accoladeelectronics.com:6101/httpFileManagement/uploadFile"

# def is_home_network():
#     try:
#         current_ssid = subprocess.check_output(['iwgetid','-r']).decode().strip()
#         return current_ssid in HOME_NETWORKS
#     except Exception as e:
#         print(f"Error getting SSID: {e}")
#         return False

# def get_log_files():
#     return [f for f in os.listdir(LOG_DIR) if f.startswith("serial_log_") and f.endswith(".log")]

# def load_uploaded_logs():
#     if not os.path.exists(UPLOADED_LOGS_FILE):
#         return set()
#     with open(UPLOADED_LOGS_FILE, 'r') as f:
#         return set(line.strip() for line in f.readlines())

# def mark_log_as_uploaded(log_file):
#     with open(UPLOADED_LOGS_FILE, 'a') as f:
#         f.write(log_file + '\n')

# def upload_to_onedrive(file_path):
#     if not os.path.isfile(file_path):
#         print(f"File not found: {file_path}")
#         return

#     try:
#         result = subprocess.run(["/usr/bin/rclone", "copy", file_path, ONEDRIVE_DIR], capture_output=True, text=True)
#         if result.returncode == 0:
#             print(f"Uploaded {file_path} to OneDrive.")
#             mark_log_as_uploaded(os.path.basename(file_path))  
#         else:
#             print(f"Error uploading {file_path}: {result.stderr}")
#     except Exception as e:
#         print(f"Error during upload: {e}")


# # To upload to server
# def upload_to_server(file_path):
#     """ Uploads log file to the server via API """
#     if not os.path.isfile(file_path):
#         print(f"File not found: {file_path}")
#         return False

#     try:
#         with open(file_path, 'rb') as f:
#             files = {'file': f}
#             response = requests.post(API_ENDPOINT, files=files)

#         if response.status_code == 200:
#             print(f"Uploaded {file_path} to server successfully.")
#             return True
#         else:
#             print(f"Failed to upload {file_path} to server. Status: {response.status_code}, Response: {response.text}")
#             return False
#     except Exception as e:
#         print(f"Error uploading {file_path} to server: {e}")
#         return False

# def list_onedrive_files():
#     try:
#         result = subprocess.run(
#             ["/usr/bin/rclone", "ls", ONEDRIVE_DIR],
#             capture_output=True, text=True
#         )
#         if result.returncode == 0:
#             return set(line.split()[1] for line in result.stdout.splitlines())
#         else:
#             print(f"Error listing OneDrive files: {result.stderr}")
#             return set()
#     except Exception as e:
#         print(f"Error during listing OneDrive files: {e}")
#         return set()

# def main():
#     if is_home_network():
#         uploaded_logs = load_uploaded_logs()
#         onedrive_files = list_onedrive_files()
#         log_files = get_log_files()

#         for log_file in log_files:
#             if log_file not in uploaded_logs and log_file not in onedrive_files:
#                 log_file_path = os.path.join(LOG_DIR, log_file)

#                 # Upload to OneDrive
#                 onedrive_success = upload_to_onedrive(log_file_path)

#                 # Upload to API Server
#                 server_success = upload_to_server(log_file_path)

#                 if onedrive_success or server_success:
#                     mark_log_as_uploaded(log_file)
#             else:
#                 if log_file in uploaded_logs:
#                     print(f"Log already uploaded (local record): {log_file}")
#                 if log_file in onedrive_files:
#                     print(f"Log already uploaded (OneDrive): {log_file}")
#     else:
#         print("Not connected to home network.")

# if __name__ == "__main__":
#     main()

import os
import subprocess
import requests
import platform
from datetime import datetime

# === CONFIGURATION ===
LOG_DIR = r"D:\LOG\FOTA\17-04-25"  # Use raw string or double backslashes
ONEDRIVE_DIR = "onedrive:/Rpi_Logs"
HOME_NETWORKS = ["AEPL-R&D"]
UPLOADED_LOGS_FILE = r"D:\LOG\FOTA\uploaded_logs.txt"
API_ENDPOINT = "http://atcu-qadata.accoladeelectronics.com:6101/httpFileManagement/uploadFile"

# === UTILITY FUNCTIONS ===

def get_current_ssid():
    try:
        if platform.system() == "Linux":
            ssid = subprocess.check_output(['iwgetid', '-r']).decode().strip()
        elif platform.system() == "Windows":
            output = subprocess.check_output("netsh wlan show interfaces", shell=True).decode(errors="ignore")
            if "State" not in output or "connected" not in output.lower():
                return None  # Not connected to Wi-Fi
            for line in output.splitlines():
                if "SSID" in line and "BSSID" not in line:
                    return line.split(":", 1)[1].strip()
        else:
            print("[ERROR] Unsupported OS for SSID check.")
            return None
        return ssid
    except subprocess.CalledProcessError:
        return None  # Return None if command fails
    except Exception as e:
        print(f"[ERROR] Could not get SSID: {e}")
        return None


def is_home_network():
    print("[INFO] Skipping SSID check. Assuming trusted network.")
    return True

def get_log_files():
    """Find all relevant log files in the log directory"""
    return [f for f in os.listdir(LOG_DIR) if f.startswith("serial_log_") and f.endswith(".log")]

def load_uploaded_logs():
    """Load the list of already uploaded log files"""
    if not os.path.exists(UPLOADED_LOGS_FILE):
        return set()
    with open(UPLOADED_LOGS_FILE, 'r') as f:
        return set(line.strip() for line in f.readlines())

def mark_log_as_uploaded(log_file):
    """Mark a log file as uploaded"""
    with open(UPLOADED_LOGS_FILE, 'a') as f:
        f.write(log_file + '\n')

def upload_to_onedrive(file_path):
    """Upload a file to OneDrive using rclone"""
    if not os.path.isfile(file_path):
        print(f"[ERROR] File not found: {file_path}")
        return False

    try:
        result = subprocess.run(
            ["rclone", "copy", file_path, ONEDRIVE_DIR],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print(f"[SUCCESS] Uploaded to OneDrive: {file_path}")
            return True
        else:
            print(f"[ERROR] OneDrive upload failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"[ERROR] Exception during OneDrive upload: {e}")
        return False

def upload_to_server(file_path):
    """Upload a file to the remote server via API"""
    if not os.path.isfile(file_path):
        print(f"[ERROR] File not found: {file_path}")
        return False

    try:
        with open(file_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(API_ENDPOINT, files=files)

        if response.status_code == 200:
            print(f"[SUCCESS] Uploaded to server: {file_path}")
            return True
        else:
            print(f"[ERROR] Server upload failed. Status {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"[ERROR] Exception during server upload: {e}")
        return False

def list_onedrive_files():
    """List existing files on OneDrive to prevent re-uploads"""
    try:
        result = subprocess.run(
            ["rclone", "ls", ONEDRIVE_DIR],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            return set(line.split()[1] for line in result.stdout.splitlines())
        else:
            print(f"[ERROR] Could not list OneDrive files: {result.stderr}")
            return set()
    except Exception as e:
        print(f"[ERROR] Exception during listing OneDrive files: {e}")
        return set()

# === MAIN FUNCTION ===

def main():
    print(f"[{datetime.now()}] Starting log uploader...")

    if not is_home_network():
        print("[INFO] Not connected to a trusted home network. Exiting.")
        return

    uploaded_logs = load_uploaded_logs()
    onedrive_files = list_onedrive_files()
    log_files = get_log_files()

    for log_file in log_files:
        if log_file in uploaded_logs or log_file in onedrive_files:
            print(f"[SKIP] Already uploaded: {log_file}")
            continue

        full_path = os.path.join(LOG_DIR, log_file)

        # Attempt uploads
        onedrive_success = upload_to_onedrive(full_path)
        server_success = upload_to_server(full_path)

        if onedrive_success or server_success:
            mark_log_as_uploaded(log_file)
        else:
            print(f"[WARN] Upload failed for: {log_file}")

    print(f"[{datetime.now()}] Log uploader finished.")

# === ENTRY POINT ===

if __name__ == "__main__":
    main()
