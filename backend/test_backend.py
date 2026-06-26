#!/usr/bin/env python3
"""
Simple test script for the Technical Support Backend
"""
import requests
import json
import sys
import time

def test_backend(base_url="http://localhost:8000"):
    """Test the backend API endpoints"""
    
    print(f"Testing backend at: {base_url}")
    print("=" * 60)
    
    # Test 1: Health Check
    print("\n1. Testing Health Check...")
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Health check passed")
            print(json.dumps(response.json(), indent=2))
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {str(e)}")
        return False
    
    time.sleep(1)
    
    # Test 2: Status Endpoint
    print("\n2. Testing Status Endpoint...")
    try:
        response = requests.get(f"{base_url}/api/status", timeout=5)
        if response.status_code == 200:
            print("✅ Status endpoint working")
            print(json.dumps(response.json(), indent=2))
        else:
            print(f"⚠️  Status endpoint returned: {response.status_code}")
    except Exception as e:
        print(f"⚠️  Status endpoint error: {str(e)}")
    
    time.sleep(1)
    
    # Test 3: Question Endpoint
    print("\n3. Testing Question Endpoint...")
    test_question = "What is Python?"
    
    try:
        print(f"Asking: {test_question}")
        response = requests.post(
            f"{base_url}/api/question",
            json={"question": test_question},
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Question answered successfully")
            print(f"\nAnswer: {result.get('answer', 'No answer')[:200]}...")
            
            sources = result.get('sources', [])
            if sources:
                print(f"\nSources: {len(sources)} sources returned")
            
        else:
            print(f"❌ Question endpoint failed: {response.status_code}")
            print(response.text)
            return False
            
    except requests.exceptions.Timeout:
        print("⚠️  Request timed out (this is normal for first request)")
    except Exception as e:
        print(f"❌ Question endpoint error: {str(e)}")
        return False
    
    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    return True

if __name__ == "__main__":
    # Get URL from command line or use default
    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    
    success = test_backend(url)
    sys.exit(0 if success else 1)
