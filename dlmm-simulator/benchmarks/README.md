# DLMM Quote Engine Benchmarks

This directory contains performance benchmarking and measurement tools for the DLMM quote engine.

## 🚀 Recent Updates

The quote engine has been refactored with the **optimized implementation now as the default**:
- **`src/quote_engine.py`** - Optimized implementation (default)
- **`src/quote_engine_legacy.py`** - Original implementation (preserved)
- **Performance**: 48.4% latency reduction, 1.94x speedup achieved
- **Benchmark script updated** to reflect the consolidation

## Scripts

### `benchmark_quote_engine.py`
Comprehensive performance benchmark comparing original vs optimized quote engine implementations.

**Usage:**
```bash
python benchmarks/benchmark_quote_engine.py
```

**What it does:**
- Benchmarks original quote engine performance
- Benchmarks optimized quote engine performance  
- Compares performance improvements
- Tests API endpoint performance
- Measures concurrent request handling
- Saves results to JSON files

**Note**: Now uses the same optimized engine for both "original" and "optimized" tests since we've consolidated the implementations.

### `measure_streamlit_latency.py`
End-to-end latency measurement simulating real Streamlit app user experience.

**Usage:**
```bash
python benchmarks/measure_streamlit_latency.py
```

**What it does:**
- Measures API response times for different trade sizes
- Tests concurrent user scenarios
- Provides P95/P99 latency metrics
- Simulates real-world usage patterns

## Results

Benchmark results are stored in the `results/` subdirectory:
- `benchmark_comparison_*.json` - Engine performance comparison results
- `streamlit_latency_*.json` - End-to-end latency measurement results

## Performance Metrics

The benchmarks measure:
- **Latency**: Average, P95, P99 response times
- **Throughput**: Requests per second
- **Success Rate**: Percentage of successful requests
- **Concurrent Performance**: Multi-user load testing

## Requirements

- API server running on `http://localhost:8000`
- Python dependencies: `requests`, `statistics`, `concurrent.futures` 