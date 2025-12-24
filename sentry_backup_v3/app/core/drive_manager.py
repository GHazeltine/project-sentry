import subprocess
import json
import os
import shutil

class DriveManager:
    """
    Handles Physical Drives and Network Mounts.
    """
    
    def detect_drives(self):
        cmd = ["lsblk", "-J", "-o", "NAME,LABEL,SIZE,FSTYPE,MOUNTPOINT"]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            data = json.loads(result.stdout)
            drives = []
            for dev in data.get("blockdevices", []):
                if "children" in dev:
                    for child in dev["children"]:
                        if child.get("mountpoint"): drives.append(self._format(child))
                elif dev.get("mountpoint"):
                    drives.append(self._format(dev))
            return drives
        except Exception:
            return []

    def _format(self, dev):
        return {
            "label": dev.get("label") or dev.get("name"),
            "mountpoint": dev.get("mountpoint"),
            "size": dev.get("size"),
            "fstype": dev.get("fstype")
        }

    def mount_smb(self, remote_path, user, password):
        """
        Mounts a network share to /mnt/sentry/<Name>.
        Required for the Web UI to see it.
        """
        # Clean up the path to make a safe folder name
        clean_name = remote_path.replace("/", "_").replace("\\", "_").replace(":", "").strip("_")
        local_mount = f"/mnt/sentry/NET_{clean_name}"
        
        if not os.path.exists(local_mount):
            os.makedirs(local_mount)

        # Check if already mounted
        if os.path.ismount(local_mount):
            return {"success": True, "path": local_mount, "message": "Already mounted"}

        cmd = [
            "mount", "-t", "cifs", remote_path, local_mount,
            "-o", f"username={user},password={password},rw,iocharset=utf8"
        ]
        
        try:
            subprocess.run(cmd, check=True, stderr=subprocess.PIPE, text=True)
            return {"success": True, "path": local_mount, "message": "Mounted successfully"}
        except subprocess.CalledProcessError as e:
            return {"success": False, "message": f"Mount Failed: {e.stderr}"}
