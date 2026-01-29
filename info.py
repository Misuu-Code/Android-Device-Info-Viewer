#!/usr/bin/env python3
"""
Android Device Info Viewer
"""

import subprocess
import sys
import os
from datetime import datetime
import json
from colorama import Fore, Style, init
import platform
import re
import time

# Initialize colorama
init(autoreset=True)

class Color:
    """Warna untuk output"""
    HEADER = Fore.MAGENTA + Style.BRIGHT
    TITLE = Fore.CYAN + Style.BRIGHT
    SUCCESS = Fore.GREEN
    WARNING = Fore.YELLOW
    ERROR = Fore.RED
    INFO = Fore.BLUE
    RESET = Style.RESET_ALL

def check_adb_installed():
    """Cek apakah ADB sudah terinstall dan bisa diakses"""
    # Coba beberapa lokasi umum ADB
    possible_adb_paths = [
        'adb',  # Jika sudah di PATH
        os.path.join(os.getenv('ANDROID_HOME', ''), 'platform-tools', 'adb'),
        os.path.join(os.getenv('ANDROID_SDK_ROOT', ''), 'platform-tools', 'adb'),
        'platform-tools/adb',  # Relative path
        './platform-tools/adb',  # Current directory
        '../platform-tools/adb',  # Parent directory
    ]
    
    # Untuk Windows
    if platform.system() == "Windows":
        possible_adb_paths.extend([
            'adb.exe',
            'platform-tools\\adb.exe',
            '.\\platform-tools\\adb.exe',
            '..\\platform-tools\\adb.exe',
            os.path.join(os.getcwd(), 'platform-tools', 'adb.exe'),
            os.path.join(os.path.dirname(os.getcwd()), 'platform-tools', 'adb.exe'),
        ])
    
    # Coba setiap path
    for adb_path in possible_adb_paths:
        try:
            result = subprocess.run([adb_path, '--version'], 
                                   capture_output=True, 
                                   text=True,
                                   creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0)
            if result.returncode == 0:
                return True, adb_path
        except (FileNotFoundError, PermissionError):
            continue
    
    return False, None

def run_adb_command_safe(command, device_id=None, adb_path='adb'):
    """Jalankan command ADB dengan error handling yang lebih baik"""
    try:
        # Untuk command shell, gunakan pendekatan berbeda
        if '|' in command or '>' in command or 'cat' in command or 'grep' in command:
            # Gunakan shell command dengan format yang benar
            full_cmd = f'shell "{command}"'
            cmd = [adb_path]
            if device_id:
                cmd.extend(['-s', device_id])
            cmd.extend(full_cmd.split())
            
            result = subprocess.run(cmd, 
                                   capture_output=True, 
                                   text=True, 
                                   timeout=10,
                                   creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0,
                                   encoding='utf-8',
                                   errors='ignore')
            return result.stdout.strip()
        else:
            # Untuk command biasa
            cmd = [adb_path]
            if device_id:
                cmd.extend(['-s', device_id])
            cmd.extend(['shell', command])
            
            result = subprocess.run(cmd, 
                                   capture_output=True, 
                                   text=True, 
                                   timeout=10,
                                   creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0,
                                   encoding='utf-8',
                                   errors='ignore')
            return result.stdout.strip()
            
    except subprocess.TimeoutExpired:
        return "Timeout"
    except Exception as e:
        return f"Error: {str(e)}"

def run_adb_command(command, device_id=None, adb_path='adb'):
    """Jalankan command ADB - versi sederhana"""
    try:
        cmd = [adb_path]
        if device_id:
            cmd.extend(['-s', device_id])
        cmd.extend(['shell', command])
        
        result = subprocess.run(cmd, 
                               capture_output=True, 
                               text=True, 
                               timeout=10,
                               creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0,
                               encoding='utf-8',
                               errors='ignore')
        return result.stdout.strip()
    except Exception as e:
        return ""

def get_connected_devices(adb_path='adb'):
    """Dapatkan list device yang terkoneksi"""
    try:
        result = subprocess.run([adb_path, 'devices'], 
                               capture_output=True, 
                               text=True,
                               creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0)
        output = result.stdout
        devices = []
        
        if output:
            lines = output.split('\n')
            for line in lines:
                if line.strip() and '\t' in line and 'device' in line:
                    device_id, status = line.strip().split('\t')
                    if status == 'device':
                        devices.append(device_id)
        
        return devices
    except:
        return []

