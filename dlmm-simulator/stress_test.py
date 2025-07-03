#!/usr/bin/env python3
"""
Stress Testing Suite for DLMM Quote Engine
Tests performance, reliability, and edge cases under load.
"""

import time
import threading
import concurrent.futures
import statistics
import json
from typing import List, Dict, Any
import requests
import random

from src.quote_engine import MockRedisClient, QuoteEngine


class StressTestSuite:
    """Comprehensive stress testing for the quote engine"""
    
    def __init__(self, api_url: str = "http://localhost:8000"):
        self.api_url = api_url
        self.redis_client = MockRedisClient()
        self.quote_engine = QuoteEngine(self.redis_client)
        
        # Test scenarios
        self.tokens = ["BTC", "ETH", "USDC", "SOL"]
        self.amounts = [0.001, 0.01, 0.1, 1.0, 10.0, 100.0, 1000.0]
        
    def test_single_quotes(self, num_requests: int = 100) -> Dict[str, Any]:
        """Test single quote performance"""
        print(f"🧪 Testing {num_requests} single quotes...")
        
        results = []
        start_time = time.time()
        
        for i in range(num_requests):
            token_in = random.choice(self.tokens)
            token_out = random.choice([t for t in self.tokens if t != token_in])
            amount = random.choice(self.amounts)
            
            try:
                quote_start = time.time()
                quote = self.quote_engine.get_quote(
                    token_in, token_out, amount
                )
                quote_time = time.time() - quote_start
                
                results.append({
                    "success": quote.success,
                    "time": quote_time,
                    "token_in": token_in,
                    "token_out": token_out,
                    "amount": amount,
                    "amount_out": quote.amount_out if quote.success else 0
                })
                
            except Exception as e:
                results.append({
                    "success": False,
                    "time": 0,
                    "error": str(e),
                    "token_in": token_in,
                    "token_out": token_out,
                    "amount": amount
                })
        
        total_time = time.time() - start_time
        successful_quotes = [r for r in results if r["success"]]
        
        return {
            "test_type": "single_quotes",
            "total_requests": num_requests,
            "successful_requests": len(successful_quotes),
            "success_rate": len(successful_quotes) / num_requests * 100,
            "total_time": total_time,
            "avg_time": statistics.mean([r["time"] for r in successful_quotes]) if successful_quotes else 0,
            "min_time": min([r["time"] for r in successful_quotes]) if successful_quotes else 0,
            "max_time": max([r["time"] for r in successful_quotes]) if successful_quotes else 0,
            "requests_per_second": num_requests / total_time
        }
    
    def test_concurrent_quotes(self, num_threads: int = 10, requests_per_thread: int = 50) -> Dict[str, Any]:
        """Test concurrent quote performance"""
        print(f"🧪 Testing {num_threads} threads with {requests_per_thread} requests each...")
        
        results = []
        start_time = time.time()
        
        def worker(thread_id: int):
            thread_results = []
            for i in range(requests_per_thread):
                token_in = random.choice(self.tokens)
                token_out = random.choice([t for t in self.tokens if t != token_in])
                amount = random.choice(self.amounts)
                
                try:
                    quote_start = time.time()
                    quote = self.quote_engine.get_quote(
                        token_in, token_out, amount
                    )
                    quote_time = time.time() - quote_start
                    
                    thread_results.append({
                        "thread_id": thread_id,
                        "success": quote.success,
                        "time": quote_time,
                        "token_in": token_in,
                        "token_out": token_out,
                        "amount": amount
                    })
                    
                except Exception as e:
                    thread_results.append({
                        "thread_id": thread_id,
                        "success": False,
                        "time": 0,
                        "error": str(e),
                        "token_in": token_in,
                        "token_out": token_out,
                        "amount": amount
                    })
            
            return thread_results
        
        # Run concurrent tests
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker, i) for i in range(num_threads)]
            for future in concurrent.futures.as_completed(futures):
                results.extend(future.result())
        
        total_time = time.time() - start_time
        successful_quotes = [r for r in results if r["success"]]
        total_requests = num_threads * requests_per_thread
        
        return {
            "test_type": "concurrent_quotes",
            "total_threads": num_threads,
            "requests_per_thread": requests_per_thread,
            "total_requests": total_requests,
            "successful_requests": len(successful_quotes),
            "success_rate": len(successful_quotes) / total_requests * 100,
            "total_time": total_time,
            "avg_time": statistics.mean([r["time"] for r in successful_quotes]) if successful_quotes else 0,
            "min_time": min([r["time"] for r in successful_quotes]) if successful_quotes else 0,
            "max_time": max([r["time"] for r in successful_quotes]) if successful_quotes else 0,
            "requests_per_second": total_requests / total_time
        }
    
    def test_api_endpoints(self, num_requests: int = 100) -> Dict[str, Any]:
        """Test API endpoint performance"""
        print(f"🧪 Testing {num_requests} API requests...")
        
        endpoints = [
            ("/health", "GET"),
            ("/tokens", "GET"),
            ("/pools", "GET"),
            ("/pairs", "GET")
        ]
        
        results = []
        start_time = time.time()
        
        for i in range(num_requests):
            endpoint, method = random.choice(endpoints)
            
            try:
                if method == "GET":
                    api_start = time.time()
                    response = requests.get(f"{self.api_url}{endpoint}", timeout=5)
                    api_time = time.time() - api_start
                    
                    results.append({
                        "endpoint": endpoint,
                        "method": method,
                        "status_code": response.status_code,
                        "time": api_time,
                        "success": response.status_code == 200
                    })
                elif method == "POST":
                    # Test quote endpoint
                    token_in = random.choice(self.tokens)
                    token_out = random.choice([t for t in self.tokens if t != token_in])
                    amount = random.choice(self.amounts)
                    
                    payload = {
                        "token_in": token_in,
                        "token_out": token_out,
                        "amount_in": amount
                    }
                    
                    api_start = time.time()
                    response = requests.post(
                        f"{self.api_url}/quote",
                        json=payload,
                        timeout=5
                    )
                    api_time = time.time() - api_start
                    
                    results.append({
                        "endpoint": "/quote",
                        "method": method,
                        "status_code": response.status_code,
                        "time": api_time,
                        "success": response.status_code == 200
                    })
                    
            except Exception as e:
                results.append({
                    "endpoint": endpoint,
                    "method": method,
                    "status_code": 0,
                    "time": 0,
                    "success": False,
                    "error": str(e)
                })
        
        total_time = time.time() - start_time
        successful_requests = [r for r in results if r["success"]]
        
        return {
            "test_type": "api_endpoints",
            "total_requests": num_requests,
            "successful_requests": len(successful_requests),
            "success_rate": len(successful_requests) / num_requests * 100,
            "total_time": total_time,
            "avg_time": statistics.mean([r["time"] for r in successful_requests]) if successful_requests else 0,
            "min_time": min([r["time"] for r in successful_requests]) if successful_requests else 0,
            "max_time": max([r["time"] for r in successful_requests]) if successful_requests else 0,
            "requests_per_second": num_requests / total_time
        }
    
    def test_edge_cases(self) -> Dict[str, Any]:
        """Test edge cases and error conditions"""
        print("🧪 Testing edge cases...")
        
        edge_cases = [
            # Same token swap
            ("BTC", "BTC", 1.0),
            # Zero amount
            ("BTC", "ETH", 0.0),
            # Very small amount
            ("BTC", "ETH", 0.0000001),
            # Very large amount
            ("BTC", "ETH", 1000000.0),
            # Non-existent tokens
            ("INVALID", "BTC", 1.0),
            ("BTC", "INVALID", 1.0),
            # Negative amount
            ("BTC", "ETH", -1.0),
        ]
        
        results = []
        
        for token_in, token_out, amount in edge_cases:
            try:
                quote = self.quote_engine.get_quote(
                    token_in, token_out, amount
                )
                
                results.append({
                    "case": f"{token_in}->{token_out} ({amount})",
                    "success": quote.success,
                    "expected_failure": token_in == token_out or amount <= 0 or "INVALID" in [token_in, token_out],
                    "amount_out": quote.amount_out if quote.success else 0,
                    "error": quote.error
                })
                
            except Exception as e:
                results.append({
                    "case": f"{token_in}->{token_out} ({amount})",
                    "success": False,
                    "expected_failure": token_in == token_out or amount <= 0 or "INVALID" in [token_in, token_out],
                    "amount_out": 0,
                    "error": str(e)
                })
        
        return {
            "test_type": "edge_cases",
            "total_cases": len(edge_cases),
            "results": results
        }
    
    def test_memory_usage(self, num_iterations: int = 1000) -> Dict[str, Any]:
        """Test memory usage under load"""
        print(f"🧪 Testing memory usage with {num_iterations} iterations...")
        
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        start_time = time.time()
        
        for i in range(num_iterations):
            token_in = random.choice(self.tokens)
            token_out = random.choice([t for t in self.tokens if t != token_in])
            amount = random.choice(self.amounts)
            
            try:
                quote = self.quote_engine.get_quote(
                    token_in, token_out, amount
                )
            except:
                pass
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        total_time = time.time() - start_time
        
        return {
            "test_type": "memory_usage",
            "iterations": num_iterations,
            "initial_memory_mb": initial_memory,
            "final_memory_mb": final_memory,
            "memory_increase_mb": final_memory - initial_memory,
            "total_time": total_time,
            "iterations_per_second": num_iterations / total_time
        }
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all stress tests"""
        print("🚀 Starting comprehensive stress test suite...")
        
        results = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "tests": {}
        }
        
        # Run all tests
        results["tests"]["single_quotes"] = self.test_single_quotes(100)
        results["tests"]["concurrent_quotes"] = self.test_concurrent_quotes(5, 20)
        results["tests"]["api_endpoints"] = self.test_api_endpoints(50)
        results["tests"]["edge_cases"] = self.test_edge_cases()
        results["tests"]["memory_usage"] = self.test_memory_usage(500)
        
        # Save results
        with open("stress_test_results.json", "w") as f:
            json.dump(results, f, indent=2)
        
        print("✅ Stress test suite completed!")
        print(f"📊 Results saved to: stress_test_results.json")
        
        return results
    
    def print_summary(self, results: Dict[str, Any]):
        """Print a summary of test results"""
        print("\n" + "="*60)
        print("📊 STRESS TEST SUMMARY")
        print("="*60)
        
        for test_name, test_result in results["tests"].items():
            print(f"\n🔍 {test_name.upper()}:")
            
            if test_name == "edge_cases":
                print(f"   Total cases: {test_result['total_cases']}")
                for case in test_result["results"]:
                    status = "✅" if case["success"] else "❌"
                    print(f"   {status} {case['case']}: {case.get('error', 'Success')}")
            
            elif test_name == "memory_usage":
                print(f"   Memory increase: {test_result['memory_increase_mb']:.2f} MB")
                print(f"   Iterations/sec: {test_result['iterations_per_second']:.2f}")
            
            else:
                print(f"   Success rate: {test_result['success_rate']:.1f}%")
                print(f"   Avg response time: {test_result['avg_time']*1000:.2f} ms")
                print(f"   Requests/sec: {test_result['requests_per_second']:.1f}")
        
        print("\n" + "="*60)


if __name__ == "__main__":
    # Run stress tests
    test_suite = StressTestSuite()
    results = test_suite.run_all_tests()
    test_suite.print_summary(results) 