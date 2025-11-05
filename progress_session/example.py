#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# example.py
# Comprehensive examples for ProgressSession usage

import logging
import json
from progress_session import ProgressSession

# Setup logging untuk melihat detail retry
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def example_1_basic_usage():
    """Example 1: Basic GET request dengan retry"""
    print("\n" + "="*70)
    print("EXAMPLE 1: Basic GET Request dengan Automatic Retry")
    print("="*70)
    
    session = ProgressSession()
    
    try:
        response = session.get(
            "https://httpbin.org/get",
            timeout=10,
            max_try=3
        )
        print(f"✓ Success! Status Code: {response.status_code}")
        print(f"✓ Response Headers: {dict(list(response.headers.items())[:3])}")
        
    except Exception as e:
        print(f"✗ Request failed: {type(e).__name__}: {e}")
    finally:
        session.close()


def example_2_context_manager():
    """Example 2: Menggunakan context manager (recommended)"""
    print("\n" + "="*70)
    print("EXAMPLE 2: Context Manager (Best Practice)")
    print("="*70)
    
    with ProgressSession(base_url="https://httpbin.org") as session:
        try:
            # Request 1: GET
            response = session.get("/get", timeout=10)
            print(f"✓ GET request: {response.status_code}")
            
            # Request 2: POST with JSON
            response = session.post(
                "/post",
                json={"name": "John", "age": 30},
                timeout=10
            )
            print(f"✓ POST request: {response.status_code}")
            
            # Request 3: Headers
            response = session.get(
                "/headers",
                headers={"X-Custom-Header": "MyValue"},
                timeout=10
            )
            data = response.json()
            print(f"✓ Custom header sent: {data['headers'].get('X-Custom-Header')}")
            
        except Exception as e:
            print(f"✗ Request failed: {e}")


def example_3_retry_mechanism():
    """Example 3: Testing retry mechanism dengan endpoint yang fail"""
    print("\n" + "="*70)
    print("EXAMPLE 3: Retry Mechanism dengan Failing Endpoint")
    print("="*70)
    
    with ProgressSession() as session:
        try:
            # httpbin.org/status/500 akan selalu return 500
            response = session.get(
                "https://httpbin.org/status/500",
                timeout=5,
                max_try=3,
                retry_delay=0.5,
                exponential_backoff=True
            )
            print(f"✓ Unexpected success: {response.status_code}")
            
        except Exception as e:
            print(f"✓ Expected failure after retries: {type(e).__name__}")
            print(f"  Error: {str(e)[:100]}")


def example_4_url_masking():
    """Example 4: URL masking untuk security"""
    print("\n" + "="*70)
    print("EXAMPLE 4: URL Masking untuk Security/Privacy")
    print("="*70)
    
    # Dengan URL masking (default)
    print("\n[A] Dengan URL Masking (show_url=False):")
    with ProgressSession(show_url=False) as session:
        try:
            response = session.get(
                "https://api.github.com/invalid-endpoint-12345",
                timeout=5,
                max_try=1
            )
        except Exception as e:
            print(f"   Error message (URL should be masked): {str(e)[:80]}...")
    
    # Tanpa URL masking
    print("\n[B] Tanpa URL Masking (show_url=True):")
    with ProgressSession(show_url=True) as session:
        try:
            response = session.get(
                "https://api.github.com/invalid-endpoint-12345",
                timeout=5,
                max_try=1
            )
        except Exception as e:
            print(f"   Error message (URL visible): {str(e)[:80]}...")


def example_5_exponential_backoff():
    """Example 5: Exponential backoff vs linear retry"""
    print("\n" + "="*70)
    print("EXAMPLE 5: Exponential Backoff vs Linear Retry")
    print("="*70)
    
    import time
    
    # Linear backoff
    print("\n[A] Linear Backoff (1s, 1s, 1s):")
    with ProgressSession() as session:
        start = time.time()
        try:
            response = session.get(
                "https://httpbin.org/status/503",
                timeout=3,
                max_try=3,
                retry_delay=1.0,
                exponential_backoff=False
            )
        except Exception:
            duration = time.time() - start
            print(f"   Total time: {duration:.1f}s")
    
    # Exponential backoff
    print("\n[B] Exponential Backoff (1s, 2s, 4s):")
    with ProgressSession() as session:
        start = time.time()
        try:
            response = session.get(
                "https://httpbin.org/status/503",
                timeout=3,
                max_try=3,
                retry_delay=1.0,
                exponential_backoff=True
            )
        except Exception:
            duration = time.time() - start
            print(f"   Total time: {duration:.1f}s")


