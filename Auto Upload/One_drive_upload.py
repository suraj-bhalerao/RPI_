import os

import subprocess                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               		    

LOG_DIR = "/home/sharukh/CIAP"  
ONEDRIVE_DIR = "onedrive:/Rpi_Logs" 
HOME_NETWORKS = ["AEPL-R&D"] 
UPLOADED_LOGS_FILE = "/home/sharukh/CIAP/uploaded_logs.txt" 
API_ENDPOINT = "http://atcu-qadata.accoladeelectronics.com:6101/httpFileManagement/uploadFile"

def is_home_network():
    try:
        current_ssid = subprocess.check_output(['iwgetid','-r']).decode().strip()
        return current_ssid in HOME_NETWORKS
    except Exception as e:
        print(f"Error getting SSID: {e}")
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

def upload_to_onedrive(file_path):
    if not os.path.isfile(file_path):
        print(f"File not found: {file_path}")
        return

    try:
        result = subprocess.run(["/usr/bin/rclone", "copy", file_path, ONEDRIVE_DIR], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"Uploaded {file_path} to OneDrive.")
            mark_log_as_uploaded(os.path.basename(file_path))  
        else:
            print(f"Error uploading {file_path}: {result.stderr}")
    except Exception as e:
        print(f"Error during upload: {e}")


# To upload to server
def upload_to_server(file_path):
    """ Uploads log file to the server via API """
    if not os.path.isfile(file_path):
        print(f"File not found: {file_path}")
        return False

    try:
        with open(file_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(API_ENDPOINT, files=files)

        if response.status_code == 200:
            print(f"Uploaded {file_path} to server successfully.")
            return True
        else:
            print(f"Failed to upload {file_path} to server. Status: {response.status_code}, Response: {response.text}")
            return False
    except Exception as e:
        print(f"Error uploading {file_path} to server: {e}")
        return False

def list_onedrive_files():
    try:
        result = subprocess.run(
            ["/usr/bin/rclone", "ls", ONEDRIVE_DIR],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            return set(line.split()[1] for line in result.stdout.splitlines())
        else:
            print(f"Error listing OneDrive files: {result.stderr}")
            return set()
    except Exception as e:
        print(f"Error during listing OneDrive files: {e}")
        return set()

def main():
    if is_home_network():
        uploaded_logs = load_uploaded_logs()
        onedrive_files = list_onedrive_files()
        log_files = get_log_files()

        for log_file in log_files:
            if log_file not in uploaded_logs and log_file not in onedrive_files:
                log_file_path = os.path.join(LOG_DIR, log_file)

                # Upload to OneDrive
                onedrive_success = upload_to_onedrive(log_file_path)

                # Upload to API Server
                server_success = upload_to_server(log_file_path)

                if onedrive_success or server_success:
                    mark_log_as_uploaded(log_file)
            else:
                if log_file in uploaded_logs:
                    print(f"Log already uploaded (local record): {log_file}")
                if log_file in onedrive_files:
                    print(f"Log already uploaded (OneDrive): {log_file}")
    else:
        print("Not connected to home network.")

if __name__ == "__main__":
    main()
