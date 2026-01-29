<h1 align="center">Android Device Info Viewer</h1>
<p align= center>Python tool to extract detailed information from connected Android devices via ADB</p>

![Python Version](https://img.shields.io/badge/python-3.7+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)
![ADB](https://img.shields.io/badge/ADB-Required-orange.svg)

## ✨ Features
📊 Device Info: ID, serial, model, manufacturer

🔋 Battery Health: Percentage, health rating, temperature, voltage

🤖 Android Info: Version, API level, security patch, build number

🌍 Region: Locale, country code

⚙️ Hardware: CPU, RAM, storage, screen resolution

🔒 Security: Root status, USB debugging status

## 🚀 Quick Start
1. Install ADB
2. Prepare Your Android Device
```cmd
# Enable Developer Options
Settings → About Phone → Tap "Build Number" 7 times

# Enable USB Debugging
Settings → Developer Options → Enable USB Debugging
```
3. Clone repository
```cmd
git clone https://github.com/Misuu-Code/Android-Device-Viewer.git
cd android-device-info

# Install dependencies
pip install colorama

# Run tool
python device_info.py
```

## 🤝 Contributing
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## ⚠️ Disclaimer
For educational and personal use only.
Not for unauthorized access or malicious purposes.

