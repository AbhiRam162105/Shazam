#!/usr/bin/env python3
"""
Check system requirements and setup for Shazam.
"""

import sys
import subprocess
from pathlib import Path

def check_redis():
    """Check if Redis is available."""
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        print("✅ Redis is running and accessible")
        return True
    except Exception as e:
        print(f"❌ Redis not available: {e}")
        print("   Install Redis: brew install redis (macOS) or apt install redis-server (Ubuntu)")
        print("   Start Redis: redis-server")
        return False

def check_dependencies():
    """Check if all Python dependencies are installed."""
    required_packages = [
        'numpy', 'scipy', 'librosa','redis', 'flask', 'sounddevice', 'pywt'
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package}")
            missing.append(package)
    
    if missing:
        print(f"\nMissing packages: {missing}")
        print("Install with: pip install -r requirements.txt")
        return False
    
    return True

def setup_directories():
    """Create necessary directories."""
    dirs = ['data', 'temp']
    
    for dirname in dirs:
        path = Path(dirname)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            print(f"✅ Created directory: {dirname}")
        else:
            print(f"✅ Directory exists: {dirname}")

def main():
    """Run system checks."""
    print("🔍 SHAZAM SYSTEM CHECK")
    print("=" * 40)
    
    print("\n1. Checking Python dependencies...")
    deps_ok = check_dependencies()
    
    print("\n2. Checking Redis availability...")
    redis_ok = check_redis()
    
    print("\n3. Setting up directories...")
    setup_directories()
    
    print("\n" + "=" * 40)
    
    if deps_ok and redis_ok:
        print("✅ System ready for Shazam!")
        print("\nQuick start:")
        print("1. Run demo: python demo.py")
        print("2. Build database: python main.py build /path/to/music")
        print("3. Identify song: python main.py identify song.wav")
        print("4. Start API: python main.py api")
    else:
        print("❌ System not ready - please fix the issues above")
        
        if not redis_ok:
            print("\nNote: Shazam can run without Redis, but will use in-memory storage")
            print("This is fine for testing but not recommended for production")

if __name__ == "__main__":
    main()