def example_6_different_http_methods():
    """Example 6: Berbagai HTTP methods"""
    print("\n" + "="*70)
    print("EXAMPLE 6: Different HTTP Methods")
    print("="*70)
    
    with ProgressSession(base_url="https://httpbin.org") as session:
        
        # GET
        print("\n[GET]")
        response = session.get("/get", params={"key": "value"})
        print(f"  ✓ Status: {response.status_code}, URL: {response.url}")
        
        # POST with JSON
        print("\n[POST - JSON]")
        response = session.post(
            "/post",
            json={"username": "testuser", "password": "secret123"}
        )
        print(f"  ✓ Status: {response.status_code}")
        
        # POST with form data
        print("\n[POST - Form Data]")
        response = session.post(
            "/post",
            data={"field1": "value1", "field2": "value2"}
        )
        print(f"  ✓ Status: {response.status_code}")
        
        # PUT
        print("\n[PUT]")
        response = session.put(
            "/put",
            json={"id": 123, "name": "Updated Name"}
        )
        print(f"  ✓ Status: {response.status_code}")
        
        # DELETE
        print("\n[DELETE]")
        response = session.delete("/delete")
        print(f"  ✓ Status: {response.status_code}")
        
        # PATCH
        print("\n[PATCH]")
        response = session.patch(
            "/patch",
            json={"field": "new_value"}
        )
        print(f"  ✓ Status: {response.status_code}")


def example_7_authentication():
    """Example 7: Authentication examples"""
    print("\n" + "="*70)
    print("EXAMPLE 7: Authentication")
    print("="*70)
    
    # Basic Auth
    print("\n[A] Basic Authentication:")
    with ProgressSession() as session:
        response = session.get(
            "https://httpbin.org/basic-auth/user/passwd",
            auth=("user", "passwd")
        )
        print(f"  ✓ Status: {response.status_code}")
        print(f"  ✓ Authenticated: {response.json().get('authenticated')}")
    
    # Bearer Token
    print("\n[B] Bearer Token:")
    with ProgressSession() as session:
        response = session.get(
            "https://httpbin.org/bearer",
            headers={"Authorization": "Bearer my-secret-token-12345"}
        )
        print(f"  ✓ Status: {response.status_code}")
        print(f"  ✓ Token received: {response.json().get('authenticated')}")
    
    # Session with persistent headers
    print("\n[C] Persistent Headers (API Key):")
    with ProgressSession() as session:
        session.headers.update({"X-API-Key": "my-api-key-67890"})
        
        response = session.get("https://httpbin.org/headers")
        headers_received = response.json()['headers']
        print(f"  ✓ API Key sent: {headers_received.get('X-Api-Key')}")


def example_8_file_upload():
    """Example 8: File upload"""
    print("\n" + "="*70)
    print("EXAMPLE 8: File Upload")
    print("="*70)
    
    # Create temporary file
    import tempfile
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("This is a test file content\nLine 2\nLine 3")
        temp_file_path = f.name
    
    try:
        with ProgressSession() as session:
            with open(temp_file_path, 'rb') as f:
                files = {'file': ('test.txt', f, 'text/plain')}
                response = session.post(
                    "https://httpbin.org/post",
                    files=files
                )
                
                print(f"  ✓ Status: {response.status_code}")
                print(f"  ✓ File uploaded: {response.json()['files']}")
    finally:
        import os
        os.unlink(temp_file_path)


def example_9_custom_timeout():
    """Example 9: Custom timeout dan error handling"""
    print("\n" + "="*70)
    print("EXAMPLE 9: Custom Timeout & Error Handling")
    print("="*70)
    
    # Short timeout (akan timeout)
    print("\n[A] Short Timeout (akan gagal):")
    with ProgressSession() as session:
        try:
            response = session.get(
                "https://httpbin.org/delay/5",  # Server delay 5 detik
                timeout=2,  # Timeout 2 detik
                max_try=2,
                retry_delay=0.5
            )
        except Exception as e:
            print(f"  ✓ Expected timeout: {type(e).__name__}")
    
    # Proper timeout
    print("\n[B] Proper Timeout (akan berhasil):")
    with ProgressSession() as session:
        response = session.get(
            "https://httpbin.org/delay/2",  # Server delay 2 detik
            timeout=5  # Timeout 5 detik
        )
        print(f"  ✓ Status: {response.status_code}")