def get_battery_info(device_id, adb_path='adb'):
    """Dapatkan informasi battery lengkap dengan multiple methods"""
    battery_info = {}
    
    # Method 1: dumpsys battery (standard method)
    battery_output = run_adb_command('dumpsys battery', device_id, adb_path)
    
    if battery_output and len(battery_output) > 10:
        battery_info['raw_output'] = battery_output
        
        # Parse dengan regex yang lebih toleran
        patterns = {
            'level': r'level.*?:.*?(\d+)',
            'scale': r'scale.*?:.*?(\d+)',
            'status': r'status.*?:.*?(\d+)',
            'health': r'health.*?:.*?(\d+)',
            'plugged': r'plugged.*?:.*?(\d+)',
            'voltage': r'voltage.*?:.*?(\d+)',
            'temperature': r'temperature.*?:.*?(\d+)',
            'technology': r'technology.*?:.*?(\w+)',
            'present': r'present.*?:\s*(true|false)',
            'capacity': r'capacity.*?:.*?(\d+)'
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, battery_output, re.IGNORECASE)
            if match:
                battery_info[key] = match.group(1)
        
        # Calculate percentage
        if 'level' in battery_info and 'scale' in battery_info:
            try:
                level = int(battery_info['level'])
                scale = int(battery_info.get('scale', 100))
                if scale > 0:
                    percentage = (level / scale) * 100
                    battery_info['percentage'] = round(percentage, 1)
            except:
                pass
        
        # Map values to text
        if 'status' in battery_info:
            status_map = {'1': 'Unknown', '2': 'Charging', '3': 'Discharging', '4': 'Not Charging', '5': 'Full'}
            battery_info['status_text'] = status_map.get(battery_info['status'], 'Unknown')
        
        if 'health' in battery_info:
            health_map = {'1': 'Unknown', '2': 'Good', '3': 'Overheat', '4': 'Dead', '5': 'Over Voltage', '6': 'Unspecified Failure', '7': 'Cold'}
            battery_info['health_text'] = health_map.get(battery_info['health'], 'Unknown')
        
        if 'plugged' in battery_info:
            plugged_map = {'0': 'Not Plugged', '1': 'AC', '2': 'USB', '3': 'Wireless', '4': 'Power Bank'}
            battery_info['plugged_text'] = plugged_map.get(battery_info['plugged'], 'Unknown')
        
        # Convert temperature
        if 'temperature' in battery_info:
            try:
                temp_c = int(battery_info['temperature']) / 10.0
                battery_info['temperature_c'] = round(temp_c, 1)
                battery_info['temperature_f'] = round((temp_c * 9/5) + 32, 1)
            except:
                pass
        
        # Convert voltage
        if 'voltage' in battery_info:
            try:
                voltage_v = int(battery_info['voltage']) / 1000.0
                battery_info['voltage_v'] = round(voltage_v, 3)
            except:
                pass
    
    # Method 2: Alternative battery info
    if not battery_info:
        # Try alternative commands
        alt_commands = [
            'cat /sys/class/power_supply/battery/capacity',
            'cat /sys/class/power_supply/batttery/uevent | grep CAPACITY',
            'dumpsys power | grep mBatteryLevel'
        ]
        
        for cmd in alt_commands:
            result = run_adb_command(cmd, device_id, adb_path)
            if result and result.isdigit():
                battery_info['level'] = result
                battery_info['percentage'] = int(result)
                break
    
    return battery_info

