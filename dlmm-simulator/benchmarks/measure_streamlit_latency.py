#!/usr/bin/env python3
"""
Simple latency measurement for Streamlit app to API communication.
Simulates real user experience by measuring end-to-end latency.
"""

import time
import requests
import statistics
from typing import List, Dict
import json

def measure_streamlit_latency(api_url: str = "http://localhost:8000", iterations: int = 50):
    """Measure latency from Streamlit app perspective"""
    
    print("🎯 Streamlit App Latency Measurement")
    print("=" * 50)
    print(f"API URL: {api_url}")
    print(f"Iterations: {iterations}")
    print()
    
    # Test scenarios that users might perform
    test_scenarios = [
        {
            "name": "Quick BTC Quote (1 BTC)",
            "token_in": "BTC",
            "token_out": "USDC", 
            "amount_in": 1.0
        },
        {
            "name": "Medium BTC Quote (100 BTC)",
            "token_in": "BTC",
            "token_out": "USDC",
            "amount_in": 100.0
        },
        {
            "name": "Large BTC Quote (1000 BTC)", 
            "token_in": "BTC",
            "token_out": "USDC",
            "amount_in": 1000.0
        },
        {
            "name": "SOL Quote (1000 SOL)",
            "token_in": "SOL",
            "token_out": "USDC", 
            "amount_in": 1000.0
        }
    ]
    
    results = {}
    
    for scenario in test_scenarios:
        print(f"📊 Testing: {scenario['name']}")
        
        latencies = []
        successful_requests = 0
        
        for i in range(iterations):
            start_time = time.perf_counter()
            
            try:
                response = requests.post(
                    f"{api_url}/quote",
                    json={
                        "token_in": scenario["token_in"],
                        "token_out": scenario["token_out"],
                        "amount_in": scenario["amount_in"]
                    },
                    timeout=5
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success'):
                        successful_requests += 1
                        latency_ms = (time.perf_counter() - start_time) * 1000
                        latencies.append(latency_ms)
                        
                        # Show first result details
                        if successful_requests == 1:
                            print(f"  ✅ First successful quote: {data.get('amount_out', 0):.2f} {scenario['token_out']}")
                            print(f"  📈 Price impact: {data.get('price_impact', 0):.4f}%")
                            print(f"  🛣️  Route steps: {len(data.get('steps', []))}")
                
            except Exception as e:
                print(f"  ❌ Error in iteration {i}: {e}")
        
        if latencies:
            latencies.sort()
            
            results[scenario["name"]] = {
                "avg_latency_ms": statistics.mean(latencies),
                "min_latency_ms": min(latencies),
                "max_latency_ms": max(latencies),
                "p50_latency_ms": latencies[len(latencies)//2],
                "p95_latency_ms": latencies[int(len(latencies) * 0.95)],
                "p99_latency_ms": latencies[int(len(latencies) * 0.99)],
                "success_rate": successful_requests / iterations,
                "throughput_rps": 1000 / statistics.mean(latencies)
            }
            
            print(f"  📊 Results:")
            print(f"    Average: {statistics.mean(latencies):.2f} ms")
            print(f"    P95: {latencies[int(len(latencies) * 0.95)]:.2f} ms")
            print(f"    P99: {latencies[int(len(latencies) * 0.99)]:.2f} ms")
            print(f"    Success Rate: {successful_requests/iterations*100:.1f}%")
            print(f"    Throughput: {1000/statistics.mean(latencies):.1f} req/s")
        else:
            print(f"  ❌ No successful requests")
        
        print()
    
    # Print summary table
    print("📈 Summary Table")
    print("=" * 80)
    print(f"{'Scenario':<25} {'Avg (ms)':<10} {'P95 (ms)':<10} {'P99 (ms)':<10} {'Success %':<10} {'Throughput':<12}")
    print("-" * 80)
    
    for scenario_name, result in results.items():
        print(f"{scenario_name:<25} {result['avg_latency_ms']:<10.2f} {result['p95_latency_ms']:<10.2f} "
              f"{result['p99_latency_ms']:<10.2f} {result['success_rate']*100:<9.1f}% {result['throughput_rps']:<11.1f}")
    
    # Overall statistics
    if results:
        all_latencies = [r['avg_latency_ms'] for r in results.values()]
        overall_avg = statistics.mean(all_latencies)
        overall_p95 = statistics.mean([r['p95_latency_ms'] for r in results.values()])
        
        print("\n🎯 Overall Performance")
        print("=" * 40)
        print(f"Average Latency: {overall_avg:.2f} ms")
        print(f"Average P95 Latency: {overall_p95:.2f} ms")
        
        # Performance assessment
        if overall_avg < 10:
            print("✅ Excellent performance! (< 10ms)")
        elif overall_avg < 50:
            print("✅ Good performance! (< 50ms)")
        elif overall_avg < 100:
            print("⚠️  Acceptable performance (< 100ms)")
        else:
            print("❌ Poor performance (> 100ms) - needs optimization")
        
        # Save results
        timestamp = int(time.time())
        filename = f"streamlit_latency_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump({
                "timestamp": timestamp,
                "api_url": api_url,
                "iterations": iterations,
                "results": results,
                "overall_stats": {
                    "avg_latency_ms": overall_avg,
                    "avg_p95_latency_ms": overall_p95
                }
            }, f, indent=2)
        
        print(f"💾 Results saved to {filename}")

