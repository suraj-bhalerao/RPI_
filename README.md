# AEPL Serial Logger

AEPL Serial Logger is a Python-based desktop application that automates the process of detecting serial devices, logging real-time data from them (especially IMEI responses), and executing pre-defined command scripts (TTL Macros). It is designed for diagnostic, testing, or production line environments where devices communicate over serial ports.

---

## 🚀 Overview

This application is designed to:

- Continuously monitor available serial ports and automatically connect to newly attached devices.
- Extract IMEI numbers from incoming data and dynamically create logs based on them.
- Run scripted commands from `.ttl` files to automate device communication.
- Provide an intuitive graphical user interface (GUI) for interacting with logs, devices, and macros.

The logger is ideal for environments where devices connect and disconnect frequently, and where capturing clean, structured log data is essential.

---

## 🔧 Key Features

### 1. **Auto Serial Port Detection**
- The app automatically detects when a new serial port becomes available.
- Connects to the first available port using a default baudrate (115200).
- Disconnects and stops logging if the device is unplugged.

### 2. **IMEI Extraction and Dynamic Logging**
- When the app receives a string like `STATUS#IMEI#<IMEI_NUMBER>#`, it extracts the IMEI and:
  - Creates a new log file named after the IMEI and current timestamp.
  - Redirects future logs to that IMEI-specific file.
- All logs are timestamped.
- Before detecting an IMEI, logs are saved to a fallback file (`default.log`).

### 3. **Fallback Logging**
- If the device does not respond with an IMEI or is still initializing, logs are written to a fallback file until the IMEI is received.

### 4. **ANSI Escape Code Removal**
- The logger removes ANSI color codes and escape sequences from incoming data to ensure clean logs.

### 5. **TTL Macro Execution**
- Supports automated command execution using `.ttl` script files.
- Each line in the file represents either:
  - A serial command (`*COMMAND`)
  - A pause instruction (`pause <seconds>`)
- Commands are executed sequentially with support for timed delays.

Example TTL macro:
```ttl
*GET#VERSION#
pause 2
*SET#CONFIG#1
