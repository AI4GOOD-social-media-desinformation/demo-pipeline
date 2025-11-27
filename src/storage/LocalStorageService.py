import os


# class StorageService:
#     def read_file(self, path: str) -> bytes | None: ...
#     def write_file(self, path: str, data: bytes) -> str: ...

class LocalFileSystemStorageService:
    """
    Implements the StorageService using the local file system.
    Paths are relative to the configured root_dir.
    """
    def __init__(self, root_dir: str):

        self.root_dir = os.path.abspath(root_dir)
        os.makedirs(self.root_dir, exist_ok=True)
        print(f"Local Storage initialized. Root Directory: {self.root_dir}")


    def read_file(self, path: str) -> bytes | None:
        """Reads a file's content as bytes from the local storage."""
        
        full_path = os.path.join(self.root_dir, path)
        try:
            with open(full_path, 'rb') as f:
                print(f"Reading file: {path}")
                return f.read()
            
        except FileNotFoundError:
            print(f"File not found: {path}")
            return None
        
        except Exception as e:
            print(f"Error reading file {path}: {e}")
            raise

    def write_file(self, path: str, data: bytes) -> str:
        """Writes bytes content to a file in the local storage."""
        full_path = os.path.join(self.root_dir, path)
        
        parent_dir = os.path.dirname(full_path)
        os.makedirs(parent_dir, exist_ok=True)
        
        try:
            with open(full_path, 'wb') as f:
                f.write(data)
            print(f"File written successfully: {path}")
            return path
        
        except Exception as e:
            print(f"Error writing file {path}: {e}")
            raise