def measure_concurrent_latency(api_url: str = "http://localhost:8000", num_concurrent: int = 10, iterations: int = 20):
    """Measure latency under concurrent load"""
    
    print(f"\n⚡ Concurrent Load Test ({num_concurrent} concurrent users)")
    print("=" * 50)
    
    import threading
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    def make_request():
        start_time = time.perf_counter()
        try:
            response = requests.post(
                f"{api_url}/quote",
                json={
                    "token_in": "BTC",
                    "token_out": "USDC",
                    "amount_in": 1.0
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    return (time.perf_counter() - start_time) * 1000, True
            return None, False
        except:
            return None, False
    
    latencies = []
    successful_requests = 0
    
    with ThreadPoolExecutor(max_workers=num_concurrent) as executor:
        futures = [executor.submit(make_request) for _ in range(iterations)]
        
        for future in as_completed(futures):
            latency, success = future.result()
            if success and latency is not None:
                successful_requests += 1
                latencies.append(latency)
    
    if latencies:
        latencies.sort()
        avg_latency = statistics.mean(latencies)
        p95_latency = latencies[int(len(latencies) * 0.95)]
        p99_latency = latencies[int(len(latencies) * 0.99)]
        
        print(f"📊 Concurrent Results:")
        print(f"  Average Latency: {avg_latency:.2f} ms")
        print(f"  P95 Latency: {p95_latency:.2f} ms")
        print(f"  P99 Latency: {p99_latency:.2f} ms")
        print(f"  Success Rate: {successful_requests/iterations*100:.1f}%")
        print(f"  Throughput: {1000/avg_latency:.1f} req/s")
        
        # Performance assessment
        if avg_latency < 50:
            print("✅ Excellent concurrent performance!")
        elif avg_latency < 100:
            print("✅ Good concurrent performance")
        elif avg_latency < 200:
            print("⚠️  Acceptable concurrent performance")
        else:
            print("❌ Poor concurrent performance - needs optimization")
    else:
        print("❌ No successful concurrent requests")

if __name__ == "__main__":
    # Check if API server is running
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ API server is running")
        else:
            print("❌ API server returned error")
            exit(1)
    except:
        print("❌ API server is not running. Please start it first:")
        print("   python api_server.py")
        exit(1)
    
    # Run measurements
    measure_streamlit_latency(iterations=30)
    measure_concurrent_latency(num_concurrent=5, iterations=20) 