import argparse
import multiprocessing
import subprocess
import sys
import time
from pathlib import Path

SERVERS = {
    "availability": {
        "file": "availability_server.py",
        "port": 8082,
        "description": "Manages photographer availability and bookings",
        "required": True,
        "emoji": "availability"
    },
    "weather": {
        "file": "weather_server.py",
        "port": 8083,
        "description": "Weather forecasts for outdoor shoot planning",
        "required": False,
        "emoji": "weather"
    },
    "search": {
        "file": "search_server.py",
        "port": 8084,
        "description": "Web search for photography research and trends",
        "required": False,
        "emoji": "search"
    }
}

def run_server(server_name: str):
    if server_name not in SERVERS:
        print(f"Unknown server: {server_name}")
        return
    
    server_config = SERVERS[server_name]
    server_file = Path(__file__).parent / server_config["file"]
    
    if not server_file.exists():
        print(f"Server file not found: {server_file}")
        return
    
    print(f"Starting {server_name.upper()} MCP Server")
    print(f"   Port: {server_config['port']}")
    print(f"   Description: {server_config['description']}")
    
    try:
        subprocess.run([sys.executable, str(server_file)], check=True)
    except KeyboardInterrupt:
        print(f"\nStopped {server_name} server")
    except Exception as e:
        print(f"Error running {server_name} server: {e}")

def run_all_servers():
    print("\nMCP SERVER MANAGER - Starting All Services")
    print("=" * 60)
    
    for name, config in SERVERS.items():
        status = "REQUIRED" if config["required"] else "OPTIONAL"
        print(f"  {name.upper():<12} Port {config['port']} - {status}")
    
    print("=" * 60)
    print()
    
    processes = []
    
    for server_name in SERVERS.keys():
        try:
            p = multiprocessing.Process(target=run_server, args=(server_name,))
            p.start()
            processes.append((server_name, p))
            print(f"Started {server_name} server")
            time.sleep(0.5)
        except Exception as e:
            print(f"Failed to start {server_name}: {e}")
    
    if not processes:
        print("No servers started")
        return
    
    print(f"\nStarted {len(processes)} MCP servers!")
    print("Press Ctrl+C to stop all servers\n")
    
    try:
        for server_name, process in processes:
            process.join()
    except KeyboardInterrupt:
        print("\n🛑 Stopping all servers...")
        for server_name, process in processes:
            print(f"   Stopping {server_name}...")
            process.terminate()
            process.join(timeout=5)
            if process.is_alive():
                process.kill()
        print("All servers stopped")

def health_check():
    import httpx
    import asyncio
    
    async def check_server(name: str, port: int):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"http://localhost:{port}/health", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    return f"OK {name.upper():<12} Port {port} - {data.get('status', 'unknown')}"
                else:
                    return f"ERROR {name.upper():<12} Port {port} - HTTP {response.status_code}"
        except Exception as e:
            return f"ERROR {name.upper():<12} Port {port} - {str(e)[:50]}"
    
    async def check_all():
        print("\nMCP SERVER HEALTH CHECK")
        print("=" * 50)
        
        tasks = []
        for name, config in SERVERS.items():
            tasks.append(check_server(name, config["port"]))
        
        results = await asyncio.gather(*tasks)
        for result in results:
            print(result)
        
        print("=" * 50)
    
    asyncio.run(check_all())

def list_servers():
    print("\nAVAILABLE MCP SERVERS")
    print("=" * 60)
    
    for name, config in SERVERS.items():
        status = "REQUIRED" if config["required"] else "OPTIONAL"
        print(f"  {name}")
        print(f"    Port: {config['port']}")
        print(f"    File: {config['file']}")
        print(f"    Status: {status}")
        print(f"    Description: {config['description']}")
        print()

def main():
    parser = argparse.ArgumentParser(description="MCP Server Manager")
    parser.add_argument(
        "action",
        choices=["start", "health", "list"],
        help="Action to perform"
    )
    parser.add_argument(
        "--server",
        choices=list(SERVERS.keys()) + ["all"],
        default="all",
        help="Which server to start (only for 'start' action)"
    )
    
    args = parser.parse_args()
    
    if args.action == "start":
        if args.server == "all":
            run_all_servers()
        else:
            run_server(args.server)
    elif args.action == "health":
        health_check()
    elif args.action == "list":
        list_servers()

if __name__ == "__main__":
    main()