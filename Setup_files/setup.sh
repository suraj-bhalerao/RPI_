#!/bin/bash

# --- Define Constants ---
USER_NAME="Sharukh"
HOME_DIR="/home/$USER_NAME"
CIAP_DIR="$HOME_DIR/CIAP"
SETUP_DIR="$CIAP_DIR/Setup_files"
UPLOAD_SCRIPT="$CIAP_DIR/Upload_script"
DESKTOP_DIR="$HOME_DIR/Desktop"
GIT_REPO_URL="https://github.com/suraj-bhalerao/RPI_.git"
RC_LOCAL="/etc/rc.local"
AUTOSTART_DIR="/etc/xdg/autostart"
SERVICE_NAME="onedrive-upload.service"
SERVICE_PATH="/etc/systemd/system/$SERVICE_NAME"
PYTHON_SCRIPT="$UPLOAD_SCRIPT/one.py"

# --- Update & Install Essentials ---
echo "🔄 Updating system..."
sudo apt update && sudo apt upgrade -y

echo "✅ Ensuring required packages..."
sudo apt install -y git curl lsof

# --- Clone or Pull Git Repository ---
echo "📁 Setting up CIAP directory at $CIAP_DIR..."
if [ -d "$CIAP_DIR/.git" ]; then
    echo "🔁 Pulling latest changes..."
    cd "$CIAP_DIR" && git pull
else
    echo "⬇️ Cloning repository..."
    git clone "$GIT_REPO_URL" "$CIAP_DIR"
fi

# --- Desktop Shortcut ---
AEP_SCRIPT="$SETUP_DIR/AEP.sh"
if [ -f "$AEP_SCRIPT" ]; then
    echo "🖥️ Copying AEP.sh to Desktop..."
    cp "$AEP_SCRIPT" "$DESKTOP_DIR/"
    chmod +x "$DESKTOP_DIR/AEP.sh"
fi

# --- Make Upload Script Executable ---
if [ -f "$PYTHON_SCRIPT" ]; then
    chmod +x "$PYTHON_SCRIPT"
fi

# --- Setup rc.local ---
RC_LOCAL_SRC="$SETUP_DIR/rc.local"
if [ -f "$RC_LOCAL_SRC" ]; then
    echo "⚙️ Installing rc.local..."
    sudo cp "$RC_LOCAL_SRC" "$RC_LOCAL"
    sudo chmod +x "$RC_LOCAL"
else
    echo "⚠️ rc.local not found in $SETUP_DIR"
fi

# --- Setup Autostart Entry ---
AUTOSTART_DESKTOP="$SETUP_DIR/atculogger.desktop"
if [ -f "$AUTOSTART_DESKTOP" ]; then
    echo "🔧 Setting up autostart..."
    sudo cp "$AUTOSTART_DESKTOP" "$AUTOSTART_DIR/"
    sudo chmod +x "$AUTOSTART_DIR/atculogger.desktop"
else
    echo "⚠️ atculogger.desktop not found."
fi

# --- Create Systemd Service ---
echo "🛠️ Creating systemd service: $SERVICE_NAME"
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

# --- Install rclone if Needed ---
if ! command -v rclone &> /dev/null; then
    echo "⬇️ Installing rclone..."
    curl https://rclone.org/install.sh | sudo bash
else
    echo "✅ rclone already installed."
fi

# --- Final Message ---
echo ""
echo "======================================================="
echo "✅ CIAP Setup Complete!"
echo "⚠️  REMEMBER TO CONFIGURE RCLONE MANUALLY:"
echo "    ➤ Run: rclone config"
echo "    ➤ Link to your OneDrive account"
echo "======================================================="
