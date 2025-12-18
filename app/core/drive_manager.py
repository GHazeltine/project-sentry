import subprocess
import json
import os
import getpass

class DriveManager:
    """
    Module A: The Gatekeeper
    Responsibility: Hardware detection, Health Checks, and Auto-Fixing locks.
    """
    
    def detect_drives(self):
        """
        Runs 'lsblk' to find connected storage devices.
        Returns a list of dictionaries containing drive info.
        """
        # We use JSON output (-J) for reliable parsing
        cmd = ["lsblk", "-J", "-o", "NAME,LABEL,SIZE,FSTYPE,MOUNTPOINT,UUID"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            print("❌ Error: Could not parse drive data.")
            return []

        drives = []
        blockdevices = data.get("blockdevices", [])

        # Recursive function to find partitions
        def find_partitions(devices):
            for dev in devices:
                # We only care about partitions with a Mountpoint or a Label
                if dev.get("mountpoint") or dev.get("label"):
                    # Filter out loop devices (Snaps) and the Boot partition
                    if "loop" not in dev["name"] and "/boot" not in str(dev.get("mountpoint")):
                        drives.append({
                            "name": dev["name"],
                            "label": dev.get("label") or "Unknown Label",
                            "size": dev["size"],
                            "fstype": dev.get("fstype"),
                            "mountpoint": dev.get("mountpoint"),
                            "uuid": dev.get("uuid")
                        })
                
                # Check children (sub-partitions)
                if "children" in dev:
                    find_partitions(dev["children"])

        find_partitions(blockdevices)
        return drives

    def display_drives(self, drives):
        print(f"\n{'ID':<5} {'LABEL':<25} {'SIZE':<10} {'TYPE':<10} {'MOUNTPOINT'}")
        print("-" * 80)
        for i, d in enumerate(drives):
            print(f"[{i+1}]   {d['label'][:24]:<25} {d['size']:<10} {d['fstype']:<10} {d['mountpoint']}")

    def health_check(self, drive):
        """
        Diagnoses the drive.
        Returns: 'OK', 'LOCKED' (Read-Only), 'PERMISSION_DENIED', or 'UNMOUNTED'
        """
        path = drive['mountpoint']
        
        if not path:
            return "UNMOUNTED"

        # Test 1: Write Access (File System Level)
        if not os.access(path, os.W_OK):
            return "LOCKED"

        # Test 2: Effective Permissions (Can we actually write a file?)
        test_file = os.path.join(path, ".sentry_test")
        try:
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
            return "OK"
        except PermissionError:
            return "PERMISSION_DENIED"
        except OSError:
            return "LOCKED"

    def unlock_drive(self, drive):
        """
        Attempts to force-mount Mac/Windows drives to RW mode.
        """
        fstype = drive['fstype']
        dev_path = f"/dev/{drive['name']}"
        mount_point = drive['mountpoint']
        
        print(f"🔧 Attempting Auto-Fix for {drive['label']} ({fstype})...")

        # FIX 1: Mac HFS+ Force Mount
        if "hfs" in fstype or "hfsplus" in fstype:
            print("   -> Applying HFS+ Force Protocol...")
            # Unmount first
            subprocess.run(["sudo", "umount", mount_point])
            # Remount with force,rw
            subprocess.run(["sudo", "mount", "-t", "hfsplus", "-o", "force,rw", dev_path, mount_point])
            
        # FIX 2: Windows NTFS Fix (Simple Remount)
        elif "ntfs" in fstype:
            print("   -> Applying NTFS Remount...")
            subprocess.run(["sudo", "mount", "-o", "remount,rw", mount_point])
        
        else:
            print(f"   -> Unknown filesystem '{fstype}'. Trying generic remount...")
            subprocess.run(["sudo", "mount", "-o", "remount,rw", mount_point])

    def claim_ownership(self, drive):
        """
        Runs chown to give the current user ownership.
        """
        user = getpass.getuser()
        print(f"🔧 Seizing ownership for user: {user}...")
        cmd = ["sudo", "chown", "-R", f"{user}:{user}", drive['mountpoint']]
        subprocess.run(cmd)
        print("   -> Ownership claim command sent.")
