# Diagnostic Scripts

This directory contains diagnostic scripts used to troubleshoot issues with the Folio application, particularly when running in a Docker container.

## Available Scripts

### `run_diagnostics.sh`

A shell script that runs all diagnostic scripts on a running Docker container.

**Usage:**
```bash
./run_diagnostics.sh [container_name]
```

If `container_name` is not provided, it defaults to "omninmo-folio-1".

### `check_modules.py`

Checks for the availability and versions of Python modules required by the Folio application.

**Usage:**
```bash
python check_modules.py
```

**In Docker:**
```bash
docker exec omninmo-folio-1 python /app/scripts/check_modules.py
```

### `check_network.py`

Tests network connectivity from inside a Docker container, including binding to different interfaces and testing external connectivity.

**Usage:**
```bash
python check_network.py [--bind-test] [--external-test]
```

**In Docker:**
```bash
docker exec omninmo-folio-1 python /app/scripts/check_network.py
```

### `test_imports.py`

Tests importing various modules used by the Folio application to diagnose import-related issues.

**Usage:**
```bash
python test_imports.py
```

**In Docker:**
```bash
docker exec omninmo-folio-1 python /app/scripts/test_imports.py
```

## Common Issues

These scripts were created to diagnose the following common issues:

1. **Module Import Errors**: Problems with Python module imports, particularly with the project structure in a Docker container.

2. **Network Binding Issues**: Issues with the application binding to the correct network interface inside the container.

3. **Dependency Problems**: Missing or incompatible dependencies.

## Adding New Scripts

When adding new diagnostic scripts, please follow these guidelines:

1. Include a detailed docstring explaining the purpose of the script
2. Add usage examples, both for local execution and in Docker
3. Make the script executable (`chmod +x script_name.py`)
4. Update this README with information about the new script