def get_device_property(prop_name, device_id, adb_path='adb'):
    """Dapatkan property dengan multiple fallback methods"""
    # Method 1: Standard getprop
    result = run_adb_command(f'getprop {prop_name}', device_id, adb_path)
    
    if result and result.strip() and "error" not in result.lower() and "not found" not in result.lower():
        return result.strip()
    
    # Method 2: Try with different property names
    alt_props = {
        'ro.serialno': ['ro.boot.serialno', 'ril.serialnumber', 'sys.serialnumber'],
        'ro.product.model': ['ro.product.model.name', 'ro.product.device.model'],
        'ro.product.manufacturer': ['ro.product.brand.manufacturer', 'ro.product.vendor.manufacturer'],
        'ro.product.brand': ['ro.product.vendor.brand', 'ro.product.manufacturer.brand'],
        'ro.product.device': ['ro.hardware.device', 'ro.build.device'],
        'ro.product.name': ['ro.product.model.full', 'ro.build.product'],
        'ro.build.version.release': ['ro.build.version', 'ro.system.build.version.release'],
        'ro.build.version.sdk': ['ro.build.version.sdk_int', 'ro.sdk.version'],
        'ro.build.display.id': ['ro.build.id', 'ro.build.fingerprint'],
        'ro.build.version.security_patch': ['ro.vendor.build.security_patch', 'ro.build.security_patch'],
        'persist.sys.locale': ['ro.product.locale', 'ro.product.locale.region'],
        'gsm.sim.operator.iso-country': ['ro.csc.country_code', 'ro.product.locale.region']
    }
    
    if prop_name in alt_props:
        for alt_prop in alt_props[prop_name]:
            result = run_adb_command(f'getprop {alt_prop}', device_id, adb_path)
            if result and result.strip() and "error" not in result.lower():
                return result.strip()
    
    # Method 3: Try reading from build.prop
    if not result:
        build_prop = run_adb_command('cat /system/build.prop 2>/dev/null | grep -i "{}"'.format(prop_name.split('.')[-1]), device_id, adb_path)
        if build_prop:
            lines = build_prop.split('\n')
            for line in lines:
                if '=' in line:
                    key, value = line.split('=', 1)
                    if prop_name.split('.')[-1] in key.lower():
                        return value.strip()
    
    return None

