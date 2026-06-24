#!/usr/bin/env python3
print("🎯 Test worker started successfully!")
print("Python is working!")

import sys
print(f"Python version: {sys.version}")

import os
print(f"Working directory: {os.getcwd()}")
print(f"Files in directory: {os.listdir('.')}")

try:
    print("Testing app directory...")
    if os.path.exists('app'):
        print(f"App directory exists: {os.listdir('app')}")
    else:
        print("❌ App directory not found!")

    print("Testing imports...")
    sys.path.append('app')

    import services
    print("✅ Services module imported")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    print(f"❌ Traceback: {traceback.format_exc()}")

print("🎉 Test completed!")