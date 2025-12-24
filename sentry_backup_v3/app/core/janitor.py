import os

class Janitor:
    """
    The Ghostbuster.
    Responsible for cleaning up empty directory structures 
    left behind after the Reaper deletes files.
    """
    
    def cleanup_ghosts(self, target_paths):
        removed_count = 0
        print(f"[Janitor] Starting ghost bust on: {target_paths}")
        
        for root_path in target_paths:
            if not os.path.exists(root_path):
                continue
                
            # Walk BOTTOM-UP (topdown=False)
            # This deletes nested empty folders (A/B/C -> deletes C, then B, then A)
            for dirpath, dirnames, filenames in os.walk(root_path, topdown=False):
                try:
                    if not os.listdir(dirpath):
                        os.rmdir(dirpath)
                        removed_count += 1
                except Exception as e:
                    print(f"[Janitor] Failed to remove {dirpath}: {e}")
                    
        return removed_count
