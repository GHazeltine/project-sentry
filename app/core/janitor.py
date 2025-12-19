import os

class Janitor:
    def __init__(self, target_root: str):
        self.target_root = target_root

    def clean_empty_folders(self):
        empty_dirs = []
        for root, dirs, files in os.walk(self.target_root, topdown=False):
            for name in dirs:
                full_path = os.path.join(root, name)
                try:
                    if not os.listdir(full_path):
                        os.rmdir(full_path)
                        empty_dirs.append(full_path)
                except: pass
        return empty_dirs
