# Intel GPU Disabler

## Overview
This script is designed for users with Optimus laptops who want to use only their dedicated GPU (e.g., NVIDIA) and disable the integrated Intel GPU. This can help resolve issues such as screen tearing, limited refresh rates (e.g., capping at 60Hz), and problems with Variable Refresh Rate (VRR) technologies like FreeSync or G-Sync on external displays.

The script modifies system configurations to disable the Intel GPU entirely by updating the GRUB configuration and setting up a systemd service. It has been tested on KDE using Wayland.

## Requirements
- Python: Ensure Python 3 is installed on your system.
- Root Privileges: The script requires root access to modify system files and create systemd services.
- GRUB and Systemd: The script assumes you are using GRUB as your bootloader and systemd for managing services.

## Setup Instructions
1. Download the Script
Save the script to a file named `main.py` or another name of your choice (you can also clone the project):

```bash
wget https://example.com/gpu_control.py
```

2. Make the Script Executable

Open a terminal and run:
```bash
chmod +x main.py
```

3. Run the Script
Execute the script with superuser privileges to enable or disable the Intel GPU:

To Disable the Intel GPU:

```bash
sudo ./main.py disable
```

To Enable the Intel GPU:
```bash
sudo ./main.py enable
```

4. Reboot Your System
After running the script, reboot your system to apply the changes:

```bash
sudo reboot
```

## What the Script Does
- Updates GRUB Configuration: Adds parameters to the GRUB configuration to blacklist the Intel GPU driver and enable NVIDIA modesetting.
- Creates Systemd Service: Sets up a systemd service to disable the Intel GPU by modifying the PCI device settings.
- Toggles GPU: Allows you to enable or disable the Intel GPU on demand.

## Detailed Steps Performed by the Script
1. GRUB Configuration Update:

- Appends the following parameters to the GRUB configuration to prevent loading the Intel GPU driver:

```bash
GRUB_CMDLINE_LINUX="rd.driver.blacklist=i915 modprobe.blacklist=i915 nvidia-drm.modeset=1"
```

- Updates the GRUB configuration file:
```bash
sudo grub2-mkconfig -o /boot/grub2/grub.cfg
sudo grub2-mkconfig -o /boot/efi/EFI/fedora/grub.cfg
```

2. Systemd Service Creation:

Creates a systemd service to disable the Intel GPU by removing its PCI device:

```bash
[Unit]
Description=Disable Intel GPU

[Service]
Type=oneshot
ExecStart=/usr/bin/bash -c 'echo 1 > /sys/bus/pci/devices/0000:00:02.0/remove'

[Install]
WantedBy=multi-user.target
```

3. Enables and reloads the systemd configuration:
```bash
sudo systemctl daemon-reload
sudo systemctl enable disable-intel-gpu.service
```

## Warnings
- Backup: Always back up important data before modifying system configurations.
- GRUB Backup: The script backs up the GRUB configuration file before making changes. If you encounter issues, you can restore the backup.
- PCI Address: Ensure that 0000:00:02.0 is the correct PCI address for your Intel GPU. You can verify this using the lspci command:

```bash
lspci | grep VGA
```

- Testing: The script has been tested on KDE with Wayland. If you use a different desktop environment or display server, results may vary.

## Troubleshooting
- System Does Not Boot: If you experience boot issues after running the script, you can revert changes by restoring the backed-up GRUB file:

```bash
sudo cp /etc/default/grub.bak /etc/default/grub
sudo grub2-mkconfig -o /boot/grub2/grub.cfg
sudo grub2-mkconfig -o /boot/efi/EFI/fedora/grub.cfg
```

- Intel GPU Still Active: Check the status of the Intel GPU driver and verify that the PCI address is correct. Ensure the systemd service is enabled and running.

# License
This script is provided as-is. Use it at your own risk. No warranties or guarantees are provided.
