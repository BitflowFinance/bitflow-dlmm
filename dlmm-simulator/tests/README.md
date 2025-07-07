# DLMM Quote Engine Tests

This directory contains all test scripts and test data for the DLMM quote engine.

## Test Scripts

### Core Tests
- `test_quote_engine.py` - Main quote engine functionality tests
- `test_routing.py` - Routing algorithm tests
- `test_multibin.py` - Multi-bin swap simulation tests

### Feature Tests
- `test_dynamic_pricing.py` - Dynamic pricing logic tests
- `test_fee_calculation.py` - Fee calculation verification
- `test_multi_bin_swap.py` - Multi-bin swap scenarios
- `test_pool_id_fix.py` - Pool ID handling tests

### Test Runner
- `run_tests.py` - Main test runner script

## Running Tests

### Run All Tests
```bash
python tests/run_tests.py
```

### Run Individual Tests
```bash
# Core functionality
python tests/test_quote_engine.py

# Specific features
python tests/test_dynamic_pricing.py
python tests/test_fee_calculation.py
python tests/test_multi_bin_swap.py
python tests/test_pool_id_fix.py
```

### Run with pytest
```bash
pytest tests/
```

## Test Data

Test data files are stored in the `data/` subdirectory:
- Simulation results
- Test fixtures
- Expected output files

## Test Categories

### Unit Tests
- Individual component testing
- Function-level validation
- Edge case handling

### Integration Tests
- Component interaction testing
- End-to-end workflow validation
- API integration testing

### Performance Tests
- Load testing scenarios
- Memory usage validation
- Response time verification

## Test Requirements

- Python testing frameworks: `pytest`, `unittest`
- Mock data and fixtures
- API server for integration tests 