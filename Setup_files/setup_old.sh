#!/bin/bash

# --- Update System ---
echo "Updating system..."
sudo apt update && sudo apt upgrade -y

# --- Create Directories ---
echo "Creating directories..."
mkdir -p /home/Sharukh/CIAP
mkdir -p /home/Sharukh/CIAP_RPI

# --- Pull from GitHub ---
echo "Cloning/Updating Git repository..."
cd /home/Sharukh/CIAP_RPI || exit
git pull https://github.com/suraj-bhalerao/CIAP_RPI.git || git clone https://github.com/suraj-bhalerao/CIAP_RPI.git .

# --- Copy AEP.sh to Desktop ---
echo "Copying AEP.sh to Desktop..."
sudo cp /home/Sharukh/CIAP_RPI/AEP.sh /home/Sharukh/Desktop/
sudo chmod +x /home/Sharukh/Desktop/AEP.sh

# --- Copy Logger.py and one.py ---
echo "Copying Logger.py and one.py to /home/Sharukh/CIAP..."
sudo cp /home/Sharukh/CIAP_RPI/Logger.py /home/Sharukh/CIAP/
sudo cp /home/Sharukh/CIAP_RPI/one.py /home/Sharukh/CIAP/
sudo chmod +x /home/Sharukh/CIAP/one.py

# --- Copy rc.local ---
echo "Replacing rc.local..."
sudo cp /home/Sharukh/CIAP_RPI/rc.local /etc/
sudo chmod +x /etc/rc.local

# --- Copy .desktop file ---
echo "Copying autostart desktop file..."
sudo cp /home/Sharukh/CIAP_RPI/atculogger.desktop /etc/xdg/autostart/
sudo chmod +x /etc/xdg/autostart/atculogger.desktop

# --- RTC Battery Charging Config --- 
echo "Configuring RTC battery charging..."
CONFIG_FILE="/boot/firmware/config.txt"
RTC_PARAM="dtparam=rtc_bbat_vchg=3000000"

# Append only if the parameter is not already present
if ! grep -Fxq "$RTC_PARAM" "$CONFIG_FILE"; then
    echo "$RTC_PARAM" | sudo tee -a "$CONFIG_FILE" > /dev/null
    echo "RTC charging parameter added."
else
    echo "RTC charging parameter already present."
fi

# --- Create systemd service for one.py ---
echo "Creating systemd service for one.py..."
SERVICE_PATH="/etc/systemd/system/onedrive-upload.service"
sudo bash -c "cat > $SERVICE_PATH" << EOF
[Unit]
Description=Upload RPi Logs to OneDrive
After=network.target

[Service]
ExecStart=/usr/bin/python3 /home/Sharukh/CIAP/one.py
WorkingDirectory=/home/Sharukh
Restart=always
User=Sharukh

[Install]
WantedBy=multi-user.target
EOF

sudo chmod 644 "$SERVICE_PATH"
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl enable onedrive-upload.service
sudo systemctl start onedrive-upload.service

# --- Install rclone ---
echo "Installing rclone..."
#sudo apt install -y rclone
sudo -v ; curl https://rclone.org/install.sh | sudo bash

echo ""
echo "=============================================="
echo "RCLONE NOT YET CONFIGURED"
echo "You still need to manually run: rclone config"
echo "Follow the prompts to link your OneDrive account."
echo "Once done, one.py will begin syncing."
echo "=============================================="

echo "Setup complete!"
