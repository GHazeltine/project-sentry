import os

class Janitor:
    """
    Module E: The Ghostbuster
    Responsibility: Recursively remove empty directories.
    Strategy: Aggressive Bottom-Up Traversal (Delete-as-you-go).
    """

    def __init__(self, dry_run=False):
        self.dry_run = dry_run

    def clean(self, target_path):
        """
        Executes the cleanup protocol.
        """
        print(f"\n👻 GHOSTBUSTER: Scanning {target_path}...")
        
        if not os.path.exists(target_path):
            print(f"❌ Error: Path not found: {target_path}")
            return {"deleted": 0, "errors": 1}

        deleted_count = 0
        error_count = 0

        # OS.WALK with topdown=False is the key.
        # It lets us visit the children (deepest folders) BEFORE the parents.
        for root, dirs, files in os.walk(target_path, topdown=False):
            for name in dirs:
                full_path = os.path.join(root, name)
                
                try:
                    # We simply try to delete every folder we encounter.
                    # os.rmdir ONLY works if the folder is empty.
                    # If it has files (or un-deleted children), it throws an error, which we catch.
                    
                    if not self.dry_run:
                        os.rmdir(full_path)
                        deleted_count += 1
                        # Visual feedback for massive cleans
                        if deleted_count % 100 == 0:
                            print(f"   ...dissolved {deleted_count} ghosts...", end='\r')
                    
                    else:
                        # In Dry Run, we just check if it LOOKS empty
                        if not os.listdir(full_path):
                            deleted_count += 1

                except OSError:
                    # This is normal! It means the folder wasn't empty.
                    # We just move on.
                    pass

        if deleted_count == 0:
            print("✅ No ghosts found (or Dry Run active).")
        else:
            print(f"✨ Ghostbuster finished. Removed {deleted_count} empty folders.")
            
        return {"deleted": deleted_count, "errors": error_count}
