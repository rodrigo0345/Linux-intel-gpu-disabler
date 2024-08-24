#!/usr/bin/env python3

import subprocess
import sys
import os

def execute_command(command):
    """Execute a shell command and return the output."""
    try:
        result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result.stdout.decode().strip()
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e}")
        print(e.stderr.decode())
        return ""

def backup_grub():
    """Backup the GRUB configuration file before modifying."""
    print("Backing up GRUB configuration...")
    grub_file = "/etc/default/grub"
    backup_file = f"{grub_file}-backup.bak"
    try:
        execute_command(f"cp {grub_file} {backup_file}")
        print(f"GRUB configuration backed up to {backup_file}.")
    except Exception as e:
        print(f"Failed to backup GRUB file: {e}")
        sys.exit(1)

def update_grub_for_blacklisting():
    """Update GRUB configuration to blacklist the Intel GPU driver."""
    print("Updating GRUB configuration to blacklist Intel GPU...")
    grub_file = "/etc/default/grub"
    grub_update_cmd = "/usr/sbin/grub2-mkconfig -o /boot/grub2/grub.cfg"  # Ensure full path is used
    
    # Backup GRUB before making changes
    backup_grub()

    # Update GRUB configuration
    with open(grub_file, 'r') as file:
        lines = file.readlines()

    with open(grub_file, 'w') as file:
        for line in lines:
            if line.startswith('GRUB_CMDLINE_LINUX'):
                # Remove any trailing spaces and single quotes at the end of the line
                line = line.strip()
                
                # Find the position of the last single quote in the line
                last_quote_index = line.rfind("'")
                
                # If the blacklist options are not already present, insert them before the last single quote
                if "modprobe.blacklist=i915" not in line:
                    # Insert the blacklist options before the closing quote
                    line = line[:last_quote_index] + " modprobe.blacklist=i915 nvidia-drm.modeset=1" + line[last_quote_index:]
                
                # Ensure the line ends with a newline character
                line = line + "\n"

            file.write(line)

    # Execute GRUB update command
    execute_command(grub_update_cmd)
    print("GRUB configuration updated. Please reboot for changes to take effect.")

def update_grub_for_enabling():
    """Update GRUB configuration to remove Intel GPU blacklist."""
    print("Updating GRUB configuration to enable Intel GPU...")
    grub_file = "/etc/default/grub"
    grub_update_cmd = "sudo /usr/sbin/grub2-mkconfig -o /boot/grub2/grub.cfg"
    rescan_devices = "echo 1 | sudo tee /sys/bus/pci/rescan"

    # Backup GRUB before making changes
    backup_grub()

    # Update GRUB configuration
    with open(grub_file, 'r') as file:
        lines = file.readlines()

    with open(grub_file, 'w') as file:
        for line in lines:
            if line.startswith('GRUB_CMDLINE_LINUX'):
                # Remove the blacklisting entries
                line = line.replace(" modprobe.blacklist=i915 nvidia-drm.modeset=1", "").strip()  # Remove the entries and strip extra whitespace
                line = line + "\n"
            file.write(line)


    execute_command(grub_update_cmd)
    execute_command(rescan_devices)
    print("GRUB configuration updated. Please reboot for changes to take effect.")

def create_systemd_service():
    """Create a systemd service to disable the Intel GPU."""
    print("Creating systemd service to disable Intel GPU...")
    service_file = "/etc/systemd/system/disable-intel-gpu.service"
    service_content = """
[Unit]
Description=Disable Intel GPU

[Service]
Type=oneshot
ExecStart=/usr/bin/bash -c 'echo 1 > /sys/bus/pci/devices/0000:00:02.0/remove'

[Install]
WantedBy=multi-user.target
"""

    try:
        with open(service_file, 'w') as file:
            file.write(service_content)
    except Exception as e:
        print(f"Failed to create systemd service: {e}")
        return

    execute_command("systemctl daemon-reload")
    execute_command("systemctl enable disable-intel-gpu.service")
    print("Systemd service created and enabled. Please reboot for changes to take effect.")

def get_intel_gpu_path():
    """Find the PCI device path for the Intel GPU."""
    try:
        path = execute_command("lspci | grep 'VGA compatible controller: Intel' | awk '{print $1}'")
        return f"/sys/bus/pci/devices/0000:{path.strip()}/remove"
    except Exception as e:
        print(f"Failed to find Intel GPU path: {e}")
        return None

def is_intel_gpu_enabled():
    """Check if the Intel GPU is enabled by verifying its presence in lspci output."""
    try:
        lspci_output = execute_command("lspci -nn | grep 'VGA compatible controller: Intel'")
        return "Intel" in lspci_output  # True if Intel GPU is present
    except Exception as e:
        print(f"Error checking Intel GPU status: {e}")
        return False

