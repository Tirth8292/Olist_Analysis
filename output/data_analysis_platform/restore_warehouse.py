import py7zr
from pathlib import Path
import shutil
import time

def main():
    warehouse_dir = Path("data/warehouse")
    backup_file = Path("data/warehouse_backup.7z")

    if not backup_file.exists():
        print(f"ERROR: Backup file not found: {backup_file}")
        return

    print("="*50)
    print("WARNING: Before proceeding, make sure all services are stopped!")
    print("(Stop the start_services.py process first by pressing Ctrl+C)")
    print("="*50)
    time.sleep(3)

    print(f"\nRestoring from {backup_file}...")

    # Delete existing warehouse if it exists
    if warehouse_dir.exists():
        try:
            print(f"Deleting existing warehouse directory: {warehouse_dir}")
            shutil.rmtree(warehouse_dir)
        except PermissionError:
            print("\nERROR: Cannot delete warehouse because files are in use!")
            print("Please stop all running services (port 8000, 8001, 8002) first!")
            return

    # Extract the backup
    print("Extracting backup...")
    try:
        with py7zr.SevenZipFile(backup_file, mode='r') as archive:
            archive.extractall(path="data/")
        print("✅ Restore complete!")
    except Exception as e:
        print(f"ERROR during extraction: {e}")
        return

if __name__ == "__main__":
    main()
