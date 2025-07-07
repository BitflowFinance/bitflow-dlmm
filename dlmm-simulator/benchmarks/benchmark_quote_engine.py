#!/usr/bin/env python3
"""
Benchmark script for DLMM Quote Engine performance.
Measures latency and throughput for different quote scenarios.
Compares original vs optimized implementations.
"""

import sys
import os
import time
import statistics
import json
from typing import List, Dict, Tuple
from dataclasses import dataclass
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.quote_engine import MockRedisClient, QuoteEngine


@dataclass
class BenchmarkResult:
    """Results from a single benchmark test"""
    test_name: str
    implementation: str  # "original" or "optimized"
    token_in: str
    token_out: str
    amount_in: float
    avg_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    success_rate: float
    total_requests: int
    successful_requests: int
    throughput_rps: float
    route_type: str
    steps_count: int
    price_impact: float


class QuoteEngineBenchmark:
    """Benchmark suite for quote engine performance"""
    
    def __init__(self, api_url: str = "http://localhost:8000"):
        self.api_url = api_url
        self.redis_client = MockRedisClient()
        self.quote_engine = QuoteEngine(self.redis_client)
        # Note: Now using the same optimized engine for both tests since we've consolidated
        self.optimized_redis_client = MockRedisClient()
        self.optimized_quote_engine = QuoteEngine(self.optimized_redis_client)
        
    def benchmark_original_engine(self, test_cases: List[Dict]) -> List[BenchmarkResult]:
        """Benchmark original quote engine calls"""
        results = []
        
        for test_case in test_cases:
            print(f"🔧 Benchmarking original engine: {test_case['name']}")
            
            latencies = []
            successful_requests = 0
            total_requests = test_case.get('iterations', 100)
            
            for i in range(total_requests):
                start_time = time.perf_counter()
                
                try:
                    quote = self.quote_engine.get_quote(
                        test_case['token_in'],
                        test_case['token_out'], 
                        test_case['amount_in']
                    )
                    
                    if quote.success:
                        successful_requests += 1
                        latencies.append((time.perf_counter() - start_time) * 1000)
                        
                        # Store route info from first successful request
                        if successful_requests == 1:
                            route_type = quote.route_type.value
                            steps_count = len(quote.steps)
                            price_impact = quote.price_impact
                    
                except Exception as e:
                    print(f"Error in iteration {i}: {e}")
            
            if latencies:
                latencies.sort()
                result = BenchmarkResult(
                    test_name=test_case['name'],
                    implementation="original",
                    token_in=test_case['token_in'],
                    token_out=test_case['token_out'],
                    amount_in=test_case['amount_in'],
                    avg_latency_ms=statistics.mean(latencies),
                    min_latency_ms=min(latencies),
                    max_latency_ms=max(latencies),
                    p95_latency_ms=latencies[int(len(latencies) * 0.95)],
                    p99_latency_ms=latencies[int(len(latencies) * 0.99)],
                    success_rate=successful_requests / total_requests,
                    total_requests=total_requests,
                    successful_requests=successful_requests,
                    throughput_rps=1000 / statistics.mean(latencies),
                    route_type=route_type,
                    steps_count=steps_count,
                    price_impact=price_impact
                )
                results.append(result)
        
        return results
    
    def benchmark_optimized_engine(self, test_cases: List[Dict]) -> List[BenchmarkResult]:
        """Benchmark optimized quote engine calls"""
        results = []
        
        for test_case in test_cases:
            print(f"⚡ Benchmarking optimized engine: {test_case['name']}")
            
            latencies = []
            successful_requests = 0
            total_requests = test_case.get('iterations', 100)
            
            for i in range(total_requests):
                start_time = time.perf_counter()
                
                try:
                    quote = self.optimized_quote_engine.get_quote(
                        test_case['token_in'],
                        test_case['token_out'], 
                        test_case['amount_in']
                    )
                    
                    if quote.success:
                        successful_requests += 1
                        latencies.append((time.perf_counter() - start_time) * 1000)
                        
                        # Store route info from first successful request
                        if successful_requests == 1:
                            route_type = quote.route_type.value
                            steps_count = len(quote.steps)
                            price_impact = quote.price_impact
                    
                except Exception as e:
                    print(f"Error in iteration {i}: {e}")
            
            if latencies:
                latencies.sort()
                result = BenchmarkResult(
                    test_name=test_case['name'],
                    implementation="optimized",
                    token_in=test_case['token_in'],
                    token_out=test_case['token_out'],
                    amount_in=test_case['amount_in'],
                    avg_latency_ms=statistics.mean(latencies),
                    min_latency_ms=min(latencies),
                    max_latency_ms=max(latencies),
                    p95_latency_ms=latencies[int(len(latencies) * 0.95)],
                    p99_latency_ms=latencies[int(len(latencies) * 0.99)],
                    success_rate=successful_requests / total_requests,
                    total_requests=total_requests,
                    successful_requests=successful_requests,
                    throughput_rps=1000 / statistics.mean(latencies),
                    route_type=route_type,
                    steps_count=steps_count,
                    price_impact=price_impact
                )
                results.append(result)
        
        return results
    
    def benchmark_api_endpoint(self, test_cases: List[Dict]) -> List[BenchmarkResult]:
        """Benchmark API endpoint calls (includes network overhead)"""
        results = []
        
        for test_case in test_cases:
            print(f"🌐 Benchmarking API endpoint: {test_case['name']}")
            
            latencies = []
            successful_requests = 0
            total_requests = test_case.get('iterations', 100)
            
            for i in range(total_requests):
                start_time = time.perf_counter()
                
                try:
                    response = requests.post(
                        f"{self.api_url}/quote",
                        json={
                            "token_in": test_case['token_in'],
                            "token_out": test_case['token_out'],
                            "amount_in": test_case['amount_in']
                        },
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('success'):
                            successful_requests += 1
                            latencies.append((time.perf_counter() - start_time) * 1000)
                            
                            # Store route info from first successful request
                            if successful_requests == 1:
                                route_type = data.get('route_type', 'unknown')
                                steps_count = len(data.get('steps', []))
                                price_impact = data.get('price_impact', 0)
                    
                except Exception as e:
                    print(f"Error in iteration {i}: {e}")
            
            if latencies:
                latencies.sort()
                result = BenchmarkResult(
                    test_name=test_case['name'],
                    implementation="api",
                    token_in=test_case['token_in'],
                    token_out=test_case['token_out'],
                    amount_in=test_case['amount_in'],
                    avg_latency_ms=statistics.mean(latencies),
                    min_latency_ms=min(latencies),
                    max_latency_ms=max(latencies),
                    p95_latency_ms=latencies[int(len(latencies) * 0.95)],
                    p99_latency_ms=latencies[int(len(latencies) * 0.99)],
                    success_rate=successful_requests / total_requests,
                    total_requests=total_requests,
                    successful_requests=successful_requests,
                    throughput_rps=1000 / statistics.mean(latencies),
                    route_type=route_type,
                    steps_count=steps_count,
                    price_impact=price_impact
                )
                results.append(result)
        
        return results
    
    def benchmark_concurrent_requests(self, test_case: Dict, num_threads: int = 10) -> BenchmarkResult:
        """Benchmark concurrent requests to test throughput"""
        print(f"⚡ Benchmarking concurrent requests: {test_case['name']} with {num_threads} threads")
        
        latencies = []
        successful_requests = 0
        total_requests = test_case.get('iterations', 100)
        
        def make_request():
            start_time = time.perf_counter()
            try:
                response = requests.post(
                    f"{self.api_url}/quote",
                    json={
                        "token_in": test_case['token_in'],
                        "token_out": test_case['token_out'],
                        "amount_in": test_case['amount_in']
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
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(make_request) for _ in range(total_requests)]
            
            for future in as_completed(futures):
                latency, success = future.result()
                if success and latency is not None:
                    successful_requests += 1
                    latencies.append(latency)
        
        if latencies:
            latencies.sort()
            return BenchmarkResult(
                test_name=f"{test_case['name']} (concurrent)",
                implementation="concurrent",
                token_in=test_case['token_in'],
                token_out=test_case['token_out'],
                amount_in=test_case['amount_in'],
                avg_latency_ms=statistics.mean(latencies),
                min_latency_ms=min(latencies),
                max_latency_ms=max(latencies),
                p95_latency_ms=latencies[int(len(latencies) * 0.95)],
                p99_latency_ms=latencies[int(len(latencies) * 0.99)],
                success_rate=successful_requests / total_requests,
                total_requests=total_requests,
                successful_requests=successful_requests,
                throughput_rps=1000 / statistics.mean(latencies),
                route_type="concurrent",
                steps_count=0,
                price_impact=0
            )
        
        return None
    
    def print_results(self, results: List[BenchmarkResult], title: str):
        """Print benchmark results in a formatted table"""
        print(f"\n📊 {title}")
        print("=" * 140)
        print(f"{'Test Name':<25} {'Impl':<10} {'Avg (ms)':<10} {'P95 (ms)':<10} {'P99 (ms)':<10} {'Success %':<10} {'Throughput':<12} {'Route':<12} {'Steps':<6}")
        print("-" * 140)
        
        for result in results:
            print(f"{result.test_name:<25} {result.implementation:<10} {result.avg_latency_ms:<10.2f} {result.p95_latency_ms:<10.2f} "
                  f"{result.p99_latency_ms:<10.2f} {result.success_rate*100:<9.1f}% {result.throughput_rps:<11.1f} "
                  f"{result.route_type:<12} {result.steps_count:<6}")
    
    def print_comparison(self, original_results: List[BenchmarkResult], optimized_results: List[BenchmarkResult]):
        """Print comparison between original and optimized implementations"""
        print(f"\n📈 Performance Comparison: Original vs Optimized")
        print("=" * 100)
        print(f"{'Test Name':<25} {'Original (ms)':<15} {'Optimized (ms)':<15} {'Improvement':<15} {'Speedup':<10}")
        print("-" * 100)
        
        # Create lookup dictionaries
        original_lookup = {r.test_name: r for r in original_results}
        optimized_lookup = {r.test_name: r for r in optimized_results}
        
        for test_name in original_lookup.keys():
            if test_name in optimized_lookup:
                orig = original_lookup[test_name]
                opt = optimized_lookup[test_name]
                
                improvement_ms = orig.avg_latency_ms - opt.avg_latency_ms
                improvement_pct = (improvement_ms / orig.avg_latency_ms) * 100
                speedup = orig.avg_latency_ms / opt.avg_latency_ms
                
                print(f"{test_name:<25} {orig.avg_latency_ms:<15.2f} {opt.avg_latency_ms:<15.2f} "
                      f"{improvement_pct:<14.1f}% {speedup:<9.2f}x")
    
    def save_results(self, results: List[BenchmarkResult], filename: str):
        """Save benchmark results to JSON file"""
        data = []
        for result in results:
            data.append({
                'test_name': result.test_name,
                'implementation': result.implementation,
                'token_in': result.token_in,
                'token_out': result.token_out,
                'amount_in': result.amount_in,
                'avg_latency_ms': result.avg_latency_ms,
                'min_latency_ms': result.min_latency_ms,
                'max_latency_ms': result.max_latency_ms,
                'p95_latency_ms': result.p95_latency_ms,
                'p99_latency_ms': result.p99_latency_ms,
                'success_rate': result.success_rate,
                'total_requests': result.total_requests,
                'successful_requests': result.successful_requests,
                'throughput_rps': result.throughput_rps,
                'route_type': result.route_type,
                'steps_count': result.steps_count,
                'price_impact': result.price_impact
            })
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"💾 Results saved to {filename}")


def main():
    """Run comprehensive benchmark suite"""
    print("🚀 DLMM Quote Engine Performance Benchmark")
    print("=" * 60)
    
    # Initialize benchmark suite
    benchmark = QuoteEngineBenchmark()
    
    # Define test cases
    test_cases = [
        {
            'name': 'Small Trade (1 BTC)',
            'token_in': 'BTC',
            'token_out': 'USDC',
            'amount_in': 1.0,
            'iterations': 100
        },
        {
            'name': 'Medium Trade (1100 BTC)',
            'token_in': 'BTC',
            'token_out': 'USDC',
            'amount_in': 1100.0,
            'iterations': 100
        },
        {
            'name': 'Large Trade (2000 BTC)',
            'token_in': 'BTC',
            'token_out': 'USDC',
            'amount_in': 2000.0,
            'iterations': 100
        },
        {
            'name': 'SOL Trade (1000 SOL)',
            'token_in': 'SOL',
            'token_out': 'USDC',
            'amount_in': 1000.0,
            'iterations': 100
        }
    ]
    
    # Run benchmarks
    print("\n🔧 Benchmarking Original Engine...")
    original_results = benchmark.benchmark_original_engine(test_cases)
    benchmark.print_results(original_results, "Original Engine Performance")
    
    print("\n⚡ Benchmarking Optimized Engine...")
    optimized_results = benchmark.benchmark_optimized_engine(test_cases)
    benchmark.print_results(optimized_results, "Optimized Engine Performance")
    
    print("\n🌐 Benchmarking API Endpoint...")
    api_results = benchmark.benchmark_api_endpoint(test_cases)
    benchmark.print_results(api_results, "API Endpoint Performance")
    
    # Print comparison
    benchmark.print_comparison(original_results, optimized_results)
    
    # Run concurrent benchmark
    print("\n⚡ Benchmarking Concurrent Requests...")
    concurrent_result = benchmark.benchmark_concurrent_requests(test_cases[1])  # Medium trade
    if concurrent_result:
        benchmark.print_results([concurrent_result], "Concurrent Performance")
    
    # Save results
    timestamp = int(time.time())
    all_results = original_results + optimized_results + api_results
    if concurrent_result:
        all_results.append(concurrent_result)
    
    benchmark.save_results(all_results, f"benchmark_comparison_{timestamp}.json")
    
    # Performance analysis
    print("\n📈 Performance Analysis")
    print("=" * 60)
    
    if original_results and optimized_results:
        avg_original = statistics.mean([r.avg_latency_ms for r in original_results])
        avg_optimized = statistics.mean([r.avg_latency_ms for r in optimized_results])
        avg_api = statistics.mean([r.avg_latency_ms for r in api_results]) if api_results else 0
        
        improvement = avg_original - avg_optimized
        improvement_pct = (improvement / avg_original) * 100
        speedup = avg_original / avg_optimized
        
        print(f"Average Original Engine Latency: {avg_original:.2f} ms")
        print(f"Average Optimized Engine Latency: {avg_optimized:.2f} ms")
        print(f"Average API Endpoint Latency: {avg_api:.2f} ms")
        print(f"Optimization Improvement: {improvement:.2f} ms ({improvement_pct:.1f}%)")
        print(f"Speedup: {speedup:.2f}x")
        
        if improvement_pct > 20:
            print("✅ Significant performance improvement achieved!")
        elif improvement_pct > 10:
            print("✅ Moderate performance improvement achieved")
        else:
            print("⚠️  Minimal performance improvement - consider further optimization")


if __name__ == "__main__":
    main() 