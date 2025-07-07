#!/usr/bin/env python3
"""
Simple test runner for DLMM simulator.
"""

import sys
import os
import subprocess

def run_tests():
    """Run all tests in the project."""
    print("Running DLMM Simulator Tests...")
    
    # Add src to path
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
    
    # Run pytest
    try:
        result = subprocess.run([
            sys.executable, '-m', 'pytest', 'tests/', '-v'
        ], capture_output=True, text=True)
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        return result.returncode == 0
    except Exception as e:
        print(f"Error running tests: {e}")
        return False

def run_examples():
    """Run example scripts."""
    print("\nRunning Examples...")
    
    examples = [
        'examples/basic_routing.py',
        'examples/multi_pool_routing.py'
    ]
    
    for example in examples:
        print(f"\n--- Running {example} ---")
        try:
            result = subprocess.run([
                sys.executable, example
            ], capture_output=True, text=True)
            
            print(result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr)
                
        except Exception as e:
            print(f"Error running {example}: {e}")

if __name__ == "__main__":
    print("=== DLMM Simulator Test Runner ===\n")
    
    # Run tests
    tests_passed = run_tests()
    
    # Run examples
    run_examples()
    
    print("\n=== Test Runner Complete ===")
    if tests_passed:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed!")
        sys.exit(1) 