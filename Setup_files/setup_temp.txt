#!/bin/bash

# --- Define Variables ---
USER_NAME="Sharukh"
HOME_DIR="/home/$USER_NAME"
CIAP_DIR="$HOME_DIR/CIAP"
CIAP_RPI_DIR="$HOME_DIR/CIAP_RPI"
DESKTOP_DIR="$HOME_DIR/Desktop"
GIT_REPO_URL="https://github.com/suraj-bhalerao/CIAP_RPI.git"
RC_LOCAL="/etc/rc.local"
AUTOSTART_DIR="/etc/xdg/autostart"
SERVICE_NAME="onedrive-upload.service"
SERVICE_PATH="/etc/systemd/system/$SERVICE_NAME"
PYTHON_SCRIPT="$CIAP_DIR/one.py"

# --- Update System ---
echo "Updating system..."
sudo apt update && sudo apt upgrade -y

# --- Create Directories ---
echo "Creating directories..."
mkdir -p "$CIAP_DIR"
mkdir -p "$CIAP_RPI_DIR"

# --- Pull from GitHub ---
echo "Cloning/Updating Git repository..."
cd "$CIAP_RPI_DIR" || exit
git pull "$GIT_REPO_URL" || git clone "$GIT_REPO_URL" .

# --- Copy AEP.sh to Desktop ---
echo "Copying AEP.sh to Desktop..."
sudo cp "$CIAP_RPI_DIR/AEP.sh" "$DESKTOP_DIR/"
sudo chmod +x "$DESKTOP_DIR/AEP.sh"

# --- Copy Logger.py and one.py ---
echo "Copying Logger.py and one.py to $CIAP_DIR..."
sudo cp "$CIAP_RPI_DIR/Logger.py" "$CIAP_DIR/"
sudo cp "$CIAP_RPI_DIR/one.py" "$CIAP_DIR/"
sudo chmod +x "$PYTHON_SCRIPT"

# --- Copy rc.local ---
echo "Replacing rc.local..."
sudo cp "$CIAP_RPI_DIR/rc.local" "$RC_LOCAL"
sudo chmod +x "$RC_LOCAL"

# --- Copy .desktop file ---
echo "Copying autostart desktop file..."
sudo cp "$CIAP_RPI_DIR/atculogger.desktop" "$AUTOSTART_DIR/"
sudo chmod +x "$AUTOSTART_DIR/atculogger.desktop"

# --- Create systemd service for one.py ---
echo "Creating systemd service for one.py..."
sudo bash -c "cat > $SERVICE_PATH" << EOF
[Unit]
Description=Upload RPi Logs to OneDrive
After=network.target

[Service]
ExecStart=/usr/bin/python3 $PYTHON_SCRIPT
WorkingDirectory=$HOME_DIR
Restart=always
User=${USER_NAME}

[Install]
WantedBy=multi-user.target
EOF

sudo chmod 644 "$SERVICE_PATH"
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl start "$SERVICE_NAME"

# --- Install rclone ---
echo "Installing rclone..."
sudo -v ; curl https://rclone.org/install.sh | sudo bash

echo ""
echo "======================================================="
echo "RCLONE NOT YET CONFIGURED"
echo "You still need to manually run: rclone config"
echo "Follow the prompts to link your OneDrive account."
echo "Once done, one.py will begin syncing."
echo "NOTE : You have to manually configure the RPI-Connect"
echo "======================================================="

echo "Setup complete!"