def get_device_info_enhanced(device_id, adb_path='adb'):
    """Dapatkan informasi device dengan enhanced methods"""
    info = {
        'device_id': device_id,
        'timestamp': datetime.now().isoformat(),
        'status': 'connected'
    }
    
    # List of properties to get
    properties = [
        ('serial_number', 'ro.serialno'),
        ('model_name', 'ro.product.model'),
        ('manufacturer', 'ro.product.manufacturer'),
        ('brand', 'ro.product.brand'),
        ('device_name', 'ro.product.device'),
        ('product_name', 'ro.product.name'),
        ('android_version', 'ro.build.version.release'),
        ('api_level', 'ro.build.version.sdk'),
        ('build_number', 'ro.build.display.id'),
        ('security_patch', 'ro.build.version.security_patch'),
        ('region_locale', 'persist.sys.locale'),
        ('country_code', 'gsm.sim.operator.iso-country')
    ]
    
    # Get all properties
    for info_key, prop_name in properties:
        value = get_device_property(prop_name, device_id, adb_path)
        info[info_key] = value if value else "Unknown"
    
    # Get battery info
    battery_info = get_battery_info(device_id, adb_path)
    info['battery'] = battery_info if battery_info else {}
    
    # Try alternative methods for other info
    # CPU Architecture
    cpu = run_adb_command('getprop ro.product.cpu.abi', device_id, adb_path)
    if not cpu or not cpu.strip():
        cpu = run_adb_command('uname -m', device_id, adb_path)
    info['cpu_architecture'] = cpu.strip() if cpu and cpu.strip() else "Unknown"
    
    # Kernel version
    kernel = run_adb_command('uname -a', device_id, adb_path)
    info['kernel_version'] = kernel.strip() if kernel and kernel.strip() else "Unknown"
    
    # Uptime
    uptime = run_adb_command('cat /proc/uptime 2>/dev/null', device_id, adb_path)
    if uptime and uptime.strip():
        try:
            uptime_seconds = float(uptime.split()[0])
            hours = int(uptime_seconds // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            info['uptime'] = f"{hours}h {minutes}m"
        except:
            info['uptime'] = "Unknown"
    else:
        info['uptime'] = "Unknown"
    
    # Screen resolution - try multiple methods
    resolution = run_adb_command('wm size 2>/dev/null', device_id, adb_path)
    if not resolution or not resolution.strip():
        resolution = run_adb_command('dumpsys window displays 2>/dev/null | grep cur=', device_id, adb_path)
    info['screen_resolution'] = resolution.strip().replace("Physical size: ", "") if resolution and resolution.strip() else "Unknown"
    
    # RAM info
    ram = run_adb_command('cat /proc/meminfo 2>/dev/null | grep MemTotal', device_id, adb_path)
    if ram and ram.strip():
        match = re.search(r'MemTotal:\s+(\d+)', ram)
        if match:
            ram_kb = int(match.group(1))
            ram_gb = ram_kb / (1024 * 1024)
            info['total_ram_gb'] = round(ram_gb, 2)
        else:
            info['total_ram_gb'] = "Unknown"
    else:
        info['total_ram_gb'] = "Unknown"
    
    # Storage info
    storage = run_adb_command('df /data 2>/dev/null | tail -1', device_id, adb_path)
    if storage and storage.strip():
        parts = storage.split()
        if len(parts) >= 5:
            info['total_storage'] = parts[1]
            info['used_storage'] = parts[2]
            info['available_storage'] = parts[3]
            info['storage_use_percentage'] = parts[4]
        else:
            info['total_storage'] = "Unknown"
    else:
        info['total_storage'] = "Unknown"
    
    # Root status
    root_check = run_adb_command('which su 2>/dev/null', device_id, adb_path)
    info['root_status'] = "Rooted" if root_check and "/su" in root_check else "Not Rooted"
    
    # USB Debugging - check if we can run adb commands
    info['usb_debugging'] = "Enabled"  # Jika device terdeteksi, berarti USB debugging enabled
    
    # Device state
    state = run_adb_command('getprop sys.boot_completed', device_id, adb_path)
    info['device_state'] = "Boot Completed" if state and state.strip() == "1" else "Unknown"
    
    # IMEI - try multiple methods
    imei_methods = [
        'service call iphonesubinfo 1 2>/dev/null | grep -o "[0-9a-f]\\{8\\}" | head -n 1',
        'dumpsys iphonesubinfo 2>/dev/null | grep Device',
        'getprop gsm.device.id 2>/dev/null'
    ]
    
    imei_found = None
    for imei_cmd in imei_methods:
        imei = run_adb_command(imei_cmd, device_id, adb_path)
        if imei and imei.strip() and len(imei.strip()) > 3:
            imei_found = imei.strip()[:8]  # Take first 8 chars
            break
    
    info['imei_last_4'] = imei_found if imei_found else "Unknown"
    
    return info

def print_battery_info_enhanced(battery_info):
    """Tampilkan informasi battery dengan format yang bagus"""
    if not battery_info:
        print(f"{Color.WARNING}⚠️ Battery: Information not available{Color.RESET}")
        return
    
    print(f"\n{Color.TITLE}🔋 BATTERY INFORMATION{Color.RESET}")
    print(f"{'-'*40}")
    
    # Battery Level
    if 'percentage' in battery_info:
        percentage = battery_info['percentage']
        level_bar_length = 20
        filled = min(level_bar_length, int((percentage / 100) * level_bar_length))
        level_bar = "█" * filled + "░" * (level_bar_length - filled)
        color = Color.SUCCESS if percentage > 50 else Color.WARNING if percentage > 20 else Color.ERROR
        print(f"{Color.INFO}• Level:{Color.RESET}         {color}{percentage}%{Color.RESET}")
        print(f"            {color}{level_bar}{Color.RESET}")
    elif 'level' in battery_info:
        level = battery_info['level']
        scale = battery_info.get('scale', 100)
        print(f"{Color.INFO}• Level:{Color.RESET}         {level}/{scale}")
    
    # Battery Health
    if 'health_text' in battery_info:
        health = battery_info['health_text']
        color = Color.SUCCESS if health == 'Good' else Color.ERROR if health in ['Dead', 'Overheat'] else Color.WARNING
        print(f"{Color.INFO}• Health:{Color.RESET}        {color}{health}{Color.RESET}")
    
    # Battery Status
    if 'status_text' in battery_info:
        status = battery_info['status_text']
        color = Color.SUCCESS if status == 'Full' else Color.WARNING if status == 'Charging' else Color.INFO
        print(f"{Color.INFO}• Status:{Color.RESET}        {color}{status}{Color.RESET}")
    
    # Charging Source
    if 'plugged_text' in battery_info:
        plugged = battery_info['plugged_text']
        print(f"{Color.INFO}• Power Source:{Color.RESET}  {plugged}")
    
    # Voltage
    if 'voltage_v' in battery_info:
        voltage = battery_info['voltage_v']
        print(f"{Color.INFO}• Voltage:{Color.RESET}       {voltage} V")
    
    # Temperature
    if 'temperature_c' in battery_info:
        temp = battery_info['temperature_c']
        color = Color.ERROR if temp > 40 else Color.WARNING if temp > 35 else Color.SUCCESS
        print(f"{Color.INFO}• Temperature:{Color.RESET}   {color}{temp}°C{Color.RESET}")
    
    # Technology
    if 'technology' in battery_info:
        tech = battery_info['technology']
        print(f"{Color.INFO}• Technology:{Color.RESET}    {tech}")

def print_device_info_enhanced(info, device_num=1, total_devices=1):
    """Tampilkan informasi device dengan format yang bagus"""
    print(f"\n{Color.HEADER}{'='*60}")
    print(f"DEVICE INFO - {device_num}/{total_devices}")
    print(f"{'='*60}{Color.RESET}\n")
    
    # Helper function untuk display dengan warna
    def display_item(label, value):
        if value == "Unknown" or value == "Tidak tersedia":
            print(f"{Color.WARNING}• {label:20} {value}{Color.RESET}")
        else:
            print(f"{Color.INFO}• {label:20} {Color.SUCCESS}{value}{Color.RESET}")
    
    # Basic Info Section
    print(f"{Color.TITLE}📱 BASIC INFORMATION{Color.RESET}")
    print(f"{'-'*40}")
    display_item("Device ID:", info['device_id'])
    display_item("Serial Number:", info['serial_number'])
    display_item("Status:", info['status'])
    display_item("Timestamp:", info['timestamp'][:19].replace('T', ' '))
    display_item("Uptime:", info.get('uptime', 'Unknown'))
    
    # Device Info Section
    print(f"\n{Color.TITLE}📊 DEVICE SPECIFICATIONS{Color.RESET}")
    print(f"{'-'*40}")
    display_item("Manufacturer:", info['manufacturer'])
    display_item("Brand:", info['brand'])
    display_item("Model Name:", info['model_name'])
    display_item("Device Name:", info['device_name'])
    display_item("Product Name:", info['product_name'])
    
    # Android Info Section
    print(f"\n{Color.TITLE}🤖 ANDROID INFORMATION{Color.RESET}")
    print(f"{'-'*40}")
    display_item("Android Version:", info['android_version'])
    display_item("API Level:", info['api_level'])
    display_item("Build Number:", info['build_number'])
    display_item("Security Patch:", info['security_patch'])
    display_item("Kernel:", info.get('kernel_version', 'Unknown'))
    
    # Region & Location Section
    print(f"\n{Color.TITLE}🌍 REGION & LOCATION{Color.RESET}")
    print(f"{'-'*40}")
    display_item("Region/Locale:", info['region_locale'])
    display_item("Country Code:", info['country_code'])
    
    # Print Battery Information
    print_battery_info_enhanced(info.get('battery', {}))
    
    # Hardware Info Section
    print(f"\n{Color.TITLE}⚙️ HARDWARE INFORMATION{Color.RESET}")
    print(f"{'-'*40}")
    display_item("CPU Architecture:", info['cpu_architecture'])
    display_item("Total RAM:", f"{info.get('total_ram_gb', 'Unknown')} GB")
    display_item("Screen Resolution:", info['screen_resolution'])
    
    # Storage Info Section
    if info.get('total_storage') != "Unknown":
        print(f"\n{Color.TITLE}💾 STORAGE INFORMATION{Color.RESET}")
        print(f"{'-'*40}")
        display_item("Total Storage:", info.get('total_storage', 'Unknown'))
        display_item("Used Storage:", info.get('used_storage', 'Unknown'))
        display_item("Available Storage:", info.get('available_storage', 'Unknown'))
        if 'storage_use_percentage' in info:
            display_item("Usage:", info['storage_use_percentage'])
    
    # Security Info Section
    print(f"\n{Color.TITLE}🔒 SECURITY INFORMATION{Color.RESET}")
    print(f"{'-'*40}")
    display_item("Root Status:", info['root_status'])
    display_item("USB Debugging:", info['usb_debugging'])
    
    # Device State
    print(f"\n{Color.TITLE}🔋 DEVICE STATE{Color.RESET}")
    print(f"{'-'*40}")
    display_item("Device State:", info['device_state'])
    display_item("IMEI (last 4):", info.get('imei_last_4', 'Unknown'))
    
    print(f"\n{Color.SUCCESS}✓ Device information retrieved successfully{Color.RESET}")

def main():
    """Fungsi utama"""
    print(f"\n{Color.HEADER}{'='*60}")
    print("ANDROID DEVICE INFO VIEWER WITH BATTERY HEALTH")
    print("Enhanced Version - Multiple Fallback Methods")
    print("Authorized for Educational Use Only")
    print(f"{'='*60}{Color.RESET}\n")
    
    # Cek ADB
    print(f"{Color.INFO}[*] Checking ADB installation...{Color.RESET}")
    adb_installed, adb_path = check_adb_installed()
    
    if not adb_installed:
        print(f"{Color.WARNING}[!] ADB not found in PATH{Color.RESET}")
        
        # Try common locations
        common_paths = [
            os.path.join(os.getcwd(), 'platform-tools', 'adb.exe' if platform.system() == "Windows" else 'adb'),
            'adb.exe' if platform.system() == "Windows" else 'adb'
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                adb_path = path
                adb_installed = True
                print(f"{Color.SUCCESS}[✓] ADB found at: {adb_path}{Color.RESET}")
                break
        
        if not adb_installed:
            print(f"{Color.ERROR}[!] Please install ADB or specify path{Color.RESET}")
            print(f"{Color.INFO}[*] Download from: https://developer.android.com/studio/releases/platform-tools{Color.RESET}")
            sys.exit(1)
    
    print(f"{Color.SUCCESS}[✓] ADB ready: {adb_path}{Color.RESET}")
    
    # Restart ADB
    print(f"{Color.INFO}[*] Initializing ADB...{Color.RESET}")
    try:
        subprocess.run([adb_path, 'kill-server'], capture_output=True)
        subprocess.run([adb_path, 'start-server'], capture_output=True)
        time.sleep(2)
    except:
        pass
    
    # Check devices
    print(f"{Color.INFO}[*] Looking for connected devices...{Color.RESET}")
    devices = get_connected_devices(adb_path)
    
    if not devices:
        print(f"{Color.WARNING}[!] No Android devices detected!{Color.RESET}")
        print(f"{Color.INFO}[*] Please ensure:{Color.RESET}")
        print(f"    1. Device is connected via USB")
        print(f"    2. USB Debugging is enabled")
        print(f"    3. Allow USB Debugging when prompted")
        
        # Show adb devices output
        try:
            result = subprocess.run([adb_path, 'devices', '-l'], 
                                   capture_output=True, 
                                   text=True)
            print(f"\n{Color.INFO}[*] ADB Devices Output:{Color.RESET}")
            print(result.stdout)
        except:
            pass
        
        sys.exit(1)
    
    print(f"{Color.SUCCESS}[✓] Found {len(devices)} device(s){Color.RESET}")
    
    # Get info for each device
    all_devices_info = []
    for i, device_id in enumerate(devices, 1):
        print(f"\n{Color.INFO}[*] Getting information for device {i}/{len(devices)}...{Color.RESET}")
        print(f"{Color.INFO}[*] Device ID: {device_id}{Color.RESET}")
        
        # Get enhanced device info
        info = get_device_info_enhanced(device_id, adb_path)
        all_devices_info.append(info)
        
        # Display info
        print_device_info_enhanced(info, i, len(devices))
        
        # Ask to save
        if i == len(devices) or len(devices) == 1:
            choice = input(f"\n{Color.INFO}[?] Save to JSON file? (y/N): {Color.RESET}").lower()
            if choice == 'y':
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                model = info.get('model_name', 'unknown').replace(' ', '_').replace('/', '_')
                filename = f"device_info_{model}_{timestamp}.json"
                try:
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(info, f, indent=2, ensure_ascii=False)
                    print(f"{Color.SUCCESS}[✓] Saved to: {filename}{Color.RESET}")
                except Exception as e:
                    print(f"{Color.ERROR}[!] Failed to save: {str(e)}{Color.RESET}")
        
        # Continue to next device
        if i < len(devices):
            choice = input(f"\n{Color.INFO}[?] Continue to next device? (y/N): {Color.RESET}").lower()
            if choice != 'y':
                break
    
    print(f"\n{Color.SUCCESS}[✓] Scan completed successfully{Color.RESET}")
    print(f"{Color.INFO}[*] Press Enter to exit...{Color.RESET}")
    input()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Color.ERROR}[!] Program interrupted by user{Color.RESET}")
        sys.exit(0)
    except Exception as e:
        print(f"{Color.ERROR}[!] Unexpected error: {str(e)}{Color.RESET}")
        sys.exit(1)