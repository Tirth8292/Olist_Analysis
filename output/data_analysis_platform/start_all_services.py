import subprocess
import sys
import time

def run_command(cmd, cwd=None):
    return subprocess.Popen(cmd, cwd=cwd, shell=True)

def main():
    print("🚀 Starting Olist Analytics Platform Services...")
    
    # Change to project root
    project_dir = r"c:\Users\tirth\Documents\Codex\2026-06-23\hi-2\outputs\olist_analytics_platform"
    
    # Start main API (port 8000)
    print("Starting Main Marketplace Intelligence API on port 8000...")
    main_api = run_command(
        "uvicorn src.olist_platform.api.main:app --reload --port 8000",
        cwd=project_dir
    )
    
    # Wait a bit
    time.sleep(2)
    
    # Start ingestor (port 8001)
    print("Starting Live Ingestor Portal on port 8001...")
    ingestor = run_command(
        "uvicorn src.olist_platform.api.ingestor:app --reload --port 8001",
        cwd=project_dir
    )
    
    time.sleep(2)
    
    # Start dashboard (port 8002)
    print("Starting Live Web Dashboard on port 8002...")
    dashboard = run_command(
        "uvicorn src.olist_platform.api.dashboard_api:app --reload --port 8002",
        cwd=project_dir
    )
    
    print("\n✅ All services started successfully!")
    print("📊 Main API:          http://127.0.0.1:8000")
    print("📝 Ingestor Portal:   http://127.0.0.1:8001")
    print("🎨 Web Dashboard:     http://127.0.0.1:8002")
    print("\nPress Ctrl+C to stop all services...")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping all services...")
        main_api.terminate()
        ingestor.terminate()
        dashboard.terminate()
        print("✅ All services stopped.")

if __name__ == "__main__":
    main()
