import subprocess
import time
import sys

def main():
    print("Starting Olist Analytics Services...")
    print("=" * 50)

    # Change to project directory
    import os
    project_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_dir)

    # Define commands with fixed ports
    commands = [
        ("Main API (8000)", ["python", "-m", "uvicorn", "src.olist_platform.api.main:app", "--host", "127.0.0.1", "--port", "8000"]),
        ("Ingestor Portal (8001)", ["python", "-m", "uvicorn", "src.olist_platform.api.ingestor:app", "--host", "127.0.0.1", "--port", "8001"]),
        ("Live Dashboard (8002)", ["python", "-m", "uvicorn", "src.olist_platform.api.dashboard_api:app", "--host", "127.0.0.1", "--port", "8002"])
    ]

    processes = []

    try:
        for name, cmd in commands:
            print(f"Starting {name}...")
            proc = subprocess.Popen(cmd)
            processes.append((name, proc))
            time.sleep(2)

        print("\n" + "=" * 50)
        print("All services are running!")
        print(f"Main API:        http://127.0.0.1:8000")
        print(f"Ingestor Portal: http://127.0.0.1:8001")
        print(f"Live Dashboard:  http://127.0.0.1:8002")
        print("\nPress Ctrl+C to stop all services.")
        print("=" * 50)

        # Keep script running
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nStopping all services...")
        for name, proc in processes:
            print(f"Stopping {name}...")
            proc.terminate()
        time.sleep(2)
        for name, proc in processes:
            if proc.poll() is None:
                proc.kill()
        print("All services stopped.")

if __name__ == "__main__":
    main()