def example_10_real_world_api():
    """Example 10: Real-world API usage"""
    print("\n" + "="*70)
    print("EXAMPLE 10: Real-World API Usage (GitHub API)")
    print("="*70)
    
    with ProgressSession(
        base_url="https://api.github.com",
        default_text="Fetching GitHub data"
    ) as session:
        
        # Set User-Agent (GitHub requires it)
        session.headers.update({
            "User-Agent": "ProgressSession-Example/1.0",
            "Accept": "application/vnd.github.v3+json"
        })
        
        try:
            # Get Python repository info
            print("\n[A] Repository Information:")
            response = session.get(
                "/repos/python/cpython",
                timeout=10
            )
            repo = response.json()
            print(f"  ✓ Name: {repo['name']}")
            print(f"  ✓ Stars: {repo['stargazers_count']:,}")
            print(f"  ✓ Language: {repo['language']}")
            print(f"  ✓ Description: {repo['description'][:60]}...")
            
            # Get recent commits
            print("\n[B] Recent Commits:")
            response = session.get(
                "/repos/python/cpython/commits",
                params={"per_page": 3},
                timeout=10
            )
            commits = response.json()
            for i, commit in enumerate(commits[:3], 1):
                msg = commit['commit']['message'].split('\n')[0]
                author = commit['commit']['author']['name']
                print(f"  {i}. {msg[:50]}... by {author}")
                
        except Exception as e:
            print(f"  ✗ API request failed: {e}")


def example_11_rate_limiting():
    """Example 11: Handling rate limits"""
    print("\n" + "="*70)
    print("EXAMPLE 11: Rate Limiting (Demonstrasi)")
    print("="*70)
    
    with ProgressSession() as session:
        print("\nMelakukan 5 request berturut-turut:")
        
        for i in range(1, 6):
            try:
                response = session.get(
                    f"https://httpbin.org/get?request={i}",
                    timeout=5,
                    max_try=1
                )
                print(f"  Request {i}: ✓ {response.status_code}")
                
                # Check rate limit headers (jika ada)
                if 'X-RateLimit-Remaining' in response.headers:
                    remaining = response.headers['X-RateLimit-Remaining']
                    print(f"    Rate limit remaining: {remaining}")
                    
            except Exception as e:
                print(f"  Request {i}: ✗ {type(e).__name__}")


def example_12_error_recovery():
    """Example 12: Error recovery strategies"""
    print("\n" + "="*70)
    print("EXAMPLE 12: Error Recovery Strategies")
    print("="*70)
    
    endpoints = [
        ("Working endpoint", "https://httpbin.org/get"),
        ("404 Error", "https://httpbin.org/status/404"),
        ("500 Error", "https://httpbin.org/status/500"),
        ("Timeout endpoint", "https://httpbin.org/delay/10")
    ]
    
    with ProgressSession() as session:
        results = []
        
        for name, url in endpoints:
            print(f"\n[{name}]")
            try:
                response = session.get(
                    url,
                    timeout=3,
                    max_try=2,
                    retry_delay=0.5
                )
                results.append((name, "SUCCESS", response.status_code))
                print(f"  ✓ Success: {response.status_code}")
                
            except Exception as e:
                results.append((name, "FAILED", type(e).__name__))
                print(f"  ✗ Failed: {type(e).__name__}")
        
        # Summary
        print("\n" + "-"*70)
        print("SUMMARY:")
        for name, status, detail in results:
            status_symbol = "✓" if status == "SUCCESS" else "✗"
            print(f"  {status_symbol} {name}: {detail}")


def main():
    """Run all examples"""
    print("\n" + "="*70)
    print("PROGRESS SESSION - COMPREHENSIVE EXAMPLES")
    print("="*70)
    
    examples = [
        ("Basic Usage", example_1_basic_usage),
        ("Context Manager", example_2_context_manager),
        ("Retry Mechanism", example_3_retry_mechanism),
        ("URL Masking", example_4_url_masking),
        ("Exponential Backoff", example_5_exponential_backoff),
        ("HTTP Methods", example_6_different_http_methods),
        ("Authentication", example_7_authentication),
        ("File Upload", example_8_file_upload),
        ("Timeout Handling", example_9_custom_timeout),
        ("Real-World API", example_10_real_world_api),
        ("Rate Limiting", example_11_rate_limiting),
        ("Error Recovery", example_12_error_recovery),
    ]
    
    print("\nAvailable examples:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"  {i}. {name}")
    
    print("\nRunning all examples...")
    
    for name, func in examples:
        try:
            func()
        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupted by user")
            break
        except Exception as e:
            print(f"\n✗ Example '{name}' crashed: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*70)
    print("ALL EXAMPLES COMPLETED!")
    print("="*70)
    print("\nTips:")
    print("  • Set SHOW_URL=1 to see full URLs in errors")
    print("  • Set TRACEBACK=1 to see full tracebacks")
    print("  • Use exponential_backoff=True for better retry strategy")
    print("  • Always use context manager (with statement)")
    print("  • Adjust max_try and retry_delay based on your needs")


if __name__ == "__main__":
    main()