#!/usr/bin/env python3

import subprocess
import sys
import os

def execute_command(command):
    """Execute a shell command and print the output."""
    try:
        result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result.stdout.decode()
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e}")
        print(e.stderr.decode())
        return ""

def update_grub():
    """Update GRUB configuration to blacklist the Intel GPU driver."""
    print("Updating GRUB configuration...")
    grub_file = "/etc/default/grub"
    grub_update_cmd = "grub2-mkconfig -o /boot/grub2/grub.cfg"
    grub_update_uefi_cmd = "grub2-mkconfig -o /boot/efi/EFI/fedora/grub.cfg"

    # Backup existing GRUB file
    backup_file = f"{grub_file}.bak"
    execute_command(f"cp {grub_file} {backup_file}")

    # Append parameters to GRUB configuration
    with open(grub_file, 'a') as file:
        file.write('\nGRUB_CMDLINE_LINUX="rd.driver.blacklist=i915 modprobe.blacklist=i915 nvidia-drm.modeset=1"\n')

    execute_command(grub_update_cmd)
    execute_command(grub_update_uefi_cmd)
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

    # Create and write to the service file
    with open(service_file, 'w') as file:
        file.write(service_content)

    execute_command("systemctl daemon-reload")
    execute_command("systemctl enable disable-intel-gpu.service")
    print("Systemd service created and enabled. Please reboot for changes to take effect.")

def disable_intel_gpu():
    """Disable the Intel GPU."""
    print("Disabling Intel GPU...")
    command = "echo 1 > /sys/bus/pci/devices/0000:00:02.0/remove"
    execute_command(command)
    print("Intel GPU disabled.")

def enable_intel_gpu():
    """Enable the Intel GPU."""
    print("Enabling Intel GPU...")
    command = "echo 1 > /sys/bus/pci/rescan"
    execute_command(command)
    print("Intel GPU enabled.")

def set_power_mode(mode):
    """Set NVIDIA GPU power mode and system power profile."""
    if mode not in ["eco", "balanced", "performance"]:
        print("Invalid mode. Use 'eco', 'balanced', or 'performance'.")
        return

    print(f"Setting NVIDIA GPU power mode and system profile to {mode}...")

    # Set power profile using `powerprofilesctl`
    profile_cmd = f"powerprofilesctl set {mode}"
    try:
        execute_command(profile_cmd)
    except subprocess.CalledProcessError:
        print(f"Failed to set power profile to {mode}. Please ensure `power-profiles-daemon` is running and properly configured.")
        return

    # Apply GPU power mode settings
    try:
        if mode == "eco":
            execute_command("nvidia-smi --persistence-mode=1")
            execute_command("nvidia-smi --auto-boost-default=0")
        elif mode == "balanced":
            execute_command("nvidia-smi --persistence-mode=1")
            execute_command("nvidia-smi --auto-boost-default=1")
        elif mode == "performance":
            execute_command("nvidia-smi --persistence-mode=1")
            execute_command("nvidia-smi --auto-boost-default=1")
            execute_command("nvidia-settings -a [gpu:0]/GPUPerfModes=1")
    except subprocess.CalledProcessError as e:
        print(f"Error setting GPU power mode: {e}")

    print(f"NVIDIA GPU power mode and system profile set to {mode}.")

def check_status():
    """Check and display the current power modes."""
    print("Checking current power modes...")

    # Check NVIDIA GPU power mode
    try:
        gpu_persistence_mode = execute_command("nvidia-smi --query-gpu=persistence_mode --format=csv,noheader")
        gpu_auto_boost = execute_command("nvidia-smi --query-gpu=auto_boost --format=csv,noheader")
        gpu_perf_mode = execute_command("nvidia-settings -q [gpu:0]/GPUPerfModes")
        print("NVIDIA GPU Status:")
        print(f"Persistence Mode: {gpu_persistence_mode.strip()}")
        print(f"Auto Boost: {gpu_auto_boost.strip()}")
        print(f"Performance Mode: {gpu_perf_mode.strip()}")
    except Exception as e:
        print(f"Failed to retrieve NVIDIA GPU status: {e}")

    # Check system power profile
    try:
        system_profile = execute_command("powerprofilesctl list")
        print("System Power Profile:")
        print(system_profile.strip())
    except subprocess.CalledProcessError as e:
        print(f"Failed to retrieve system power profile: {e}")

def is_first_run():
    """Check if the script is being run for the first time."""
    grub_file = "/etc/default/grub"
    return not os.path.exists(grub_file) or "i915" not in open(grub_file).read()

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 gpu_control.py [enable|disable|eco|balanced|performance|status]")
        sys.exit(1)

    action = sys.argv[1].lower()

    if is_first_run():
        print("First-time setup detected.")
        update_grub()
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

if __name__ == "__main__":
    main()