def disable_intel_gpu():
    """Disable the Intel GPU if it's currently enabled."""
    print("Disabling Intel GPU...")
    if not is_intel_gpu_enabled():
        print("Intel GPU is already disabled or not present.")
        return

    intel_gpu_path = get_intel_gpu_path()
    if intel_gpu_path:
        print(f"Intel GPU path detected: {intel_gpu_path}")
        if os.path.exists(intel_gpu_path):
            command = f"echo 1 > {intel_gpu_path}"
            execute_command(command)
            print("Intel GPU disabled.")
        else:
            print(f"Path does not exist: {intel_gpu_path}")
    else:
        print("Intel GPU path not found. Skipping GPU disable step.")

def enable_intel_gpu():
    """Enable the Intel GPU."""
    print("Enabling Intel GPU...")
    update_grub_for_enabling()  # Update GRUB to ensure Intel GPU is enabled
    command = "echo 1 > /sys/bus/pci/rescan"
    execute_command(command)
    print("Intel GPU enabled.")

def set_power_mode(mode):
    """Set GPU power mode and adjust CPU settings for eco, balanced, and performance modes."""
    if mode not in ["eco", "balanced", "performance"]:
        print("Invalid mode. Use 'eco', 'balanced', or 'performance'.")
        return

    print(f"Setting NVIDIA GPU power mode and system profile to {mode}...")

    # Set power profile using `powerprofilesctl`
    set_power_profile(mode)

    # Apply GPU power mode and CPU settings
    try:
        if mode == "eco":
            enable_intel_gpu()  # Ensure Intel GPU is enabled
            execute_command("nvidia-smi --persistence-mode=0")
            execute_command("nvidia-smi --auto-boost-default=0")
            set_cpu_governor("powersave")
        elif mode == "balanced":
            enable_intel_gpu()
            execute_command("nvidia-smi --persistence-mode=1")
            execute_command("nvidia-smi --auto-boost-default=1")
            set_cpu_governor("powersave")
        elif mode == "performance":
            disable_intel_gpu()  # Use only NVIDIA GPU
            execute_command("nvidia-smi --persistence-mode=1")
            execute_command("nvidia-smi --auto-boost-default=1")
            execute_command("nvidia-settings -a [gpu:0]/GPUPerfModes=1")
            set_cpu_governor("performance")
    except subprocess.CalledProcessError as e:
        print(f"Error setting power mode: {e}")

    print(f"NVIDIA GPU power mode and system profile set to {mode}.")

def check_status():
    """Check and display the current power modes."""
    print("Checking current power modes...")

    # Check NVIDIA GPU power mode
    try:
        gpu_persistence_mode = execute_command("nvidia-smi --query-gpu=persistence_mode --format=csv,noheader")
        gpu_power_limit = execute_command("nvidia-smi --query-gpu=power.limit --format=csv,noheader")
        gpu_perf_mode = execute_command("nvidia-settings -q [gpu:0]/GPUPerfModes")
        print("NVIDIA GPU Status:")
        print(f"Persistence Mode: {gpu_persistence_mode}")
        print(f"Power Limit: {gpu_power_limit}")
        print(f"Performance Mode: {gpu_perf_mode}")
    except Exception as e:
        print(f"Failed to retrieve NVIDIA GPU status: {e}")

    # Check system power profile
    try:
        system_profile = execute_command("powerprofilesctl get")
        print("System Power Profile:")
        print(system_profile)
    except subprocess.CalledProcessError as e:
        print(f"Failed to retrieve system power profile: {e}")

def set_power_profile(mode):
    """Set the system power profile using powerprofilesctl."""
    try:
        execute_command(f"powerprofilesctl set {mode}")
        print(f"System power profile set to {mode}.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to set power profile to {mode}: {e}")
        print("Check if power-profiles-daemon is running and configured correctly.")

def set_cpu_governor(governor):
    """Set the CPU frequency governor."""
    try:
        available_governors = execute_command("cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_available_governors")
        if governor in available_governors:
            execute_command(f"cpupower frequency-set -g {governor}")
            print(f"CPU governor set to {governor}.")
        else:
            print(f"Governor {governor} not available. Available governors: {available_governors.strip()}")
    except subprocess.CalledProcessError as e:
        print(f"Failed to set CPU governor to {governor}: {e}")
        print("Ensure cpupower is installed and the CPU driver is compatible.")

def is_first_run():
    """Check if the script is being run for the first time."""
    grub_file = "/etc/default/grub"
    try:
        return not os.path.exists(grub_file) or "i915" not in open(grub_file).read()
    except Exception as e:
        print(f"Error checking first run status: {e}")
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 gpu_control.py [enable|disable|eco|balanced|performance|status]")
        sys.exit(1)

    action = sys.argv[1].lower()

    if is_first_run():
        print("First-time setup detected.")
        update_grub_for_blacklisting()
        create_systemd_service()
    
    if action == "disable":
        disable_intel_gpu()
    elif action == "enable":
        enable_intel_gpu()
    elif action in ["eco", "balanced", "performance"]:
        set_power_mode(action)
    elif action == "status":
        check_status()
    else:
        print("Invalid action. Use 'enable', 'disable', 'eco', 'balanced', 'performance', or 'status'.")
        sys.exit(1)

    print("Please REBOOT the system")

if __name__ == "__main__":
    main()

