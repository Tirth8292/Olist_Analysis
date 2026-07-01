import py7zr
from pathlib import Path

def main():
    warehouse_dir = Path("data/warehouse")
    output_file = Path("data/warehouse_backup.7z")

    print(f"Compressing {warehouse_dir} to {output_file}...")

    # Use py7zr to compress the directory
    with py7zr.SevenZipFile(output_file, mode='w') as archive:
        archive.writeall(warehouse_dir, arcname="warehouse")

    print(f"Compression complete! File size: {output_file.stat().st_size / (1024*1024):.2f} MB")

if __name__ == "__main__":
    main()
