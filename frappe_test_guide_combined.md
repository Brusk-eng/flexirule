# Frappe Unit Testing Guide - Part 1: Fundamentals

## Table of Contents
1. [Introduction](#introduction)
2. [Test Structure and Organization](#test-structure-and-organization)
3. [Base Test Classes](#base-test-classes)
4. [Writing Your First Test](#writing-your-first-test)
5. [Test File Naming Conventions](#test-file-naming-conventions)
6. [Test Discovery](#test-discovery)

---

## Introduction

Frappe uses Python's built-in `unittest` framework for unit testing. The framework provides a robust testing infrastructure that integrates seamlessly with Frappe's database, caching, and permission systems.

### Key Features of Frappe Testing

- **Automatic Database Rollback**: All database changes are automatically rolled back after each test
- **Test Record Management**: Automatic creation and management of test data
- **Permission Testing**: Built-in utilities for testing user permissions
- **Transaction Management**: Proper handling of database transactions
- **Cache Management**: Automatic cache clearing between tests
- **Parallel Execution**: Support for running tests in parallel

### Prerequisites

Before writing tests, ensure:

1. **Tests are enabled** for your site:
   ```bash
   bench --site [site-name] set-config allow_tests true
   ```

2. **Development dependencies** are installed:
   ```bash
   bench setup requirements --dev
   ```

3. **Test site** is properly configured (usually `test_site` or your development site)

---

## Test Structure and Organization

### Directory Structure

Tests in Frappe follow a specific directory structure:

```
your_app/
├── your_app/
│   ├── module/
│   │   ├── doctype/
│   │   │   └── doctype_name/
│   │   │       ├── doctype_name.py
│   │   │       ├── test_doctype_name.py      # Test file
│   │   │       └── test_records.json         # Test data (optional)
│   │   └── tests/
│   │       └── test_module.py                # Module-level tests
│   └── tests/
│       └── test_app.py                        # App-level tests
```

### Test File Locations

1. **DocType Tests**: Located in the same directory as the DocType
   - Path: `apps/your_app/your_app/module/doctype/doctype_name/test_doctype_name.py`
   - Example: `apps/erpnext/erpnext/stock/doctype/item/test_item.py`

2. **Module Tests**: Located in module's `tests/` directory
   - Path: `apps/your_app/your_app/module/tests/test_module.py`
   - Example: `apps/frappe/frappe/tests/test_utils.py`

3. **App-Level Tests**: Located in app's root `tests/` directory
   - Path: `apps/your_app/your_app/tests/test_app.py`

---

## Base Test Classes

Frappe provides several base test classes that you should inherit from when writing tests.

### FrappeTestCase

The primary base class for all Frappe tests. It extends Python's `unittest.TestCase` and provides Frappe-specific functionality.

**Location**: `frappe.tests.utils.FrappeTestCase`

**Key Features**:
- Automatic database rollback after each test
- Thread-local variable cleanup
- Database connection management
- Cache clearing
- Custom assertion methods
- User context management
- Time freezing utilities

**Basic Usage**:
```python
import frappe
from frappe.tests.utils import FrappeTestCase

class TestMyDocType(FrappeTestCase):
    def test_something(self):
        # Your test code here
        pass
```

**Important Notes**:
- Always call `super().setUpClass()` if you override `setUpClass`
- Database changes are automatically rolled back after each test
- Each test runs in a clean environment

### FrappeAPITestCase

Specialized test case for testing API endpoints. Extends `FrappeTestCase`.

**Location**: `frappe.tests.test_api.FrappeAPITestCase`

**Key Features**:
- Built-in HTTP client methods (`get`, `post`, `put`, `patch`, `delete`)
- Automatic session management
- API path helpers
- Support for both v1 and v2 APIs

**Usage**:
```python
from frappe.tests.test_api import FrappeAPITestCase

class TestMyAPI(FrappeAPITestCase):
    version = "v1"  # or "v2" or "" for v1
    
    def test_get_resource(self):
        response = self.get(self.resource("ToDo", "test-todo"))
        self.assertEqual(response.status_code, 200)
    
    def test_create_resource(self):
        data = {"doctype": "ToDo", "description": "Test"}
        response = self.post(self.resource("ToDo"), data)
        self.assertEqual(response.status_code, 200)
```

### MockedRequestTestCase

For testing code that makes external HTTP requests. Automatically mocks all HTTP requests.

**Location**: `frappe.tests.utils.MockedRequestTestCase`

**Usage**:
```python
from frappe.tests.utils import MockedRequestTestCase
import responses

class TestExternalAPI(MockedRequestTestCase):
    def test_external_call(self):
        # Mock the external API response
        self.responses.add(
            responses.GET,
            "https://api.example.com/data",
            json={"status": "ok"},
            status=200
        )
        
        # Your code that calls the external API
        result = call_external_api()
        self.assertEqual(result["status"], "ok")
```

### UnitTestCase and IntegrationTestCase

These are newer test case classes (used in some apps like Raven) that provide a clearer separation between unit and integration tests.

**Note**: These may be aliases or wrappers around `FrappeTestCase` in newer Frappe versions. Check your Frappe version for availability.

**Usage** (if available):
```python
from frappe.tests import UnitTestCase, IntegrationTestCase

class TestMyDocType(UnitTestCase):
    """Unit tests - test individual functions/methods"""
    pass

class TestMyDocType(IntegrationTestCase):
    """Integration tests - test component interactions"""
    pass
```

---

## Writing Your First Test

### Basic Test Structure

```python
# Copyright (c) 2024, Your Company and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

class TestMyDocType(FrappeTestCase):
    """Test cases for MyDocType"""
    
    def test_create_document(self):
        """Test creating a new document"""
        doc = frappe.get_doc({
            "doctype": "MyDocType",
            "field1": "value1",
            "field2": "value2"
        })
        doc.insert()
        
        # Assertions
        self.assertIsNotNone(doc.name)
        self.assertEqual(doc.field1, "value1")
        self.assertTrue(frappe.db.exists("MyDocType", doc.name))
    
    def test_validation(self):
        """Test document validation"""
        doc = frappe.get_doc({
            "doctype": "MyDocType",
            # Missing required field
        })
        
        # Should raise validation error
        self.assertRaises(frappe.ValidationError, doc.insert)
```

### Test Method Naming

- Test methods **must** start with `test_`
- Use descriptive names: `test_create_document`, `test_validate_required_fields`
- Follow snake_case convention

### Common Test Patterns

#### 1. Testing Document Creation

```python
def test_create_document(self):
    doc = frappe.get_doc({
        "doctype": "MyDocType",
        "field1": "value1"
    })
    doc.insert()
    
    # Verify document was created
    self.assertIsNotNone(doc.name)
    self.assertTrue(frappe.db.exists("MyDocType", doc.name))
```

#### 2. Testing Document Updates

```python
def test_update_document(self):
    # Create document
    doc = frappe.get_doc({
        "doctype": "MyDocType",
        "field1": "old_value"
    })
    doc.insert()
    
    # Update document
    doc.field1 = "new_value"
    doc.save()
    
    # Reload and verify
    doc.reload()
    self.assertEqual(doc.field1, "new_value")
```

#### 3. Testing Document Deletion

```python
def test_delete_document(self):
    doc = frappe.get_doc({
        "doctype": "MyDocType",
        "field1": "value1"
    })
    doc.insert()
    doc_name = doc.name
    
    # Delete document
    frappe.delete_doc("MyDocType", doc_name)
    
    # Verify deletion
    self.assertFalse(frappe.db.exists("MyDocType", doc_name))
```

#### 4. Testing Validation Errors

```python
def test_required_field_validation(self):
    doc = frappe.get_doc({
        "doctype": "MyDocType",
        # Missing required field
    })
    
    # Should raise ValidationError
    with self.assertRaises(frappe.ValidationError):
        doc.insert()
```

#### 5. Testing Permissions

```python
def test_permissions(self):
    # Create document as Administrator
    doc = frappe.get_doc({
        "doctype": "MyDocType",
        "field1": "value1"
    })
    doc.insert()
    
    # Switch to regular user
    with self.set_user("test@example.com"):
        # Try to access document
        doc = frappe.get_doc("MyDocType", doc.name)
        
        # Check permissions
        self.assertTrue(doc.has_permission("read"))
        self.assertFalse(doc.has_permission("write"))
```

---

## Test File Naming Conventions

### Rules

1. **Test files must start with `test_`**
   - ✅ `test_my_doctype.py`
   - ✅ `test_utils.py`
   - ❌ `my_doctype_test.py`
   - ❌ `testmy_doctype.py`

2. **Test files must end with `.py`**

3. **For DocType tests**: Match the DocType name
   - DocType: `Item` → Test file: `test_item.py`
   - DocType: `Sales Invoice` → Test file: `test_sales_invoice.py`

4. **For module tests**: Use descriptive names
   - `test_utils.py`
   - `test_permissions.py`
   - `test_api.py`

### Examples

```
# DocType test
apps/erpnext/erpnext/stock/doctype/item/test_item.py

# Module test
apps/frappe/frappe/tests/test_utils.py

# App-level test
apps/erpnext/erpnext/tests/test_perf.py
```

---

## Test Discovery

Frappe automatically discovers tests based on file naming conventions.

### Discovery Rules

1. **Files starting with `test_`** are automatically discovered
2. **Files ending with `.py`** are considered test files
3. **Excluded directories**:
   - `locals/`
   - `.git/`
   - `public/`
   - `__pycache__/`
   - `doctype/doctype/boilerplate/`

### Test Class Discovery

- Classes inheriting from `unittest.TestCase` (or `FrappeTestCase`) are discovered
- Test methods starting with `test_` are discovered
- `setUp`, `tearDown`, `setUpClass`, `tearDownClass` are automatically called

### Example

```python
# This file will be discovered: test_my_doctype.py
import frappe
from frappe.tests.utils import FrappeTestCase

# This class will be discovered
class TestMyDocType(FrappeTestCase):
    # This method will be discovered and run
    def test_something(self):
        pass
    
    # This method will NOT be run as a test
    def helper_method(self):
        pass
```

---

## Next Steps

Continue to:
- [Part 2: Test Commands and Execution](./64-Frappe_Unit_Testing_Guide_Part_2_Test_Commands.md)
- [Part 3: Test Patterns and Best Practices](./65-Frappe_Unit_Testing_Guide_Part_3_Patterns.md)
- [Part 4: Advanced Testing Techniques](./66-Frappe_Unit_Testing_Guide_Part_4_Advanced.md)
- [Part 5: Test Data Management](./67-Frappe_Unit_Testing_Guide_Part_5_Test_Data.md)
- [Part 6: Test Utilities and Techniques](./68-Frappe_Unit_Testing_Guide_Part_6_Utilities.md)
- [Part 7: Assertions](./69-Frappe_Unit_Testing_Guide_Part_7_Assertions.md)
- [Part 8: Reports](./80-Frappe_Unit_Testing_Guide_Part_8_Reports.md)
- [Part 9: Test Records](./82-Frappe_Unit_Testing_Guide_Part_9_Test_Records.md)

# Frappe Unit Testing Guide - Part 2: Test Commands and Execution

## Table of Contents
1. [Enabling Tests](#enabling-tests)
2. [Basic Test Commands](#basic-test-commands)
3. [Running Tests by Scope](#running-tests-by-scope)
4. [Advanced Test Options](#advanced-test-options)
5. [Parallel Test Execution](#parallel-test-execution)
6. [Test Coverage](#test-coverage)
7. [Troubleshooting](#troubleshooting)

---

## Enabling Tests

Before running tests, you must enable them for your site:

```bash
bench --site [site-name] set-config allow_tests true
```

**Important**: Tests are disabled by default for security reasons. This prevents accidental test execution in production environments.

### Verify Tests Are Enabled

```bash
bench --site [site-name] get-config allow_tests
# Should return: true
```

### Disable Tests (if needed)

```bash
bench --site [site-name] set-config allow_tests false
```

---

## Basic Test Commands

### Command Structure

All test commands follow this basic structure:

```bash
bench --site [site-name] run-tests [options]
```

### Run All Tests

Run all tests in all installed apps:

```bash
bench --site [site-name] run-tests
```

**What it does**:
- Discovers all test files in all installed apps
- Runs tests in alphabetical order
- Creates test records automatically
- Rolls back all database changes after completion

**When to use**:
- Before committing code
- In CI/CD pipelines
- When you want to verify the entire system

**Example Output**:
```
Running tests...
test_create_document ... ok
test_update_document ... ok
test_delete_document ... ok

----------------------------------------------------------------------
Ran 3 tests in 0.123s

OK
```

---

## Running Tests by Scope

### Run Tests for a Specific App

```bash
bench --site [site-name] run-tests --app [app-name]
```

**Examples**:
```bash
# Run all Frappe tests
bench --site test_site run-tests --app frappe

# Run all ERPNext tests
bench --site test_site run-tests --app erpnext

# Run all tests for your custom app
bench --site test_site run-tests --app my_custom_app
```

**When to use**:
- Testing changes in a specific app
- Faster execution when you only need to test one app
- Isolating issues to a particular app

### Run Tests for a Specific DocType

```bash
bench --site [site-name] run-tests --doctype [DocType]
```

**Examples**:
```bash
# Run tests for Item DocType
bench --site test_site run-tests --doctype Item

# Run tests for Sales Invoice
bench --site test_site run-tests --doctype "Sales Invoice"

# Run tests for custom DocType
bench --site test_site run-tests --doctype "Custom DocType"
```

**What it does**:
- Finds the test file for the specified DocType
- Creates test records for the DocType and all dependencies
- Runs all test methods in the test class

**When to use**:
- Testing a specific DocType
- Quick iteration during development
- Debugging DocType-specific issues

**Note**: The DocType name is case-sensitive and must match exactly.

### Run Tests for a Specific Module

```bash
bench --site [site-name] run-tests --module [module-path]
```

**Examples**:
```bash
# Run tests for frappe.tests module
bench --site test_site run-tests --module frappe.tests

# Run tests for erpnext.accounts module
bench --site test_site run-tests --module erpnext.accounts

# Run tests for custom module
bench --site test_site run-tests --module my_app.my_module
```

**Module Path Format**:
- Use dot notation: `app.module`
- Must be a valid Python module path
- Module must contain test files

**When to use**:
- Testing a specific module
- Module-level integration tests
- Testing module-specific functionality

### Run Tests for All DocTypes in a Module Definition

```bash
bench --site [site-name] run-tests --module-def [Module Def Name]
```

**Examples**:
```bash
# Run tests for all DocTypes in "Accounts" module
bench --site test_site run-tests --module-def Accounts

# Run tests for all DocTypes in "Stock" module
bench --site test_site run-tests --module-def Stock
```

**What it does**:
- Queries the database for all DocTypes in the specified module
- Runs tests for each DocType found
- Creates test records for all DocTypes

**When to use**:
- Testing all DocTypes in a module
- Module-wide test coverage
- Bulk testing after module changes

### Run Tests from a DocType List File

```bash
bench --site [site-name] run-tests --doctype-list-path [path-to-file]
```

**File Format**: Plain text file with one DocType name per line

**Example file** (`erpnext/tests/server/agriculture.txt`):
```
Crop
Fertilizer
Soil Analysis
```

**Command**:
```bash
bench --site test_site run-tests --doctype-list-path erpnext/tests/server/agriculture.txt
```

**When to use**:
- Running tests for a curated list of DocTypes
- Testing related DocTypes together
- CI/CD pipelines with specific test suites

### Run a Specific Test Case Class

```bash
bench --site [site-name] run-tests --case [TestCaseClassName]
```

**Examples**:
```bash
# Run only TestItem class
bench --site test_site run-tests --case TestItem

# Run only TestSalesInvoice class
bench --site test_site run-tests --case TestSalesInvoice
```

**When to use**:
- Testing a specific test class
- Debugging a particular test class
- Running related tests together

### Run Specific Test Methods

```bash
bench --site [site-name] run-tests --test [test-method-name] [--test another-test]
```

**Examples**:
```bash
# Run a single test method
bench --site test_site run-tests --test test_create_document

# Run multiple specific test methods
bench --site test_site run-tests --test test_create_document --test test_update_document

# Combine with app/doctype
bench --site test_site run-tests --app erpnext --doctype Item --test test_item_creation
```

**Test Method Naming**:
- Use the exact method name (without `test_` prefix in some cases)
- Case-sensitive
- Can specify multiple methods with multiple `--test` flags

**When to use**:
- Quick testing of a specific feature
- Debugging a failing test
- Testing a single method during development

---

## Advanced Test Options

### Verbose Output

Get detailed output including print statements and debug information:

```bash
bench --site [site-name] run-tests --verbose
```

**What it shows**:
- Print statements from test code
- Detailed error messages
- Test execution flow
- Database operations (if enabled)

**When to use**:
- Debugging failing tests
- Understanding test execution flow
- Development and troubleshooting

### Fail Fast

Stop test execution on the first failure:

```bash
bench --site [site-name] run-tests --failfast
```

**Behavior**:
- Stops immediately when a test fails
- Does not run remaining tests
- Useful for quick feedback during development

**When to use**:
- Quick iteration during development
- When you want immediate feedback
- CI/CD pipelines where early failure is preferred

**Example**:
```bash
bench --site test_site run-tests --app my_app --failfast
```

### Skip Test Records

Skip automatic creation of test records:

```bash
bench --site [site-name] run-tests --skip-test-records
```

**What it does**:
- Does not create test records from `test_records.json`
- Does not create dependency records
- Tests must create their own data

**When to use**:
- When test records already exist
- Testing record creation logic
- Faster execution when records aren't needed

### Skip Before Tests Hook

Skip the `before_tests` hook execution:

```bash
bench --site [site-name] run-tests --skip-before-tests
```

**What it does**:
- Skips execution of functions registered in `before_tests` hook
- Useful when hooks are causing issues
- Faster execution in some cases

**When to use**:
- Debugging hook-related issues
- When hooks are not needed for specific tests
- Performance optimization

### Profile Tests

Generate performance profiling information:

```bash
bench --site [site-name] run-tests --profile
```

**Output**:
- Shows function call statistics
- Execution time per function
- Cumulative time analysis
- Helps identify performance bottlenecks

**When to use**:
- Performance analysis
- Identifying slow tests
- Optimizing test execution time

**Example Output**:
```
         1234 function calls in 0.123 seconds

   Ordered by: cumulative time

   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
        1    0.000    0.000    0.123    0.123 test_my_doctype.py:10(test_create)
```

### Generate JUnit XML Report

Generate JUnit XML format test report:

```bash
bench --site [site-name] run-tests --junit-xml-output [path/to/report.xml]
```

**Examples**:
```bash
# Generate XML report
bench --site test_site run-tests --junit-xml-output test-results.xml

# With app filter
bench --site test_site run-tests --app erpnext --junit-xml-output erpnext-results.xml
```

**Use Cases**:
- CI/CD integration (Jenkins, GitLab CI, etc.)
- Test reporting tools
- Test result analysis
- Historical test tracking

**XML Format**: Standard JUnit XML format compatible with most CI/CD tools

### Complete Command Examples

```bash
# Run all ERPNext tests with verbose output and fail fast
bench --site test_site run-tests --app erpnext --verbose --failfast

# Run Item tests with coverage
bench --site test_site run-tests --doctype Item --coverage

# Run specific test with profiling
bench --site test_site run-tests --app my_app --test test_complex_calculation --profile

# Run tests and generate XML report for CI
bench --site test_site run-tests --app my_app --junit-xml-output results.xml
```

---

## Parallel Test Execution

Frappe supports running tests in parallel across multiple processes/builds for faster execution.

### Basic Parallel Execution

```bash
bench --site [site-name] run-parallel-tests --app [app-name] --build-number [N] --total-builds [M]
```

**Parameters**:
- `--app`: App to test (default: `frappe`)
- `--build-number`: Current build number (1 to total-builds)
- `--total-builds`: Total number of parallel builds

**Examples**:
```bash
# Run build 1 of 4 parallel builds
bench --site test_site run-parallel-tests --app erpnext --build-number 1 --total-builds 4

# Run build 2 of 4 parallel builds
bench --site test_site run-parallel-tests --app erpnext --build-number 2 --total-builds 4
```

**How it works**:
- Splits test files across builds based on test count
- Each build runs a subset of tests
- Tests are load-balanced by approximate test count

**When to use**:
- CI/CD pipelines with multiple runners
- Large test suites
- Faster overall test execution

### Dry Run (List Tests)

See which tests would run without actually executing them:

```bash
bench --site [site-name] run-parallel-tests --app [app-name] --build-number [N] --total-builds [M] --dry-run
```

**Output**: Lists all test files that would be executed

**When to use**:
- Verifying test distribution
- Planning test execution
- Debugging parallel test configuration

### With Coverage

Generate coverage reports for parallel tests:

```bash
bench --site [site-name] run-parallel-tests --app [app-name] --with-coverage --build-number [N] --total-builds [M]
```

**Note**: Coverage files from multiple builds need to be merged separately

### Using Orchestrator

Use an external orchestrator to balance test execution:

```bash
bench --site [site-name] run-parallel-tests --app [app-name] --use-orchestrator
```

**Requirements**:
- `ORCHESTRATOR_URL` environment variable
- `CI_BUILD_ID` environment variable
- External orchestrator service running

**When to use**:
- Dynamic test distribution
- Better load balancing
- Advanced CI/CD setups

---

## Test Coverage

### Generate Coverage Report

```bash
bench --site [site-name] run-tests --coverage
```

**What it does**:
- Tracks which code is executed during tests
- Generates coverage report
- Shows percentage of code covered

**Output Location**: Coverage files are generated in the site directory

**When to use**:
- Measuring test coverage
- Identifying untested code
- Coverage requirements in CI/CD

### Coverage with Specific Scope

```bash
# Coverage for specific app
bench --site test_site run-tests --app my_app --coverage

# Coverage for specific DocType
bench --site test_site run-tests --doctype Item --coverage

# Coverage for specific test
bench --site test_site run-tests --test test_create_document --coverage
```

### Viewing Coverage Reports

After running with `--coverage`, coverage files are generated. Use coverage tools to view:

```bash
# Install coverage tools (if not already installed)
pip install coverage

# Generate HTML report
coverage html

# View in browser
# Open htmlcov/index.html
```

**Example**:

```bash
# Run tests with coverage
bench --site <site-name> run-tests --app <app-name> --coverage --skip-test-records

# Install coverage tools
pip install coverage

# cd to sites directory because coverage files are generated there
cd /home/frappe/frappe-bench/sites/

# Generate HTML report
coverage html

# View in browser
# Open htmlcov/index.html
```

---

## Troubleshooting

### Tests Are Disabled

**Error**: `Testing is disabled for the site!`

**Solution**:
```bash
bench --site [site-name] set-config allow_tests true
```

### Test File Not Found

**Error**: Test file not discovered

**Check**:
1. File name starts with `test_`
2. File is in correct location
3. File is not in excluded directories
4. Python syntax is correct

### Test Records Not Created

**Symptoms**: Tests fail with "Record not found" errors

**Solutions**:
1. Check `test_records.json` exists and is valid JSON
2. Verify `test_dependencies` is correctly set
3. Run without `--skip-test-records` flag
4. Check for errors in test record creation

### Import Errors

**Error**: `ImportError` or `ModuleNotFoundError`

**Solutions**:
1. Ensure app is installed: `bench install-app [app-name]`
2. Check Python path and imports
3. Verify module structure is correct
4. Clear Python cache: `find . -type d -name __pycache__ -exec rm -r {} +`

### Database Connection Issues

**Error**: Database connection errors

**Solutions**:
1. Verify site is properly configured
2. Check database credentials in `site_config.json`
3. Ensure database server is running
4. Verify site exists: `bench --site [site-name] list-apps`

### Permission Errors

**Error**: Permission denied errors

**Solutions**:
1. Run tests as the correct user
2. Check user permissions in test setup
3. Use `frappe.set_user()` appropriately
4. Verify role assignments

### Slow Test Execution

**Solutions**:
1. Use `--skip-test-records` if records already exist
2. Run tests in parallel
3. Use `--failfast` to stop on first error
4. Profile tests with `--profile` to identify bottlenecks
5. Optimize test data creation

### Tests Pass Locally But Fail in CI

**Common Causes**:
1. Different database state
2. Missing test records
3. Environment variables not set
4. Different Python/Frappe versions
5. Race conditions in parallel execution

**Solutions**:
1. Ensure CI runs `before_tests` hooks
2. Create test records explicitly
3. Set required environment variables
4. Use same Frappe version
5. Add proper test isolation

---

## Command Reference Summary

### Basic Commands

| Command | Description |
|---------|-------------|
| `bench --site [site] run-tests` | Run all tests |
| `bench --site [site] run-tests --app [app]` | Run tests for app |
| `bench --site [site] run-tests --doctype [DocType]` | Run tests for DocType |
| `bench --site [site] run-tests --module [module]` | Run tests for module |

### Options

| Option | Description |
|--------|-------------|
| `--verbose` | Detailed output |
| `--failfast` | Stop on first failure |
| `--coverage` | Generate coverage report |
| `--profile` | Performance profiling |
| `--skip-test-records` | Skip test record creation |
| `--skip-before-tests` | Skip before_tests hooks |
| `--junit-xml-output [path]` | Generate JUnit XML report |
| `--test [method]` | Run specific test method |
| `--case [class]` | Run specific test class |

### Parallel Execution

| Command | Description |
|---------|-------------|
| `bench --site [site] run-parallel-tests --app [app] --build-number [N] --total-builds [M]` | Run parallel tests |
| `--dry-run` | List tests without running |
| `--with-coverage` | Generate coverage |
| `--use-orchestrator` | Use external orchestrator |

---

## Next Steps

Continue to:
- [Part 1: Fundamentals](./63-Frappe_Unit_Testing_Guide_Part_1_Fundamentals.md)
- [Part 3: Test Patterns and Best Practices](./65-Frappe_Unit_Testing_Guide_Part_3_Patterns.md)
- [Part 4: Advanced Testing Techniques](./66-Frappe_Unit_Testing_Guide_Part_4_Advanced.md)
- [Part 5: Test Data Management](./67-Frappe_Unit_Testing_Guide_Part_5_Test_Data.md)
- [Part 6: Test Utilities and Techniques](./68-Frappe_Unit_Testing_Guide_Part_6_Utilities.md)
- [Part 7: Assertions](./69-Frappe_Unit_Testing_Guide_Part_7_Assertions.md)
- [Part 8: Reports](./80-Frappe_Unit_Testing_Guide_Part_8_Reports.md)
- [Part 9: Test Records](./82-Frappe_Unit_Testing_Guide_Part_9_Test_Records.md)
# Frappe Unit Testing Guide - Part 3: Test Patterns and Best Practices

## Table of Contents
1. [Common Test Patterns](#common-test-patterns)
2. [Assertion Methods](#assertion-methods)
3. [Context Managers](#context-managers)
4. [Test Setup and Teardown](#test-setup-and-teardown)
5. [Best Practices](#best-practices)
6. [Anti-Patterns to Avoid](#anti-patterns-to-avoid)
7. [Test Organization](#test-organization)
8. [Real-World Examples](#real-world-examples)

---

## Common Test Patterns

### Pattern 1: Document Lifecycle Testing

Test the complete lifecycle of a document: create, read, update, delete.

```python
import frappe
from frappe.tests.utils import FrappeTestCase

class TestMyDocType(FrappeTestCase):
    def test_document_lifecycle(self):
        # Create
        doc = frappe.get_doc({
            "doctype": "MyDocType",
            "field1": "value1"
        })
        doc.insert()
        doc_name = doc.name
        
        # Read
        doc = frappe.get_doc("MyDocType", doc_name)
        self.assertEqual(doc.field1, "value1")
        
        # Update
        doc.field1 = "updated_value"
        doc.save()
        doc.reload()
        self.assertEqual(doc.field1, "updated_value")
        
        # Delete
        frappe.delete_doc("MyDocType", doc_name)
        self.assertFalse(frappe.db.exists("MyDocType", doc_name))
```

### Pattern 2: Validation Testing

Test all validation rules and constraints.

```python
def test_required_field_validation(self):
    """Test that required fields are enforced"""
    doc = frappe.get_doc({
        "doctype": "MyDocType",
        # Missing required field 'field1'
    })
    
    with self.assertRaises(frappe.ValidationError) as cm:
        doc.insert()
    
    self.assertIn("field1", str(cm.exception))

def test_field_validation(self):
    """Test field-level validation"""
    doc = frappe.get_doc({
        "doctype": "MyDocType",
        "field1": "valid_value",
        "email_field": "invalid-email"  # Invalid email format
    })
    
    with self.assertRaises(frappe.ValidationError):
        doc.insert()

def test_custom_validation(self):
    """Test custom validate() method"""
    doc = frappe.get_doc({
        "doctype": "MyDocType",
        "field1": "value1",
        "field2": "invalid_combination"
    })
    
    with self.assertRaises(frappe.ValidationError):
        doc.validate()

def test_date_range_validation(self):
    """Test date range validation"""
    doc = frappe.get_doc({
        "doctype": "MyDocType",
        "start_date": "2024-01-01",
        "end_date": "2024-01-31"
    })
    doc.insert()
    
    # Test invalid date range
    doc.end_date = "2023-12-31"  # Before start_date
    with self.assertRaises(frappe.exceptions.InvalidDates):
        doc.validate_from_to_dates("start_date", "end_date")
```

### Pattern 3: Permission Testing

Test role-based access control and permissions.

```python
def test_read_permission(self):
    """Test read permission for different roles"""
    # Create document as Administrator
    doc = frappe.get_doc({
        "doctype": "MyDocType",
        "field1": "value1"
    })
    doc.insert()
    
    # Test as regular user
    with self.set_user("test@example.com"):
        doc = frappe.get_doc("MyDocType", doc.name)
        self.assertTrue(doc.has_permission("read"))
        self.assertFalse(doc.has_permission("write"))

def test_permission_restriction(self):
    """Test that users without permission cannot access"""
    doc = frappe.get_doc({
        "doctype": "MyDocType",
        "field1": "value1"
    })
    doc.insert()
    
    with self.set_user("restricted_user@example.com"):
        with self.assertRaises(frappe.PermissionError):
            frappe.get_doc("MyDocType", doc.name)

def test_submit_permission(self):
    """Test submit permission"""
    doc = frappe.get_doc({
        "doctype": "MyDocType",
        "field1": "value1"
    })
    doc.insert()
    
    with self.set_user("test@example.com"):
        doc = frappe.get_doc("MyDocType", doc.name)
        if doc.has_permission("submit"):
            doc.submit()
            self.assertEqual(doc.docstatus, 1)
        else:
            with self.assertRaises(frappe.PermissionError):
                doc.submit()

def test_user_permissions_in_list(self):
    """Test user permissions affect list queries"""
    # Create documents
    doc1 = frappe.get_doc({"doctype": "MyDocType", "field1": "value1"}).insert()
    doc2 = frappe.get_doc({"doctype": "MyDocType", "field1": "value2"}).insert()
    
    # Add user permission for doc1 only
    frappe.permissions.add_user_permission("MyDocType", doc1.name, "test@example.com")
    
    with self.set_user("test@example.com"):
        names = [d.name for d in frappe.get_list("MyDocType", fields=["name"])]
        self.assertIn(doc1.name, names)
        self.assertNotIn(doc2.name, names)
```

### Pattern 4: Workflow Testing

Test document workflows and state transitions.

```python
def test_workflow_transitions(self):
    """Test workflow state transitions"""
    doc = frappe.get_doc({
        "doctype": "MyDocType",
        "field1": "value1",
        "workflow_state": "Draft"
    })
    doc.insert()
    
    # Transition to Submitted
    doc.workflow_state = "Submitted"
    doc.save()
    self.assertEqual(doc.workflow_state, "Submitted")
    
    # Test invalid transition
    doc.workflow_state = "Cancelled"
    with self.assertRaises(frappe.ValidationError):
        doc.save()  # Cannot transition directly from Submitted to Cancelled

def test_submit_and_cancel(self):
    """Test document submission and cancellation"""
    doc = frappe.get_doc({
        "doctype": "MyDocType",
        "field1": "value1"
    })
    doc.insert()
    
    # Submit
    doc.submit()
    self.assertEqual(doc.docstatus, 1)
    
    # Verify cannot update after submit
    doc.field1 = "new_value"
    with self.assertRaises(frappe.UpdateAfterSubmitError):
        doc.save()
    
    # Cancel
    doc.cancel()
    self.assertEqual(doc.docstatus, 2)
```

### Pattern 5: Child Table Testing

Test child tables and related documents.

```python
def test_child_table_operations(self):
    """Test operations on child tables"""
    doc = frappe.get_doc({
        "doctype": "MyDocType",
        "field1": "value1",
        "child_table": [
            {
                "child_field1": "value1",
                "child_field2": "value2"
            },
            {
                "child_field1": "value3",
                "child_field2": "value4"
            }
        ]
    })
    doc.insert()
    
    # Verify child records
    self.assertEqual(len(doc.child_table), 2)
    self.assertEqual(doc.child_table[0].child_field1, "value1")
    
    # Add child record
    doc.append("child_table", {
        "child_field1": "value5",
        "child_field2": "value6"
    })
    doc.save()
    self.assertEqual(len(doc.child_table), 3)
    
    # Remove child record
    doc.remove(doc.child_table[0])
    doc.save()
    self.assertEqual(len(doc.child_table), 2)

def test_child_table_defaults(self):
    """Test default values in child tables"""
    doc = frappe.get_doc({
        "doctype": "MyDocType",
        "child_table": [{}]  # Empty child row
    })
    doc.insert()
    
    # Verify default value is applied
    self.assertEqual(doc.child_table[0].some_fieldname, "default_value")
```

### Pattern 6: Calculation Testing

Test calculated fields and formulas.

```python
def test_calculated_field(self):
    """Test automatic calculation of fields"""
    doc = frappe.get_doc({
        "doctype": "MyDocType",
        "quantity": 10,
        "rate": 100
    })
    doc.insert()
    
    # Verify calculated field
    self.assertEqual(doc.amount, 1000)  # quantity * rate
    
    # Update and verify recalculation
    doc.quantity = 20
    doc.save()
    doc.reload()
    self.assertEqual(doc.amount, 2000)

def test_formula_field(self):
    """Test formula field calculations"""
    doc = frappe.get_doc({
        "doctype": "MyDocType",
        "field1": 100,
        "field2": 50
    })
    doc.insert()
    
    # Formula: field1 + field2
    self.assertEqual(doc.calculated_field, 150)

def test_child_table_calculations(self):
    """Test calculations across child tables"""
    doc = frappe.get_doc({
        "doctype": "Invoice",
        "items": [
            {"quantity": 2, "rate": 100},  # Amount: 200
            {"quantity": 3, "rate": 50}    # Amount: 150
        ]
    })
    doc.insert()
    
    # Total should be sum of all item amounts
    self.assertEqual(doc.total, 350)
```

### Pattern 7: Link Field Testing

Test link fields and related document references.

```python
def test_link_field_validation(self):
    """Test link field validation"""
    # Create linked document
    linked_doc = frappe.get_doc({
        "doctype": "LinkedDocType",
        "field1": "value1"
    })
    linked_doc.insert()
    
    # Create document with link
    doc = frappe.get_doc({
        "doctype": "MyDocType",
        "linked_field": linked_doc.name
    })
    doc.insert()
    
    self.assertEqual(doc.linked_field, linked_doc.name)
    
    # Test invalid link
    doc.linked_field = "NonExistent"
    with self.assertRaises(frappe.ValidationError):
        doc.save()

def test_dynamic_link(self):
    """Test dynamic link fields"""
    # Create documents of different types
    doc1 = frappe.get_doc({
        "doctype": "DocType1",
        "name": "test1"
    })
    doc1.insert()
    
    # Create document with dynamic link
    doc = frappe.get_doc({
        "doctype": "MyDocType",
        "link_doctype": "DocType1",
        "link_name": "test1"
    })
    doc.insert()
    
    self.assertEqual(doc.link_name, "test1")
```

### Pattern 8: Date and Time Testing

Test date/time fields and time-based logic.

```python
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate, getdate

def test_date_validation(self):
    """Test date field validation"""
    doc = frappe.get_doc({
        "doctype": "MyDocType",
        "start_date": "2024-01-01",
        "end_date": "2024-01-31"
    })
    doc.insert()
    
    # Test invalid date range
    doc.end_date = "2023-12-31"  # Before start_date
    with self.assertRaises(frappe.ValidationError):
        doc.save()

def test_time_based_logic(self):
    """Test time-based business logic"""
    with self.freeze_time("2024-01-15"):
        doc = frappe.get_doc({
            "doctype": "MyDocType",
            "date_field": nowdate()
        })
        doc.insert()
        
        # Verify date is frozen
        self.assertEqual(str(doc.date_field), "2024-01-15")

def test_date_comparisons(self):
    """Test date comparisons and calculations"""
    with self.freeze_time("2024-01-15"):
        doc = frappe.get_doc({
            "doctype": "MyDocType",
            "start_date": nowdate(),
            "end_date": add_days(nowdate(), 30)
        })
        doc.insert()
        
        # Verify date calculations
        self.assertEqual(
            (getdate(doc.end_date) - getdate(doc.start_date)).days,
            30
        )
```

### Pattern 9: Error Handling Testing

Test error handling and exception scenarios.

```python
def test_duplicate_validation(self):
    """Test duplicate prevention"""
    doc1 = frappe.get_doc({
        "doctype": "MyDocType",
        "unique_field": "unique_value"
    })
    doc1.insert()
    
    # Try to create duplicate
    doc2 = frappe.get_doc({
        "doctype": "MyDocType",
        "unique_field": "unique_value"
    })
    
    with self.assertRaises(frappe.DuplicateEntryError):
        doc2.insert()

def test_mandatory_field_error(self):
    """Test mandatory field error messages"""
    doc = frappe.get_doc({
        "doctype": "MyDocType",
        # Missing mandatory field
    })
    
    with self.assertRaises(frappe.MandatoryError) as cm:
        doc.insert()
    
    error_message = str(cm.exception)
    self.assertIn("mandatory", error_message.lower())

def test_character_length_validation(self):
    """Test character length limits"""
    doc = frappe.get_doc({
        "doctype": "MyDocType",
        "field1": "a" * 1000  # Exceeds varchar limit
    })
    
    with self.assertRaises(frappe.CharacterLengthExceededError):
        doc.insert()

def test_non_negative_validation(self):
    """Test non-negative number validation"""
    doc = frappe.get_doc({
        "doctype": "MyDocType",
        "quantity": -1  # Negative value
    })
    
    with self.assertRaises(frappe.NonNegativeError):
        doc.insert()

def test_does_not_exist_error(self):
    """Test error when trying to save new doc with existing name"""
    doc = frappe.get_doc({
        "doctype": "ToDo",
        "description": "test",
        "name": "existing-name"  # Trying to set name on new doc
    })
    
    with self.assertRaises(frappe.DoesNotExistError):
        doc.save()
```

### Pattern 10: API Testing

Test API endpoints and responses.

```python
from frappe.tests.test_api import FrappeAPITestCase

class TestMyAPI(FrappeAPITestCase):
    version = "v1"
    
    def test_get_resource(self):
        """Test GET API endpoint"""
        # Create test document
        doc = frappe.get_doc({
            "doctype": "MyDocType",
            "field1": "value1"
        })
        doc.insert()
        
        # Test GET request
        response = self.get(self.resource("MyDocType", doc.name))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["data"]["field1"], "value1")
    
    def test_create_resource(self):
        """Test POST API endpoint"""
        data = {
            "doctype": "MyDocType",
            "field1": "value1"
        }
        
        response = self.post(self.resource("MyDocType"), data)
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.json["data"]["name"])
    
    def test_update_resource(self):
        """Test PUT API endpoint"""
        doc = frappe.get_doc({
            "doctype": "MyDocType",
            "field1": "old_value"
        })
        doc.insert()
        
        data = {"field1": "new_value"}
        response = self.put(self.resource("MyDocType", doc.name), data)
        self.assertEqual(response.status_code, 200)
        
        # Verify update
        doc.reload()
        self.assertEqual(doc.field1, "new_value")
    
    def test_delete_resource(self):
        """Test DELETE API endpoint"""
        doc = frappe.get_doc({
            "doctype": "MyDocType",
            "field1": "value1"
        })
        doc.insert()
        
        response = self.delete(self.resource("MyDocType", doc.name))
        self.assertEqual(response.status_code, 202)
        
        # Verify deletion
        response = self.get(self.resource("MyDocType", doc.name))
        self.assertEqual(response.status_code, 404)
    
    def test_api_method(self):
        """Test API method endpoint"""
        response = self.get(self.method("frappe.auth.get_logged_user"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["message"], "Administrator")
    
    def test_api_authentication(self):
        """Test API authentication"""
        # Test with valid credentials
        # (Setup API key and secret)
        response = self.get(self.method("frappe.auth.get_logged_user"))
        self.assertEqual(response.status_code, 200)
        
        # Test with invalid credentials
        # (Modify authorization token)
        response = self.get(self.method("frappe.auth.get_logged_user"))
        self.assertEqual(response.status_code, 401)
```

### Pattern 11: Database Query Testing

Test database queries and query optimization.

```python
def test_db_get_value(self):
    """Test database get_value operations"""
    doc = frappe.get_doc({
        "doctype": "MyDocType",
        "field1": "value1"
    })
    doc.insert()
    
    # Test various get_value operations
    value = frappe.db.get_value("MyDocType", doc.name, "field1")
    self.assertEqual(value, "value1")
    
    # Test with filters
    value = frappe.db.get_value("MyDocType", {"field1": "value1"})
    self.assertEqual(value, doc.name)
    
    # Test with operators
    value = frappe.db.get_value("MyDocType", {"field1": ["like", "val%"]})
    self.assertEqual(value, doc.name)

def test_query_optimization(self):
    """Test query count optimization"""
    with self.assertQueryCount(5):  # Maximum 5 queries
        # Your code that should be optimized
        docs = frappe.get_all("MyDocType", limit=10)
        for doc in docs:
            frappe.get_doc("MyDocType", doc.name)

def test_db_set_value(self):
    """Test direct database updates"""
    doc = frappe.get_doc({
        "doctype": "MyDocType",
        "field1": "value1"
    })
    doc.insert()
    
    # Update directly in database
    frappe.db.set_value("MyDocType", doc.name, "field1", "new_value")
    
    # Verify update
    value = frappe.db.get_value("MyDocType", doc.name, "field1")
    self.assertEqual(value, "new_value")
```

### Pattern 12: Document Methods Testing

Test custom document methods and hooks.

```python
def test_document_methods(self):
    """Test custom document methods"""
    doc = frappe.get_doc({
        "doctype": "MyDocType",
        "field1": "value1"
    })
    doc.insert()
    
    # Test custom method
    result = doc.my_custom_method()
    self.assertEqual(result, expected_value)
    
    # Test run_method
    result = doc.run_method("my_custom_method")
    self.assertEqual(result, expected_value)

def test_document_hooks(self):
    """Test document event hooks"""
    doc = frappe.get_doc({
        "doctype": "MyDocType",
        "field1": "value1"
    })
    
    # Test before_insert hook
    doc.insert()  # Should trigger before_insert
    
    # Test on_update hook
    doc.field1 = "new_value"
    doc.save()  # Should trigger on_update
    
    # Test before_submit hook
    doc.submit()  # Should trigger before_submit
```

### Pattern 13: Naming Series Testing

Test naming series and autoname functionality.

```python
def test_naming_series(self):
    """Test naming series generation"""
    doc = frappe.get_doc({
        "doctype": "MyDocType",
        "naming_series": "TEST-"
    })
    doc.insert()
    
    # Verify name follows naming series
    self.assertTrue(doc.name.startswith("TEST-"))
    
    # Test naming series reversion
    from frappe.model.naming import revert_series_if_last
    revert_series_if_last("TEST-", doc.name)
    
    # Verify series was reverted
    # (Check Series table)

def test_autoname(self):
    """Test autoname functionality"""
    doc = frappe.get_doc({
        "doctype": "MyDocType",
        "field1": "value1"
    })
    doc.insert()
    
    # Verify autoname was applied
    self.assertIsNotNone(doc.name)
    self.assertNotEqual(doc.name, "")
```

### Pattern 14: Formatted Values Testing

Test formatted field values and display.

```python
def test_get_formatted(self):
    """Test formatted field values"""
    doc = frappe.get_doc({
        "doctype": "MyDocType",
        "currency_field": 100000
    })
    doc.insert()
    
    # Test currency formatting
    formatted = doc.get_formatted("currency_field", currency="USD")
    self.assertIn("100,000", formatted)
    
    # Test date formatting
    formatted = doc.get_formatted("date_field")
    self.assertIsInstance(formatted, str)
```

---

## Assertion Methods

### Standard Assertions

FrappeTestCase inherits all standard unittest assertions:

```python
# Equality
self.assertEqual(a, b)
self.assertNotEqual(a, b)

# Truthiness
self.assertTrue(x)
self.assertFalse(x)

# None
self.assertIsNone(x)
self.assertIsNotNone(x)

# Type
self.assertIsInstance(obj, Class)
self.assertNotIsInstance(obj, Class)

# Containment
self.assertIn(item, container)
self.assertNotIn(item, container)

# Exceptions
self.assertRaises(Exception, function, *args)
with self.assertRaises(Exception) as cm:
    function()
    self.assertIn("error message", str(cm.exception))

# Comparison
self.assertGreater(a, b)
self.assertGreaterEqual(a, b)
self.assertLess(a, b)
self.assertLessEqual(a, b)

# Almost equal (for floats)
self.assertAlmostEqual(a, b, places=2)
```

### Frappe-Specific Assertions

#### assertDocumentEqual

Compare documents field by field:

```python
def test_document_comparison(self):
    expected = {
        "doctype": "MyDocType",
        "field1": "value1",
        "field2": 100
    }
    
    actual = frappe.get_doc("MyDocType", "test-doc")
    
    self.assertDocumentEqual(expected, actual)
```

**Features**:
- Handles nested child tables
- Compares float values with precision
- Handles datetime comparisons
- Recursive comparison for child documents

#### assertSequenceSubset

Check if one sequence is a subset of another:

```python
def test_subset(self):
    larger = ["a", "b", "c", "d"]
    smaller = ["a", "c"]
    
    self.assertSequenceSubset(larger, smaller)  # Passes
```

#### assertQueryEqual

Compare SQL queries (normalized):

```python
def test_query(self):
    query1 = "SELECT * FROM `tabUser` WHERE name = 'Admin'"
    query2 = "select * from tabUser where name='Admin'"
    
    self.assertQueryEqual(query1, query2)  # Passes after normalization
```

**Normalization**:
- Uppercase keywords
- Consistent indentation
- Removed comments
- Standardized whitespace

---

## Context Managers

### set_user

Temporarily switch user context:

```python
def test_user_context(self):
    with self.set_user("test@example.com"):
        # All operations run as test@example.com
        doc = frappe.get_doc("MyDocType", "test-doc")
        # User is automatically restored after context
```

**Use Cases**:
- Testing permissions
- Testing user-specific behavior
- Testing role-based access

### switch_site

Switch to a different site:

```python
def test_multi_site(self):
    with self.switch_site("other_site"):
        # Operations run on other_site
        doc = frappe.get_doc("MyDocType", "test-doc")
        # Site is automatically restored after context
```

**Use Cases**:
- Multi-site testing
- Site-specific configurations
- Cross-site operations

### freeze_time

Freeze time for time-based tests:

```python
def test_time_freeze(self):
    with self.freeze_time("2024-01-15 10:00:00"):
        # All datetime operations use frozen time
        doc = frappe.get_doc({
            "doctype": "MyDocType",
            "date_field": frappe.utils.nowdate()
        })
        # date_field will be 2024-01-15
```

**Use Cases**:
- Testing time-based logic
- Testing scheduled tasks
- Testing date calculations
- Testing expiration logic

### primary_connection / secondary_connection

Simulate multiple database connections (for concurrency testing):

```python
def test_concurrent_access(self):
    # Primary connection
    with self.primary_connection():
        doc1 = frappe.get_doc("MyDocType", "test-doc")
        doc1.field1 = "value1"
        doc1.save()
    
    # Secondary connection (simulates another user)
    with self.secondary_connection():
        doc2 = frappe.get_doc("MyDocType", "test-doc")
        # May see different state
        doc2.field1 = "value2"
        doc2.save()
    
    # Both connections are rolled back after test
```

**Use Cases**:
- Testing concurrent access
- Testing race conditions
- Testing transaction isolation
- Testing locking mechanisms

### assertQueryCount

Assert maximum number of SQL queries:

```python
def test_query_optimization(self):
    with self.assertQueryCount(5):  # Maximum 5 queries allowed
        # Your code that should be optimized
        docs = frappe.get_all("MyDocType", limit=10)
        for doc in docs:
            frappe.get_doc("MyDocType", doc.name)
```

**Use Cases**:
- Performance testing
- Query optimization verification
- N+1 query detection
- Database efficiency testing

### assertRedisCallCounts

Assert maximum number of Redis calls:

```python
def test_cache_optimization(self):
    with self.assertRedisCallCounts(3):  # Maximum 3 Redis calls
        # Your code that uses cache
        frappe.cache().get_value("key1")
        frappe.cache().get_value("key2")
        frappe.cache().set_value("key3", "value")
```

**Use Cases**:
- Cache optimization
- Redis performance testing
- Cache efficiency verification

### assertRowsRead

Assert maximum number of rows read:

```python
def test_data_access(self):
    with self.assertRowsRead(100):  # Maximum 100 rows
        # Your code that reads data
        frappe.get_all("MyDocType", limit=100)
```

**Use Cases**:
- Data access optimization
- Query result size verification
- Performance testing

---

## Test Setup and Teardown

### setUp and tearDown

Run before and after each test method:

```python
class TestMyDocType(FrappeTestCase):
    def setUp(self):
        """Run before each test method"""
        super().setUp()
        # Create common test data
        self.test_doc = frappe.get_doc({
            "doctype": "MyDocType",
            "field1": "test_value"
        })
        self.test_doc.insert()
    
    def tearDown(self):
        """Run after each test method"""
        # Cleanup (usually not needed due to auto-rollback)
        super().tearDown()
    
    def test_something(self):
        # self.test_doc is available here
        self.assertEqual(self.test_doc.field1, "test_value")
```

**Important**: Always call `super().setUp()` and `super().tearDown()`.

### setUpClass and tearDownClass

Run once before/after all test methods in the class:

```python
class TestMyDocType(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        """Run once before all test methods"""
        super().setUpClass()  # IMPORTANT: Always call super()
        
        # Create shared test data
        cls.shared_doc = frappe.get_doc({
            "doctype": "MyDocType",
            "field1": "shared_value"
        })
        cls.shared_doc.insert()
        frappe.db.commit()  # Commit if needed across tests
    
    @classmethod
    def tearDownClass(cls):
        """Run once after all test methods"""
        # Cleanup shared resources
        super().tearDownClass()
    
    def test_one(self):
        # cls.shared_doc is available
        pass
    
    def test_two(self):
        # cls.shared_doc is available
        pass
```

**Important Notes**:
- Always call `super().setUpClass()` first
- Database changes in `setUpClass` may need explicit commit
- Use class variables (`cls.`) for shared data
- `tearDownClass` runs even if tests fail

### When to Use setUp vs setUpClass

**Use `setUp`** when:
- Each test needs fresh data
- Tests modify shared data
- Data is test-specific

**Use `setUpClass`** when:
- Data is expensive to create
- Data is read-only across tests
- Performance is critical

---

## Best Practices

### 1. Test Naming

**Good**:
```python
def test_create_document_with_required_fields(self):
    pass

def test_validation_prevents_duplicate_entries(self):
    pass

def test_user_without_permission_cannot_access(self):
    pass

def test_calculate_total_includes_all_items(self):
    pass
```

**Bad**:
```python
def test1(self):
    pass

def test_thing(self):
    pass

def test_it(self):
    pass

def test(self):
    pass
```

**Guidelines**:
- Use descriptive names that explain what is being tested
- Follow pattern: `test_[what]_[condition]_[expected_result]`
- Use underscores, not camelCase
- Be specific about the scenario

### 2. One Assertion Per Concept

**Good**:
```python
def test_document_creation(self):
    doc = create_document()
    self.assertIsNotNone(doc.name)
    self.assertEqual(doc.status, "Draft")
    self.assertTrue(doc.is_new())
```

**Bad**:
```python
def test_everything(self):
    doc = create_document()
    # Too many unrelated assertions
    self.assertIsNotNone(doc.name)
    self.assertEqual(doc.status, "Draft")
    self.assertTrue(doc.is_new())
    # ... 20 more unrelated assertions
```

**Guidelines**:
- Group related assertions together
- Split unrelated assertions into separate tests
- Each test should verify one concept or behavior

### 3. Use Descriptive Test Data

**Good**:
```python
def test_calculate_total(self):
    doc = frappe.get_doc({
        "doctype": "Invoice",
        "items": [
            {"quantity": 2, "rate": 100},  # Total: 200
            {"quantity": 3, "rate": 50}     # Total: 150
        ]
    })
    # Expected total: 350
    self.assertEqual(doc.total, 350)
```

**Bad**:
```python
def test_calculate_total(self):
    doc = frappe.get_doc({
        "doctype": "Invoice",
        "items": [
            {"quantity": 1, "rate": 1},
            {"quantity": 1, "rate": 1}
        ]
    })
    # Not clear what the expected result should be
    self.assertEqual(doc.total, 2)
```

**Guidelines**:
- Use meaningful test data
- Add comments explaining expected results
- Make calculations obvious
- Use realistic values

### 4. Test Edge Cases

```python
def test_empty_values(self):
    """Test handling of empty/None values"""
    doc = frappe.get_doc({
        "doctype": "MyDocType",
        "field1": None,
        "field2": ""
    })
    # Should handle gracefully
    doc.insert()
    self.assertIsNone(doc.field1)

def test_boundary_values(self):
    """Test min/max values"""
    # Test minimum value
    doc = frappe.get_doc({
        "doctype": "MyDocType",
        "quantity": 0
    })
    doc.insert()
    
    # Test maximum value
    doc = frappe.get_doc({
        "doctype": "MyDocType",
        "quantity": 999999
    })
    doc.insert()

def test_special_characters(self):
    """Test special characters in strings"""
    doc = frappe.get_doc({
        "doctype": "MyDocType",
        "field1": "Test & <Special> 'Characters' \"Quotes\""
    })
    doc.insert()
    # Should escape properly
    self.assertIn("&", doc.field1)

def test_very_large_numbers(self):
    """Test handling of large numbers"""
    doc = frappe.get_doc({
        "doctype": "MyDocType",
        "amount": 999999999999.99
    })
    doc.insert()
    self.assertEqual(doc.amount, 999999999999.99)
```

### 5. Isolate Tests

Each test should be independent:

```python
# Good: Each test is independent
def test_create(self):
    doc = create_document()
    self.assertIsNotNone(doc.name)

def test_update(self):
    doc = create_document()
    doc.field1 = "new_value"
    doc.save()
    self.assertEqual(doc.field1, "new_value")

# Bad: Tests depend on each other
def test_create(self):
    self.doc = create_document()

def test_update(self):
    # Depends on test_create running first
    self.doc.field1 = "new_value"
    self.doc.save()
```

**Guidelines**:
- Each test should be able to run independently
- Don't rely on test execution order
- Create fresh data in each test if needed
- Use `setUp` for common setup, not shared state

### 6. Use setUp for Common Setup

```python
class TestMyDocType(FrappeTestCase):
    def setUp(self):
        super().setUp()
        # Common setup for all tests
        self.base_doc = frappe.get_doc({
            "doctype": "MyDocType",
            "field1": "base_value"
        })
        self.base_doc.insert()
    
    def test_scenario_one(self):
        # Use self.base_doc
        self.assertEqual(self.base_doc.field1, "base_value")
    
    def test_scenario_two(self):
        # Use self.base_doc (fresh instance each time)
        doc = frappe.get_doc("MyDocType", self.base_doc.name)
        self.assertIsNotNone(doc)
```

### 7. Clean Up After Tests

```python
def test_with_cleanup(self):
    # Create temporary data
    temp_doc = frappe.get_doc({
        "doctype": "TempDocType",
        "field1": "temp"
    })
    temp_doc.insert()
    
    try:
        # Test logic
        result = perform_operation(temp_doc)
        self.assertEqual(result, expected)
    finally:
        # Cleanup (though auto-rollback usually handles this)
        if frappe.db.exists("TempDocType", temp_doc.name):
            frappe.delete_doc("TempDocType", temp_doc.name, force=1)
```

**Note**: Frappe automatically rolls back database changes after each test, so explicit cleanup is usually not needed. However, cleanup may be needed for:
- External resources (files, network connections)
- Cache entries
- Temporary settings

### 8. Test Error Messages

```python
def test_error_message(self):
    with self.assertRaises(frappe.ValidationError) as cm:
        invalid_operation()
    
    error_message = str(cm.exception)
    self.assertIn("expected error text", error_message)
    self.assertIn("field1", error_message.lower())
```

**Guidelines**:
- Verify error messages are helpful
- Check that error messages mention relevant fields
- Ensure error messages are user-friendly

### 9. Use Constants for Test Data

```python
class TestMyDocType(FrappeTestCase):
    TEST_FIELD1 = "test_value_1"
    TEST_FIELD2 = "test_value_2"
    TEST_EMAIL = "test@example.com"
    
    def test_something(self):
        doc = frappe.get_doc({
            "doctype": "MyDocType",
            "field1": self.TEST_FIELD1,
            "field2": self.TEST_FIELD2
        })
        # ...
```

**Benefits**:
- Easy to update test data
- Consistent across tests
- Clear what values are being tested

### 10. Document Complex Tests

```python
def test_complex_calculation(self):
    """
    Test the complex calculation logic:
    1. Base amount is calculated from items
    2. Discount is applied if total > 1000
    3. Tax is calculated on discounted amount
    4. Final amount = discounted amount + tax
    
    Test case: 3 items with total 1500
    - Base: 1500
    - Discount (10%): 150
    - Discounted: 1350
    - Tax (5%): 67.50
    - Final: 1417.50
    """
    doc = frappe.get_doc({
        "doctype": "Invoice",
        "items": [
            {"quantity": 5, "rate": 200},  # 1000
            {"quantity": 2, "rate": 150},  # 300
            {"quantity": 1, "rate": 200}   # 200
        ]
    })
    doc.insert()
    
    self.assertEqual(doc.total, 1500)
    self.assertEqual(doc.discount_amount, 150)
    self.assertEqual(doc.final_amount, 1417.50)
```

### 11. Test Both Positive and Negative Cases

```python
def test_valid_email(self):
    """Test that valid emails are accepted"""
    doc = frappe.get_doc({
        "doctype": "MyDocType",
        "email": "valid@example.com"
    })
    doc.insert()
    self.assertEqual(doc.email, "valid@example.com")

def test_invalid_email(self):
    """Test that invalid emails are rejected"""
    doc = frappe.get_doc({
        "doctype": "MyDocType",
        "email": "invalid-email"
    })
    with self.assertRaises(frappe.ValidationError):
        doc.insert()
```

### 12. Use Helper Methods

```python
class TestMyDocType(FrappeTestCase):
    def create_test_document(self, **kwargs):
        """Helper to create test document"""
        defaults = {
            "doctype": "MyDocType",
            "field1": "default_value"
        }
        defaults.update(kwargs)
        doc = frappe.get_doc(defaults)
        doc.insert()
        return doc
    
    def create_test_user(self, email="test@example.com", roles=None):
        """Helper to create test user"""
        if not frappe.db.exists("User", email):
            user = frappe.get_doc({
                "doctype": "User",
                "email": email,
                "first_name": "Test",
                "roles": roles or []
            })
            user.insert()
        return frappe.get_doc("User", email)
    
    def test_scenario_one(self):
        doc = self.create_test_document(field1="custom_value")
        # Test logic
    
    def test_scenario_two(self):
        user = self.create_test_user(roles=[{"role": "System Manager"}])
        with self.set_user(user.email):
            # Test logic
```

---

## Anti-Patterns to Avoid

### 1. Testing Implementation Details

**Bad**:
```python
def test_internal_variable(self):
    doc = create_document()
    # Testing internal implementation
    self.assertEqual(doc._internal_cache, {...})
    self.assertEqual(doc._meta, {...})
```

**Good**:
```python
def test_behavior(self):
    doc = create_document()
    # Testing behavior/outcome
    self.assertEqual(doc.calculated_field, expected_value)
    self.assertTrue(doc.is_valid())
```

**Why**: Tests should verify behavior, not implementation. Implementation can change without breaking behavior.

### 2. Over-Mocking

**Bad**:
```python
@patch('frappe.get_doc')
@patch('frappe.db.get_value')
@patch('frappe.cache')
@patch('frappe.get_list')
def test_something(self, mock_list, mock_cache, mock_db, mock_get_doc):
    # Too many mocks, not testing real behavior
    mock_get_doc.return_value = mock_doc
    # ...
```

**Good**:
```python
def test_something(self):
    # Use real Frappe functions
    doc = frappe.get_doc("MyDocType", "test-doc")
    # Test actual behavior
    result = doc.calculate_something()
    self.assertEqual(result, expected)
```

**Why**: Over-mocking makes tests brittle and doesn't verify real integration.

### 3. Testing Framework Code

**Bad**:
```python
def test_frappe_get_doc(self):
    # Testing Frappe framework itself
    doc = frappe.get_doc("User", "Administrator")
    self.assertIsNotNone(doc)
```

**Good**:
```python
def test_my_business_logic(self):
    # Testing your business logic using Frappe
    doc = create_my_document()
    result = my_business_function(doc)
    self.assertEqual(result, expected)
```

**Why**: Frappe framework is already tested. Test your application code.

### 4. Slow Tests

**Bad**:
```python
def test_slow_operation(self):
    # Unnecessary sleep or delays
    import time
    time.sleep(5)
    # ...
```

**Good**:
```python
def test_operation(self):
    # Use freeze_time for time-based tests
    with self.freeze_time("2024-01-15"):
        # Test time-based logic
        result = time_based_function()
        self.assertEqual(result, expected)
```

**Why**: Slow tests reduce developer productivity and CI/CD efficiency.

### 5. Non-Deterministic Tests

**Bad**:
```python
def test_random(self):
    import random
    value = random.randint(1, 100)
    # Test depends on random value
    self.assertGreater(value, 0)
```

**Good**:
```python
def test_with_fixed_value(self):
    value = 50  # Fixed test value
    result = process_value(value)
    self.assertEqual(result, expected)
    
def test_with_seed(self):
    import random
    random.seed(42)  # Fixed seed for reproducibility
    value = random.randint(1, 100)
    # Now deterministic
```

**Why**: Non-deterministic tests are unreliable and hard to debug.

### 6. Testing Multiple Things in One Test

**Bad**:
```python
def test_everything(self):
    # Testing creation
    doc = create_document()
    self.assertIsNotNone(doc.name)
    
    # Testing update
    doc.field1 = "new"
    doc.save()
    self.assertEqual(doc.field1, "new")
    
    # Testing delete
    frappe.delete_doc("MyDocType", doc.name)
    self.assertFalse(frappe.db.exists("MyDocType", doc.name))
```

**Good**:
```python
def test_create_document(self):
    doc = create_document()
    self.assertIsNotNone(doc.name)

def test_update_document(self):
    doc = create_document()
    doc.field1 = "new"
    doc.save()
    self.assertEqual(doc.field1, "new")

def test_delete_document(self):
    doc = create_document()
    frappe.delete_doc("MyDocType", doc.name)
    self.assertFalse(frappe.db.exists("MyDocType", doc.name))
```

**Why**: Focused tests are easier to understand, debug, and maintain.

### 7. Ignoring Test Failures

**Bad**:
```python
def test_something(self):
    try:
        operation()
    except Exception:
        pass  # Ignoring failures
    # Test always passes
```

**Good**:
```python
def test_something(self):
    # Let exceptions propagate
    result = operation()
    self.assertEqual(result, expected)
```

**Why**: Tests should fail when something is wrong.

### 8. Hard-Coding Test Data

**Bad**:
```python
def test_calculation(self):
    # Hard-coded values
    doc = frappe.get_doc("Invoice", "INV-00001")
    # Assumes document exists
```

**Good**:
```python
def test_calculation(self):
    # Create test data
    doc = frappe.get_doc({
        "doctype": "Invoice",
        "items": [{"quantity": 2, "rate": 100}]
    })
    doc.insert()
    # Test with known data
```

**Why**: Tests should be self-contained and not depend on external data.

---

## Test Organization

### Group Related Tests

```python
class TestMyDocType(FrappeTestCase):
    """Group: Document Creation"""
    
    def test_create_with_minimal_fields(self):
        pass
    
    def test_create_with_all_fields(self):
        pass
    
    def test_create_with_child_table(self):
        pass
    
    """Group: Validation"""
    
    def test_required_field_validation(self):
        pass
    
    def test_field_format_validation(self):
        pass
    
    def test_custom_validation(self):
        pass
    
    """Group: Permissions"""
    
    def test_read_permission(self):
        pass
    
    def test_write_permission(self):
        pass
    
    def test_submit_permission(self):
        pass
```

### Use Helper Methods

```python
class TestMyDocType(FrappeTestCase):
    def create_test_document(self, **kwargs):
        """Helper to create test document"""
        defaults = {
            "doctype": "MyDocType",
            "field1": "default_value"
        }
        defaults.update(kwargs)
        return frappe.get_doc(defaults).insert()
    
    def create_test_user_with_role(self, role):
        """Helper to create test user with specific role"""
        email = f"test_{role}@example.com"
        if not frappe.db.exists("User", email):
            user = frappe.get_doc({
                "doctype": "User",
                "email": email,
                "first_name": "Test",
                "roles": [{"role": role}]
            })
            user.insert()
        return frappe.get_doc("User", email)
    
    def test_scenario_one(self):
        doc = self.create_test_document(field1="custom_value")
        # Test logic
    
    def test_scenario_two(self):
        user = self.create_test_user_with_role("System Manager")
        with self.set_user(user.email):
            # Test logic
```

### Organize by Feature

```python
# test_invoicing.py
class TestInvoiceCreation(FrappeTestCase):
    """Tests for invoice creation"""
    pass

class TestInvoiceCalculation(FrappeTestCase):
    """Tests for invoice calculations"""
    pass

class TestInvoicePermissions(FrappeTestCase):
    """Tests for invoice permissions"""
    pass
```

### Use Test Fixtures

```python
class TestMyDocType(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create test fixtures
        cls.company = create_test_company()
        cls.customer = create_test_customer()
        cls.item = create_test_item()
    
    def test_with_fixtures(self):
        # Use cls.company, cls.customer, cls.item
        doc = frappe.get_doc({
            "doctype": "MyDocType",
            "company": self.company.name,
            "customer": self.customer.name
        })
        # ...
```

---

## Real-World Examples

### Example 1: Complete DocType Test

```python
# Copyright (c) 2024, Your Company and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

test_dependencies = ["Company", "Customer"]

class TestSalesInvoice(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create shared test data
        if not frappe.db.exists("Company", "_Test Company"):
            cls.company = frappe.get_doc({
                "doctype": "Company",
                "company_name": "_Test Company",
                "abbr": "_TC"
            }).insert()
        else:
            cls.company = frappe.get_doc("Company", "_Test Company")
    
    def setUp(self):
        super().setUp()
        # Create test customer
        if not frappe.db.exists("Customer", "_Test Customer"):
            self.customer = frappe.get_doc({
                "doctype": "Customer",
                "customer_name": "_Test Customer"
            }).insert()
        else:
            self.customer = frappe.get_doc("Customer", "_Test Customer")
    
    def test_create_invoice(self):
        """Test creating a sales invoice"""
        invoice = frappe.get_doc({
            "doctype": "Sales Invoice",
            "company": self.company.name,
            "customer": self.customer.name,
            "items": [{
                "item_code": "_Test Item",
                "qty": 1,
                "rate": 100
            }]
        })
        invoice.insert()
        
        self.assertIsNotNone(invoice.name)
        self.assertEqual(invoice.total, 100)
        self.assertEqual(invoice.docstatus, 0)
    
    def test_submit_invoice(self):
        """Test submitting a sales invoice"""
        invoice = frappe.get_doc({
            "doctype": "Sales Invoice",
            "company": self.company.name,
            "customer": self.customer.name,
            "items": [{
                "item_code": "_Test Item",
                "qty": 1,
                "rate": 100
            }]
        })
        invoice.insert()
        invoice.submit()
        
        self.assertEqual(invoice.docstatus, 1)
        self.assertFalse(invoice.is_new())
    
    def test_cannot_update_after_submit(self):
        """Test that invoice cannot be updated after submission"""
        invoice = frappe.get_doc({
            "doctype": "Sales Invoice",
            "company": self.company.name,
            "customer": self.customer.name,
            "items": [{
                "item_code": "_Test Item",
                "qty": 1,
                "rate": 100
            }]
        })
        invoice.insert()
        invoice.submit()
        
        invoice.total = 200
        with self.assertRaises(frappe.UpdateAfterSubmitError):
            invoice.save()
    
    def test_cancel_invoice(self):
        """Test canceling a sales invoice"""
        invoice = frappe.get_doc({
            "doctype": "Sales Invoice",
            "company": self.company.name,
            "customer": self.customer.name,
            "items": [{
                "item_code": "_Test Item",
                "qty": 1,
                "rate": 100
            }]
        })
        invoice.insert()
        invoice.submit()
        invoice.cancel()
        
        self.assertEqual(invoice.docstatus, 2)
```

### Example 2: API Testing

```python
from frappe.tests.test_api import FrappeAPITestCase
import frappe

class TestSalesInvoiceAPI(FrappeAPITestCase):
    version = "v1"
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create test data
        cls.company = frappe.get_doc({
            "doctype": "Company",
            "company_name": "_Test Company",
            "abbr": "_TC"
        }).insert()
        
        cls.customer = frappe.get_doc({
            "doctype": "Customer",
            "customer_name": "_Test Customer"
        }).insert()
    
    def test_create_invoice_via_api(self):
        """Test creating invoice via API"""
        data = {
            "doctype": "Sales Invoice",
            "company": self.company.name,
            "customer": self.customer.name,
            "items": [{
                "item_code": "_Test Item",
                "qty": 1,
                "rate": 100
            }]
        }
        
        response = self.post(self.resource("Sales Invoice"), data)
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.json["data"]["name"])
    
    def test_get_invoice_via_api(self):
        """Test retrieving invoice via API"""
        # Create invoice first
        invoice = frappe.get_doc({
            "doctype": "Sales Invoice",
            "company": self.company.name,
            "customer": self.customer.name,
            "items": [{
                "item_code": "_Test Item",
                "qty": 1,
                "rate": 100
            }]
        }).insert()
        
        response = self.get(self.resource("Sales Invoice", invoice.name))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["data"]["customer"], self.customer.name)
```

### Example 3: Permission Testing

```python
import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.permissions import add_user_permission

class TestSalesInvoicePermissions(FrappeTestCase):
    def setUp(self):
        super().setUp()
        # Create test user
        self.test_user = frappe.get_doc({
            "doctype": "User",
            "email": "test_invoice_user@example.com",
            "first_name": "Test",
            "roles": [{"role": "Accounts User"}]
        })
        if not frappe.db.exists("User", self.test_user.email):
            self.test_user.insert()
        
        # Create test invoice
        self.invoice = frappe.get_doc({
            "doctype": "Sales Invoice",
            "company": "_Test Company",
            "customer": "_Test Customer",
            "items": [{
                "item_code": "_Test Item",
                "qty": 1,
                "rate": 100
            }]
        }).insert()
    
    def test_user_can_read_own_invoices(self):
        """Test that user can read invoices they created"""
        with self.set_user(self.test_user.email):
            # User creates invoice
            invoice = frappe.get_doc({
                "doctype": "Sales Invoice",
                "company": "_Test Company",
                "customer": "_Test Customer",
                "items": [{
                    "item_code": "_Test Item",
                    "qty": 1,
                    "rate": 100
                }]
            }).insert()
            
            # User can read their own invoice
            doc = frappe.get_doc("Sales Invoice", invoice.name)
            self.assertTrue(doc.has_permission("read"))
    
    def test_user_cannot_read_other_invoices(self):
        """Test that user cannot read invoices created by others"""
        with self.set_user(self.test_user.email):
            # Try to access invoice created by Administrator
            with self.assertRaises(frappe.PermissionError):
                frappe.get_doc("Sales Invoice", self.invoice.name)
    
    def test_user_permission_restriction(self):
        """Test user permission restrictions"""
        # Add user permission for specific customer
        add_user_permission("Customer", "_Test Customer", self.test_user.email)
        
        with self.set_user(self.test_user.email):
            # User can only see invoices for permitted customer
            invoices = frappe.get_list("Sales Invoice", filters={"customer": "_Test Customer"})
            self.assertGreater(len(invoices), 0)
            
            # User cannot see invoices for other customers
            other_invoices = frappe.get_list("Sales Invoice", filters={"customer": ["!=", "_Test Customer"]})
            self.assertEqual(len(other_invoices), 0)
```

### Example 4: Complex Calculation Testing

```python
import frappe
from frappe.tests.utils import FrappeTestCase

class TestInvoiceCalculations(FrappeTestCase):
    def test_tax_calculation(self):
        """Test tax calculation on invoice"""
        invoice = frappe.get_doc({
            "doctype": "Sales Invoice",
            "company": "_Test Company",
            "customer": "_Test Customer",
            "items": [{
                "item_code": "_Test Item",
                "qty": 10,
                "rate": 100
            }],
            "taxes": [{
                "charge_type": "On Net Total",
                "rate": 10
            }]
        })
        invoice.insert()
        
        # Base amount: 10 * 100 = 1000
        # Tax (10%): 100
        # Total: 1100
        self.assertEqual(invoice.net_total, 1000)
        self.assertEqual(invoice.total_taxes_and_charges, 100)
        self.assertEqual(invoice.grand_total, 1100)
    
    def test_discount_calculation(self):
        """Test discount calculation"""
        invoice = frappe.get_doc({
            "doctype": "Sales Invoice",
            "company": "_Test Company",
            "customer": "_Test Customer",
            "items": [{
                "item_code": "_Test Item",
                "qty": 10,
                "rate": 100,
                "discount_percentage": 10
            }]
        })
        invoice.insert()
        
        # Base: 1000
        # Discount (10%): 100
        # Net: 900
        self.assertEqual(invoice.total, 900)
    
    def test_rounding_calculation(self):
        """Test rounding in calculations"""
        invoice = frappe.get_doc({
            "doctype": "Sales Invoice",
            "company": "_Test Company",
            "customer": "_Test Customer",
            "items": [{
                "item_code": "_Test Item",
                "qty": 3,
                "rate": 33.33  # Will result in 99.99
            }]
        })
        invoice.insert()
        
        # Should handle rounding correctly
        self.assertAlmostEqual(invoice.total, 99.99, places=2)
```

### Example 5: Workflow Testing

```python
import frappe
from frappe.tests.utils import FrappeTestCase

class TestWorkflowStates(FrappeTestCase):
    def setUp(self):
        super().setUp()
        # Create test document
        self.doc = frappe.get_doc({
            "doctype": "MyDocType",
            "field1": "value1",
            "workflow_state": "Draft"
        })
        self.doc.insert()
    
    def test_draft_to_submitted(self):
        """Test workflow transition from Draft to Submitted"""
        self.assertEqual(self.doc.workflow_state, "Draft")
        
        # Transition to Submitted
        self.doc.workflow_state = "Submitted"
        self.doc.save()
        
        self.assertEqual(self.doc.workflow_state, "Submitted")
    
    def test_invalid_transition(self):
        """Test that invalid workflow transitions are prevented"""
        self.doc.workflow_state = "Draft"
        self.doc.save()
        
        # Try invalid transition: Draft -> Cancelled (should go through Submitted first)
        self.doc.workflow_state = "Cancelled"
        with self.assertRaises(frappe.ValidationError):
            self.doc.save()
    
    def test_workflow_action_permissions(self):
        """Test that workflow actions respect permissions"""
        with self.set_user("test@example.com"):
            doc = frappe.get_doc("MyDocType", self.doc.name)
            
            # User may not have permission to transition
            if not doc.has_permission("write"):
                with self.assertRaises(frappe.PermissionError):
                    doc.workflow_state = "Submitted"
                    doc.save()
```

### Example 6: Child Table Testing

```python
import frappe
from frappe.tests.utils import FrappeTestCase

class TestChildTableOperations(FrappeTestCase):
    def test_add_child_rows(self):
        """Test adding child table rows"""
        doc = frappe.get_doc({
            "doctype": "Sales Invoice",
            "company": "_Test Company",
            "customer": "_Test Customer",
            "items": []
        })
        
        # Add items
        doc.append("items", {
            "item_code": "_Test Item",
            "qty": 1,
            "rate": 100
        })
        doc.append("items", {
            "item_code": "_Test Item",
            "qty": 2,
            "rate": 50
        })
        
        doc.insert()
        
        self.assertEqual(len(doc.items), 2)
        self.assertEqual(doc.total, 200)  # 1*100 + 2*50
    
    def test_remove_child_rows(self):
        """Test removing child table rows"""
        doc = frappe.get_doc({
            "doctype": "Sales Invoice",
            "company": "_Test Company",
            "customer": "_Test Customer",
            "items": [
                {"item_code": "_Test Item", "qty": 1, "rate": 100},
                {"item_code": "_Test Item", "qty": 2, "rate": 50}
            ]
        })
        doc.insert()
        
        # Remove first item
        doc.remove(doc.items[0])
        doc.save()
        
        self.assertEqual(len(doc.items), 1)
        self.assertEqual(doc.total, 100)  # Only 2*50 remains
    
    def test_update_child_row(self):
        """Test updating child table row"""
        doc = frappe.get_doc({
            "doctype": "Sales Invoice",
            "company": "_Test Company",
            "customer": "_Test Customer",
            "items": [{
                "item_code": "_Test Item",
                "qty": 1,
                "rate": 100
            }]
        })
        doc.insert()
        
        # Update quantity
        doc.items[0].qty = 5
        doc.save()
        
        self.assertEqual(doc.items[0].qty, 5)
        self.assertEqual(doc.total, 500)
```

### Example 7: Date and Time Testing

```python
import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate, getdate

class TestDateOperations(FrappeTestCase):
    def test_date_range_validation(self):
        """Test date range validation"""
        with self.freeze_time("2024-01-15"):
            doc = frappe.get_doc({
                "doctype": "MyDocType",
                "start_date": nowdate(),
                "end_date": add_days(nowdate(), 30)
            })
            doc.insert()
            
            # Valid range
            self.assertIsNotNone(doc.name)
            
            # Invalid range
            doc.end_date = add_days(nowdate(), -1)  # Before start
            with self.assertRaises(frappe.exceptions.InvalidDates):
                doc.validate_from_to_dates("start_date", "end_date")
    
    def test_date_calculations(self):
        """Test date-based calculations"""
        with self.freeze_time("2024-01-15"):
            doc = frappe.get_doc({
                "doctype": "MyDocType",
                "start_date": nowdate(),
                "end_date": add_days(nowdate(), 30)
            })
            doc.insert()
            
            # Calculate duration
            duration = (getdate(doc.end_date) - getdate(doc.start_date)).days
            self.assertEqual(duration, 30)
    
    def test_time_based_queries(self):
        """Test queries filtered by date"""
        with self.freeze_time("2024-01-15"):
            # Create document with today's date
            doc = frappe.get_doc({
                "doctype": "MyDocType",
                "date_field": nowdate()
            })
            doc.insert()
            
            # Query documents for today
            today_docs = frappe.get_all(
                "MyDocType",
                filters={"date_field": nowdate()}
            )
            self.assertGreaterEqual(len(today_docs), 1)
```

### Example 8: Error Handling Testing

```python
import frappe
from frappe.tests.utils import FrappeTestCase

class TestErrorHandling(FrappeTestCase):
    def test_duplicate_entry_error(self):
        """Test duplicate entry prevention"""
        doc1 = frappe.get_doc({
            "doctype": "MyDocType",
            "unique_field": "unique_value"
        })
        doc1.insert()
        
        # Try to create duplicate
        doc2 = frappe.get_doc({
            "doctype": "MyDocType",
            "unique_field": "unique_value"
        })
        
        with self.assertRaises(frappe.DuplicateEntryError) as cm:
            doc2.insert()
        
        error_message = str(cm.exception)
        self.assertIn("unique", error_message.lower())
        self.assertIn("unique_field", error_message)
    
    def test_mandatory_error(self):
        """Test mandatory field error"""
        doc = frappe.get_doc({
            "doctype": "MyDocType",
            # Missing mandatory field
        })
        
        with self.assertRaises(frappe.MandatoryError) as cm:
            doc.insert()
        
        error_message = str(cm.exception)
        self.assertIn("mandatory", error_message.lower())
    
    def test_validation_error_with_context(self):
        """Test validation error with context manager"""
        doc = frappe.get_doc({
            "doctype": "MyDocType",
            "field1": "invalid_value"
        })
        
        with self.assertRaises(frappe.ValidationError) as cm:
            doc.validate()
        
        # Check error message
        error_message = str(cm.exception)
        self.assertIsNotNone(error_message)
        
        # Check exception type
        self.assertIsInstance(cm.exception, frappe.ValidationError)
```

---

## Summary

This guide has covered comprehensive test patterns and best practices for Frappe unit testing:

### Key Takeaways

1. **Test Patterns**: Use established patterns for common scenarios (lifecycle, validation, permissions, workflows, etc.)

2. **Assertions**: Leverage both standard unittest assertions and Frappe-specific assertions like `assertDocumentEqual`

3. **Context Managers**: Use Frappe's context managers (`set_user`, `freeze_time`, etc.) for clean test setup

4. **Organization**: Structure tests logically with proper setup/teardown and helper methods

5. **Best Practices**: 
   - Write descriptive test names
   - Test one concept per test
   - Use meaningful test data
   - Test edge cases
   - Keep tests isolated

6. **Anti-Patterns**: Avoid testing implementation details, over-mocking, and non-deterministic tests

7. **Real-World Examples**: Follow examples from actual Frappe codebase for practical implementation

### Additional Resources

- [Frappe Testing Documentation](https://docs.frappe.io/framework/user/en/testing)
- [Python unittest Documentation](https://docs.python.org/3/library/unittest.html)
- [Frappe Source Code Tests](https://github.com/frappe/frappe/tree/develop/frappe/tests)

### Next Steps

Continue to:
- [Part 1: Fundamentals](./63-Frappe_Unit_Testing_Guide_Part_1_Fundamentals.md)
- [Part 2: Test Commands and Execution](./64-Frappe_Unit_Testing_Guide_Part_2_Test_Commands.md)
- [Part 4: Advanced Testing Techniques](./66-Frappe_Unit_Testing_Guide_Part_4_Advanced.md)
- [Part 5: Test Data Management](./67-Frappe_Unit_Testing_Guide_Part_5_Test_Data.md)
- [Part 6: Test Utilities and Techniques](./68-Frappe_Unit_Testing_Guide_Part_6_Utilities.md)
- [Part 7: Assertions](./69-Frappe_Unit_Testing_Guide_Part_7_Assertions.md)
- [Part 8: Reports](./80-Frappe_Unit_Testing_Guide_Part_8_Reports.md)
- [Part 9: Test Records](./82-Frappe_Unit_Testing_Guide_Part_9_Test_Records.md)

# Frappe Unit Testing Guide - Part 4: Advanced Testing Techniques

## Table of Contents
1. [Mocking and Patching](#mocking-and-patching)
2. [Testing Background Jobs](#testing-background-jobs)
3. [Testing Hooks](#testing-hooks)
4. [Testing with External Services](#testing-with-external-services)
5. [Testing Transactions](#testing-transactions)
6. [Testing Concurrency](#testing-concurrency)
7. [Testing Performance](#testing-performance)
8. [Testing Caching](#testing-caching)
9. [Testing Custom Methods](#testing-custom-methods)
10. [Advanced Context Managers](#advanced-context-managers)
11. [Testing with Multiple Sites](#testing-with-multiple-sites)
12. [Testing Async Operations](#testing-async-operations)

---

## Mocking and Patching

Mocking allows you to replace real objects with fake ones during testing. This is useful for isolating code under test and avoiding side effects.

### Basic Mocking with unittest.mock

Frappe uses Python's built-in `unittest.mock` module for mocking.

#### Simple Mock

```python
from unittest.mock import Mock, patch
import frappe
from frappe.tests.utils import FrappeTestCase

class TestMyFunction(FrappeTestCase):
    def test_with_mock(self):
        # Create a mock object
        mock_obj = Mock()
        mock_obj.method.return_value = "mocked_value"
        
        # Use the mock
        result = mock_obj.method()
        self.assertEqual(result, "mocked_value")
        
        # Verify the method was called
        mock_obj.method.assert_called_once()
```

#### Patching Functions

```python
from unittest.mock import patch

class TestMyDocType(FrappeTestCase):
    @patch('frappe.get_doc')
    def test_with_patched_function(self, mock_get_doc):
        # Configure mock return value
        mock_doc = Mock()
        mock_doc.name = "test-doc"
        mock_get_doc.return_value = mock_doc
        
        # Your code that uses frappe.get_doc
        doc = frappe.get_doc("MyDocType", "test-doc")
        
        # Verify it was called correctly
        mock_get_doc.assert_called_once_with("MyDocType", "test-doc")
        self.assertEqual(doc.name, "test-doc")
```

#### Patching as Context Manager

```python
def test_with_context_manager(self):
    with patch('frappe.get_doc') as mock_get_doc:
        mock_doc = Mock()
        mock_doc.name = "test-doc"
        mock_get_doc.return_value = mock_doc
        
        doc = frappe.get_doc("MyDocType", "test-doc")
        self.assertEqual(doc.name, "test-doc")
    
    # Patch is automatically removed after context
```

#### Patching Object Attributes

```python
@patch.object(frappe.utils.frappecloud, "on_frappecloud", return_value=True)
def test_patch_object_attribute(self, mock_on_frappecloud):
    # Test code that uses frappe.utils.frappecloud.on_frappecloud
    result = frappe.utils.frappecloud.on_frappecloud()
    self.assertTrue(result)
    mock_on_frappecloud.assert_called_once()
```

#### Patching Dictionary Values

```python
@patch.dict(frappe.conf, {"developer_mode": 0, "http_timeout": 20})
def test_patch_config(self):
    # Test code that reads from frappe.conf
    self.assertEqual(frappe.conf.developer_mode, 0)
    self.assertEqual(frappe.conf.http_timeout, 20)
```

#### Patching Multiple Objects

```python
@patch('frappe.get_doc')
@patch('frappe.db.get_value')
@patch('frappe.cache')
def test_multiple_patches(self, mock_cache, mock_db, mock_get_doc):
    # Configure all mocks
    mock_get_doc.return_value = Mock(name="test-doc")
    mock_db.get_value.return_value = "test-value"
    
    # Your test code
    pass
```

**Note**: Patch decorators are applied bottom-to-top, so the last decorator is the first parameter.

### Mocking Document Methods

```python
from unittest.mock import Mock, patch

class TestDocumentMethods(FrappeTestCase):
    def test_mock_document_method(self):
        doc = frappe.get_doc({
            "doctype": "ToDo",
            "description": "test"
        })
        
        # Mock a method
        doc.notify_update = Mock()
        doc.insert()
        
        # Verify method was called
        self.assertEqual(doc.notify_update.call_count, 1)
    
    def test_mock_run_method(self):
        doc = frappe.get_doc("User", "Administrator")
        
        # Override a method
        def my_as_dict(*args, **kwargs):
            return "success"
        
        doc.as_dict = my_as_dict
        
        # Test run_method with override
        result = doc.run_method("as_dict")
        self.assertEqual(result, "success")
```

### When to Use Mocking

**Use mocking when**:
- Testing code that makes external API calls
- Testing code that depends on expensive operations
- Testing error handling without causing real errors
- Isolating units of code
- Testing code that depends on time/date functions

**Avoid mocking when**:
- You can test with real objects easily
- Mocking makes tests more complex than the code
- You need to test real integration
- Mocking hides important behavior

---

## Testing Background Jobs

Frappe uses RQ (Redis Queue) for background job processing. Testing background jobs requires special handling.

### Testing Enqueued Jobs

```python
import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.background_jobs import get_queue

class TestBackgroundJobs(FrappeTestCase):
    def test_enqueue_job(self):
        # Enqueue a job
        job = frappe.enqueue(
            method="frappe.handler.ping",
            queue="short"
        )
        
        # Verify job was enqueued
        self.assertIsNotNone(job)
        self.assertIsNotNone(job.id)
    
    def test_enqueue_with_kwargs(self):
        def my_function(arg1, arg2):
            return arg1 + arg2
        
        job = frappe.enqueue(
            method=my_function,
            queue="default",
            arg1=10,
            arg2=20
        )
        
        self.assertIsNotNone(job)
    
    def test_enqueue_at_front(self):
        """Test high priority jobs"""
        # Enqueue normal job
        low_priority = frappe.enqueue(
            method="frappe.handler.ping",
            queue="short"
        )
        
        # Enqueue high priority job
        high_priority = frappe.enqueue(
            method="frappe.handler.ping",
            queue="short",
            at_front=True
        )
        
        # High priority should be earlier in queue
        self.assertTrue(
            high_priority.get_position() < low_priority.get_position()
        )
```

### Testing Job Execution

```python
import time
from frappe.utils.background_jobs import execute_job

class TestJobExecution(FrappeTestCase):
    def test_execute_job_synchronously(self):
        """Test job execution without async"""
        result = frappe.enqueue(
            method="frappe.handler.ping",
            queue="short",
            is_async=False  # Execute immediately
        )
        
        self.assertEqual(result, "pong")
    
    def test_execute_job_with_now(self):
        """Test immediate job execution"""
        result = frappe.enqueue(
            method="frappe.handler.ping",
            queue="short",
            now=True  # Execute immediately
        )
        
        self.assertEqual(result, "pong")
    
    def test_wait_for_job_completion(self):
        """Test waiting for async job to complete"""
        job = frappe.enqueue(
            method="frappe.handler.ping",
            queue="short"
        )
        
        # Wait for completion
        while job.is_queued or job.is_started:
            time.sleep(0.1)
        
        # Verify job completed
        self.assertTrue(job.is_finished)
        self.assertEqual(job.result, "pong")
```

### Testing Job Hooks

```python
import time
from unittest.mock import patch
from frappe.utils.background_jobs import execute_job

class TestJobHooks(FrappeTestCase):
    def test_before_job_hook(self):
        """Test before_job hook execution"""
        hook_called = []
        
        def before_job_handler(*args, **kwargs):
            hook_called.append("before")
        
        with patch('frappe.get_hooks', return_value={
            'before_job': ['my_app.hooks.before_job_handler']
        }):
            execute_job(
                site=frappe.local.site,
                method="frappe.handler.ping",
                event=None,
                job_name="test",
                is_async=True,
                kwargs={}
            )
            
            self.assertIn("before", hook_called)
    
    def test_after_job_hook(self):
        """Test after_job hook execution"""
        hook_called = []
        
        def after_job_handler(*args, **kwargs):
            hook_called.append("after")
        
        with patch('frappe.get_hooks', return_value={
            'after_job': ['my_app.hooks.after_job_handler']
        }):
            execute_job(
                site=frappe.local.site,
                method="frappe.handler.ping",
                event=None,
                job_name="test",
                is_async=True,
                kwargs={}
            )
            
            self.assertIn("after", hook_called)
```

### Testing Failed Jobs

```python
from frappe.core.doctype.rq_job.rq_job import remove_failed_jobs
from frappe.utils.background_jobs import get_redis_conn, generate_qname
from rq import Queue

class TestFailedJobs(FrappeTestCase):
    def test_remove_failed_jobs(self):
        """Test removing failed jobs from queue"""
        # Enqueue a job that will fail
        frappe.enqueue(
            method="frappe.tests.test_background_jobs.fail_function",
            queue="short"
        )
        
        # Wait for job to fail
        time.sleep(2)
        
        # Check failed jobs exist
        conn = get_redis_conn()
        queues = Queue.all(conn)
        
        for queue in queues:
            if queue.name == generate_qname("short"):
                fail_registry = queue.failed_job_registry
                self.assertGreater(fail_registry.count, 0)
        
        # Remove failed jobs
        remove_failed_jobs()
        
        # Verify failed jobs removed
        for queue in queues:
            if queue.name == generate_qname("short"):
                fail_registry = queue.failed_job_registry
                self.assertEqual(fail_registry.count, 0)

def fail_function():
    """Function that always fails"""
    return 1 / 0
```

### Testing Job Deduplication

```python
class TestJobDeduplication(FrappeTestCase):
    def test_deduplicate_jobs(self):
        """Test that duplicate jobs are not enqueued"""
        job_id = "unique-job-id"
        
        # Enqueue first job
        job1 = frappe.enqueue(
            method="frappe.handler.ping",
            queue="short",
            job_id=job_id,
            deduplicate=True
        )
        
        # Try to enqueue duplicate
        job2 = frappe.enqueue(
            method="frappe.handler.ping",
            queue="short",
            job_id=job_id,
            deduplicate=True
        )
        
        # Second job should not be enqueued
        self.assertIsNone(job2)
```

---

## Testing Hooks

Hooks are a powerful Frappe feature that allows apps to extend functionality. Testing hooks requires patching the hook system.

### Testing Document Hooks

```python
from unittest.mock import patch
import frappe

class TestDocumentHooks(FrappeTestCase):
    def test_before_insert_hook(self):
        """Test before_insert hook"""
        hook_called = []
        
        def before_insert_handler(doc, method):
            hook_called.append("before_insert")
        
        with patch('frappe.get_doc_hooks', return_value={
            'MyDocType': {
                'before_insert': ['my_app.hooks.before_insert_handler']
            }
        }):
            doc = frappe.get_doc({
                "doctype": "MyDocType",
                "field1": "value1"
            })
            doc.insert()
            
            self.assertIn("before_insert", hook_called)
    
    def test_on_update_hook(self):
        """Test on_update hook"""
        hook_called = []
        
        def on_update_handler(doc, method):
            hook_called.append("on_update")
        
        with patch('frappe.get_doc_hooks', return_value={
            'MyDocType': {
                'on_update': ['my_app.hooks.on_update_handler']
            }
        }):
            doc = frappe.get_doc({
                "doctype": "MyDocType",
                "field1": "value1"
            })
            doc.insert()
            doc.field1 = "new_value"
            doc.save()
            
            self.assertIn("on_update", hook_called)
```

### Testing App Hooks

```python
from frappe.tests.utils import patch_hooks

class TestAppHooks(FrappeTestCase):
    def test_custom_hook(self):
        """Test custom app hook"""
        overridden_hooks = {
            'my_custom_hook': ['my_app.hooks.custom_handler']
        }
        
        with patch_hooks(overridden_hooks):
            hooks = frappe.get_hooks('my_custom_hook')
            self.assertIn('my_app.hooks.custom_handler', hooks)
```

### Testing Permission Hooks

```python
class TestPermissionHooks(FrappeTestCase):
    def test_permission_query_hook(self):
        """Test permission query hook"""
        def custom_permission_query(doctype, user):
            return f"`tab{doctype}`.owner = '{user}'"
        
        with patch('frappe.get_hooks', return_value={
            'permission_query_conditions': {
                'MyDocType': ['my_app.hooks.custom_permission_query']
            }
        }):
            # Test that permission query is applied
            pass
```

---

## Testing with External Services

When your code interacts with external services (APIs, email, etc.), you should mock those interactions.

### Testing HTTP Requests

Frappe provides `MockedRequestTestCase` for testing code that makes HTTP requests.

```python
from frappe.tests.utils import MockedRequestTestCase
import responses

class TestExternalAPI(MockedRequestTestCase):
    def test_external_api_call(self):
        """Test code that calls external API"""
        # Mock the external API response
        self.responses.add(
            responses.GET,
            "https://api.example.com/data",
            json={"status": "ok", "data": "test"},
            status=200
        )
        
        # Your code that calls the API
        import requests
        response = requests.get("https://api.example.com/data")
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
    
    def test_api_error_handling(self):
        """Test handling of API errors"""
        # Mock API error
        self.responses.add(
            responses.GET,
            "https://api.example.com/data",
            status=500
        )
        
        # Test error handling
        import requests
        response = requests.get("https://api.example.com/data")
        self.assertEqual(response.status_code, 500)
```

### Testing Email Sending

```python
from unittest.mock import patch

class TestEmailSending(FrappeTestCase):
    @patch('frappe.sendmail')
    def test_send_email(self, mock_sendmail):
        """Test email sending without actually sending"""
        # Configure mock
        mock_sendmail.return_value = True
        
        # Your code that sends email
        frappe.sendmail(
            recipients=["test@example.com"],
            subject="Test",
            message="Test message"
        )
        
        # Verify email was "sent"
        mock_sendmail.assert_called_once()
        call_args = mock_sendmail.call_args
        self.assertIn("test@example.com", call_args[1]["recipients"])
    
    def test_email_queue(self):
        """Test email queuing"""
        frappe.sendmail(
            recipients=["test@example.com"],
            subject="Test",
            message="Test message"
        )
        
        # Verify email is queued
        email_queue = frappe.get_all("Email Queue", filters={"status": "Not Sent"})
        self.assertGreater(len(email_queue), 0)
```

### Testing File Operations

```python
from unittest.mock import patch, mock_open
import os

class TestFileOperations(FrappeTestCase):
    @patch('builtins.open', new_callable=mock_open, read_data="file content")
    def test_read_file(self, mock_file):
        """Test file reading"""
        with open("test.txt", "r") as f:
            content = f.read()
        
        self.assertEqual(content, "file content")
        mock_file.assert_called_once_with("test.txt", "r")
    
    @patch('os.path.exists', return_value=True)
    def test_file_exists(self, mock_exists):
        """Test file existence check"""
        exists = os.path.exists("test.txt")
        self.assertTrue(exists)
        mock_exists.assert_called_once_with("test.txt")
```

---

## Testing Transactions

Frappe automatically manages transactions in tests, but sometimes you need to test transaction behavior explicitly.

### Testing Savepoints

```python
from frappe.database import savepoint

class TestTransactions(FrappeTestCase):
    def test_savepoint_rollback(self):
        """Test savepoint and rollback"""
        # Create document
        doc = frappe.get_doc({
            "doctype": "MyDocType",
            "field1": "value1"
        })
        doc.insert()
        
        # Create savepoint
        sp = savepoint()
        
        # Make changes
        doc.field1 = "new_value"
        doc.save()
        
        # Rollback to savepoint
        frappe.db.rollback(save_point=sp)
        
        # Verify changes were rolled back
        doc.reload()
        self.assertEqual(doc.field1, "value1")
```

### Testing Transaction Isolation

```python
class TestTransactionIsolation(FrappeTestCase):
    def test_isolation_with_connections(self):
        """Test transaction isolation between connections"""
        # Primary connection
        with self.primary_connection():
            doc = frappe.get_doc({
                "doctype": "MyDocType",
                "field1": "value1"
            })
            doc.insert()
            # Don't commit yet
        
        # Secondary connection (shouldn't see uncommitted changes)
        with self.secondary_connection():
            # Try to read - should not see the document
            docs = frappe.get_all("MyDocType", filters={"field1": "value1"})
            self.assertEqual(len(docs), 0)
```

### Testing Deadlock Handling

```python
class TestDeadlockHandling(FrappeTestCase):
    def test_deadlock_retry(self):
        """Test handling of database deadlocks"""
        # Simulate deadlock scenario
        with self.primary_connection():
            doc1 = frappe.get_doc("MyDocType", "doc1")
            # Lock row
        
        with self.secondary_connection():
            doc2 = frappe.get_doc("MyDocType", "doc2")
            # Try to lock same row - may cause deadlock
        
        # Frappe should handle deadlock and retry
        pass
```

---

## Testing Concurrency

Testing concurrent operations helps identify race conditions and locking issues.

### Testing Concurrent Document Updates

```python
import threading
import time

class TestConcurrency(FrappeTestCase):
    def test_concurrent_updates(self):
        """Test concurrent document updates"""
        doc = frappe.get_doc({
            "doctype": "MyDocType",
            "field1": "initial"
        })
        doc.insert()
        
        results = []
        
        def update_document(value):
            try:
                d = frappe.get_doc("MyDocType", doc.name)
                d.field1 = value
                d.save()
                results.append(("success", value))
            except Exception as e:
                results.append(("error", str(e)))
        
        # Create multiple threads
        threads = []
        for i in range(5):
            t = threading.Thread(target=update_document, args=(f"value{i}",))
            threads.append(t)
            t.start()
        
        # Wait for all threads
        for t in threads:
            t.join()
        
        # Verify results
        # Some updates may fail due to conflicts
        self.assertGreater(len(results), 0)
```

### Testing Document Locks

```python
class TestDocumentLocks(FrappeTestCase):
    def test_document_lock(self):
        """Test document locking mechanism"""
        doc = frappe.get_doc({
            "doctype": "MyDocType",
            "field1": "value1"
        })
        doc.insert()
        
        # Lock document
        frappe.db.set_value("MyDocType", doc.name, "locked", 1)
        
        # Try to update locked document
        doc.field1 = "new_value"
        with self.assertRaises(frappe.ValidationError):
            doc.save()
```

---

## Testing Performance

Performance testing ensures your code meets performance requirements.

### Testing Query Performance

```python
class TestQueryPerformance(FrappeTestCase):
    def test_query_count(self):
        """Test that queries are optimized"""
        with self.assertQueryCount(5):  # Maximum 5 queries
            # Your code that should be optimized
            docs = frappe.get_all("MyDocType", limit=10)
            for doc in docs:
                frappe.get_doc("MyDocType", doc.name)
    
    def test_rows_read(self):
        """Test that not too many rows are read"""
        with self.assertRowsRead(100):  # Maximum 100 rows
            # Your code that reads data
            frappe.get_all("MyDocType", limit=100)
```

### Testing Cache Performance

```python
class TestCachePerformance(FrappeTestCase):
    def test_redis_calls(self):
        """Test that cache calls are optimized"""
        with self.assertRedisCallCounts(3):  # Maximum 3 Redis calls
            # Your code that uses cache
            frappe.cache().get_value("key1")
            frappe.cache().get_value("key2")
            frappe.cache().set_value("key3", "value")
```

### Profiling Tests

```python
import cProfile
import pstats
from io import StringIO

class TestPerformance(FrappeTestCase):
    def test_with_profiling(self):
        """Test with performance profiling"""
        profiler = cProfile.Profile()
        profiler.enable()
        
        # Your code to profile
        for i in range(1000):
            frappe.get_doc("User", "Administrator")
        
        profiler.disable()
        
        # Analyze results
        s = StringIO()
        ps = pstats.Stats(profiler, stream=s)
        ps.sort_stats('cumulative')
        ps.print_stats(10)  # Top 10 functions
        
        # Check for performance issues
        output = s.getvalue()
        # Analyze output for bottlenecks
```

---

## Testing Caching

Frappe uses Redis for caching. Test cache behavior to ensure correct caching logic.

### Testing Cache Operations

```python
class TestCaching(FrappeTestCase):
    def test_cache_set_get(self):
        """Test basic cache operations"""
        # Set cache value
        frappe.cache().set_value("test_key", "test_value")
        
        # Get cache value
        value = frappe.cache().get_value("test_key")
        self.assertEqual(value, "test_value")
    
    def test_cache_expiry(self):
        """Test cache expiration"""
        # Set cache with expiry
        frappe.cache().set_value("test_key", "test_value", expires_in_sec=1)
        
        # Value should exist
        value = frappe.cache().get_value("test_key")
        self.assertEqual(value, "test_value")
        
        # Wait for expiry
        import time
        time.sleep(2)
        
        # Value should be expired
        value = frappe.cache().get_value("test_key")
        self.assertIsNone(value)
    
    def test_cache_delete(self):
        """Test cache deletion"""
        # Set cache value
        frappe.cache().set_value("test_key", "test_value")
        
        # Delete cache value
        frappe.cache().delete_value("test_key")
        
        # Value should be gone
        value = frappe.cache().get_value("test_key")
        self.assertIsNone(value)
```

### Testing Cache Invalidation

```python
class TestCacheInvalidation(FrappeTestCase):
    def test_clear_cache(self):
        """Test cache clearing"""
        # Set multiple cache values
        frappe.cache().set_value("key1", "value1")
        frappe.cache().set_value("key2", "value2")
        
        # Clear all cache
        frappe.clear_cache()
        
        # Values should be gone
        self.assertIsNone(frappe.cache().get_value("key1"))
        self.assertIsNone(frappe.cache().get_value("key2"))
    
    def test_clear_doctype_cache(self):
        """Test clearing cache for specific DocType"""
        # Set cache for DocType
        frappe.cache().set_value("doctype:MyDocType", "meta_data")
        
        # Clear DocType cache
        frappe.clear_cache(doctype="MyDocType")
        
        # DocType cache should be cleared
        self.assertIsNone(frappe.cache().get_value("doctype:MyDocType"))
```

---

## Testing Custom Methods

Test custom methods on DocTypes and other classes.

### Testing Document Methods

```python
class TestCustomMethods(FrappeTestCase):
    def test_custom_document_method(self):
        """Test custom method on document"""
        doc = frappe.get_doc({
            "doctype": "MyDocType",
            "field1": "value1"
        })
        doc.insert()
        
        # Test custom method
        result = doc.my_custom_method()
        self.assertEqual(result, expected_value)
    
    def test_method_with_parameters(self):
        """Test method with parameters"""
        doc = frappe.get_doc("MyDocType", "test-doc")
        
        result = doc.calculate_total(discount=10, tax=5)
        self.assertEqual(result, expected_total)
    
    def test_method_side_effects(self):
        """Test method that modifies document"""
        doc = frappe.get_doc({
            "doctype": "MyDocType",
            "field1": "value1"
        })
        doc.insert()
        
        # Method should update document
        doc.apply_discount(10)
        
        # Verify side effects
        self.assertEqual(doc.discount_percentage, 10)
        self.assertNotEqual(doc.total, doc.original_total)
```

### Testing Static Methods

```python
class TestStaticMethods(FrappeTestCase):
    def test_static_method(self):
        """Test static/class method"""
        result = MyDocType.get_total_for_items(items)
        self.assertEqual(result, expected_total)
    
    def test_utility_function(self):
        """Test utility function"""
        from my_app.utils import calculate_tax
        
        result = calculate_tax(amount=1000, rate=10)
        self.assertEqual(result, 100)
```

---

## Advanced Context Managers

Frappe provides several advanced context managers for testing.

### Testing with Settings Changes

```python
from frappe.tests.utils import change_settings

class TestSettings(FrappeTestCase):
    @change_settings("System Settings", {"enable_scheduler": 0})
    def test_with_settings_change(self):
        """Test with temporary settings change"""
        # Settings are automatically restored after test
        settings = frappe.get_doc("System Settings")
        self.assertEqual(settings.enable_scheduler, 0)
    
    @change_settings("Print Settings", send_print_as_pdf=1)
    def test_settings_as_kwargs(self):
        """Test settings change using kwargs"""
        settings = frappe.get_doc("Print Settings")
        self.assertEqual(settings.send_print_as_pdf, 1)
```

### Testing with Time Freeze

```python
class TestTimeFreeze(FrappeTestCase):
    def test_freeze_time(self):
        """Test with frozen time"""
        with self.freeze_time("2024-01-15 10:00:00"):
            # All datetime operations use frozen time
            doc = frappe.get_doc({
                "doctype": "MyDocType",
                "date_field": frappe.utils.nowdate()
            })
            doc.insert()
            
            # Date should be frozen
            self.assertEqual(str(doc.date_field), "2024-01-15")
    
    def test_time_based_calculations(self):
        """Test time-based calculations with frozen time"""
        with self.freeze_time("2024-01-15 10:00:00"):
            start_time = frappe.utils.now()
            
            # Simulate time passing
            with self.freeze_time("2024-01-16 10:00:00"):
                end_time = frappe.utils.now()
                duration = (end_time - start_time).days
                self.assertEqual(duration, 1)
```

### Testing with User Context

```python
class TestUserContext(FrappeTestCase):
    def test_user_switching(self):
        """Test switching between users"""
        # Create test users
        user1 = frappe.get_doc({
            "doctype": "User",
            "email": "user1@test.com",
            "first_name": "User 1"
        })
        if not frappe.db.exists("User", user1.email):
            user1.insert()
        
        user2 = frappe.get_doc({
            "doctype": "User",
            "email": "user2@test.com",
            "first_name": "User 2"
        })
        if not frappe.db.exists("User", user2.email):
            user2.insert()
        
        # Switch to user1
        with self.set_user(user1.email):
            doc1 = frappe.get_doc({
                "doctype": "MyDocType",
                "field1": "value1"
            })
            doc1.insert()
            self.assertEqual(doc1.owner, user1.email)
        
        # Switch to user2
        with self.set_user(user2.email):
            doc2 = frappe.get_doc({
                "doctype": "MyDocType",
                "field1": "value2"
            })
            doc2.insert()
            self.assertEqual(doc2.owner, user2.email)
```

### Testing with Site Switching

```python
class TestSiteSwitching(FrappeTestCase):
    def test_multi_site_operations(self):
        """Test operations across multiple sites"""
        with self.switch_site("site1"):
            doc1 = frappe.get_doc({
                "doctype": "MyDocType",
                "field1": "site1_value"
            })
            doc1.insert()
            doc1_name = doc1.name
        
        with self.switch_site("site2"):
            # Document from site1 should not exist in site2
            self.assertFalse(frappe.db.exists("MyDocType", doc1_name))
            
            doc2 = frappe.get_doc({
                "doctype": "MyDocType",
                "field1": "site2_value"
            })
            doc2.insert()
```

---

## Testing with Multiple Sites

Frappe supports multi-tenant setups. Test cross-site operations and site-specific behavior.

### Testing Site-Specific Data

```python
class TestMultiSite(FrappeTestCase):
    def test_site_isolation(self):
        """Test that sites are isolated"""
        site1_docs = []
        site2_docs = []
        
        # Create documents in site1
        with self.switch_site("site1"):
            for i in range(5):
                doc = frappe.get_doc({
                    "doctype": "MyDocType",
                    "field1": f"site1_doc_{i}"
                })
                doc.insert()
                site1_docs.append(doc.name)
        
        # Create documents in site2
        with self.switch_site("site2"):
            for i in range(5):
                doc = frappe.get_doc({
                    "doctype": "MyDocType",
                    "field1": f"site2_doc_{i}"
                })
                doc.insert()
                site2_docs.append(doc.name)
        
        # Verify isolation
        with self.switch_site("site1"):
            docs = frappe.get_all("MyDocType")
            doc_names = [d.name for d in docs]
            for name in site1_docs:
                self.assertIn(name, doc_names)
            for name in site2_docs:
                self.assertNotIn(name, doc_names)
        
        with self.switch_site("site2"):
            docs = frappe.get_all("MyDocType")
            doc_names = [d.name for d in docs]
            for name in site2_docs:
                self.assertIn(name, doc_names)
            for name in site1_docs:
                self.assertNotIn(name, doc_names)
```

### Testing Site-Specific Configuration

```python
class TestSiteConfig(FrappeTestCase):
    def test_site_config_isolation(self):
        """Test that site configurations are isolated"""
        with self.switch_site("site1"):
            frappe.db.set_value("System Settings", "System Settings", "enable_scheduler", 0)
            frappe.db.commit()
            
            settings = frappe.get_doc("System Settings")
            self.assertEqual(settings.enable_scheduler, 0)
        
        with self.switch_site("site2"):
            # Site2 should have default settings
            settings = frappe.get_doc("System Settings")
            # Default value (may be 1)
            self.assertIsNotNone(settings.enable_scheduler)
```

### Testing Cross-Site Operations

```python
class TestCrossSiteOperations(FrappeTestCase):
    def test_data_migration(self):
        """Test migrating data between sites"""
        # Create data in source site
        with self.switch_site("site1"):
            source_doc = frappe.get_doc({
                "doctype": "MyDocType",
                "field1": "migrate_me"
            })
            source_doc.insert()
            source_data = source_doc.as_dict()
        
        # Migrate to target site
        with self.switch_site("site2"):
            target_doc = frappe.get_doc(source_data)
            target_doc.insert()
            
            self.assertEqual(target_doc.field1, "migrate_me")
```

---

## Testing Async Operations

Test asynchronous operations, callbacks, and event-driven code.

### Testing Enqueued Operations

```python
import time
from frappe.utils.background_jobs import get_queue

class TestAsyncOperations(FrappeTestCase):
    def test_async_function_execution(self):
        """Test async function execution"""
        def async_function(value):
            return value * 2
        
        # Enqueue async function
        job = frappe.enqueue(
            method=async_function,
            queue="default",
            value=10
        )
        
        # Wait for completion
        while job.is_queued or job.is_started:
            time.sleep(0.1)
        
        # Verify result
        self.assertTrue(job.is_finished)
        self.assertEqual(job.result, 20)
    
    def test_async_with_callback(self):
        """Test async operation with callbacks"""
        callback_called = []
        
        def on_success(job, connection, result, *args, **kwargs):
            callback_called.append(("success", result))
        
        def on_failure(job, connection, type, value, traceback):
            callback_called.append(("failure", str(value)))
        
        job = frappe.enqueue(
            method="frappe.handler.ping",
            queue="short",
            on_success=on_success,
            on_failure=on_failure
        )
        
        # Wait for completion
        while job.is_queued or job.is_started:
            time.sleep(0.1)
        
        # Verify callback was called
        self.assertGreater(len(callback_called), 0)
        self.assertEqual(callback_called[0][0], "success")
```

### Testing Event-Driven Code

```python
class TestEventDriven(FrappeTestCase):
    def test_document_events(self):
        """Test document event handlers"""
        events_fired = []
        
        def before_insert_handler(doc, method):
            events_fired.append("before_insert")
        
        def after_insert_handler(doc, method):
            events_fired.append("after_insert")
        
        # Register event handlers (in real code, these would be hooks)
        with patch('frappe.get_doc_hooks', return_value={
            'MyDocType': {
                'before_insert': ['my_app.hooks.before_insert_handler'],
                'after_insert': ['my_app.hooks.after_insert_handler']
            }
        }):
            doc = frappe.get_doc({
                "doctype": "MyDocType",
                "field1": "value1"
            })
            doc.insert()
            
            # Verify events were fired
            self.assertIn("before_insert", events_fired)
            self.assertIn("after_insert", events_fired)
```

### Testing Webhooks

```python
from unittest.mock import patch
import requests

class TestWebhooks(FrappeTestCase):
    @patch('requests.post')
    def test_webhook_trigger(self, mock_post):
        """Test webhook triggering"""
        # Configure mock response
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"status": "ok"}
        
        # Trigger webhook
        doc = frappe.get_doc({
            "doctype": "MyDocType",
            "field1": "value1"
        })
        doc.insert()
        
        # Webhook should be triggered (if configured)
        # Verify webhook was called
        # (Implementation depends on your webhook system)
        pass
    
    def test_webhook_retry(self):
        """Test webhook retry logic"""
        call_count = []
        
        def failing_webhook(*args, **kwargs):
            call_count.append(1)
            if len(call_count) < 3:
                raise Exception("Temporary failure")
            return {"status": "ok"}
        
        with patch('requests.post', side_effect=failing_webhook):
            # Trigger webhook with retry
            # Should retry on failure
            pass
```

### Testing Real-time Updates

```python
class TestRealtimeUpdates(FrappeTestCase):
    def test_realtime_notification(self):
        """Test realtime update notifications"""
        doc = frappe.get_doc({
            "doctype": "ToDo",
            "description": "test"
        })
        
        # Mock notify_update
        doc.notify_update = Mock()
        
        doc.insert()
        
        # Verify notification was sent
        self.assertEqual(doc.notify_update.call_count, 1)
    
    def test_realtime_with_flag(self):
        """Test disabling realtime updates"""
        doc = frappe.get_doc({
            "doctype": "ToDo",
            "description": "test"
        })
        doc.insert()
        
        doc.reload()
        doc.flags.notify_update = False
        doc.description = "updated"
        doc.save()
        
        # Should not trigger realtime update
        # (Implementation specific)
        pass
```

### Testing Scheduled Tasks

```python
from unittest.mock import patch
from frappe.utils import now_datetime

class TestScheduledTasks(FrappeTestCase):
    def test_scheduled_task_execution(self):
        """Test scheduled task execution"""
        with self.freeze_time("2024-01-15 10:00:00"):
            # Schedule task
            frappe.enqueue(
                method="my_app.tasks.scheduled_task",
                queue="long",
                job_id="scheduled-task-1"
            )
            
            # Advance time
            with self.freeze_time("2024-01-15 11:00:00"):
                # Task should execute
                # (Implementation depends on scheduler)
                pass
    
    @patch('frappe.utils.scheduler.is_scheduler_enabled', return_value=True)
    def test_scheduler_enabled(self, mock_scheduler):
        """Test scheduler state"""
        # Test with scheduler enabled
        self.assertTrue(frappe.utils.scheduler.is_scheduler_enabled())
```

---

## Advanced Testing Patterns

### Testing with Database Migrations

```python
class TestMigrations(FrappeTestCase):
    def test_migration_script(self):
        """Test database migration scripts"""
        # Create old structure
        # Run migration
        # Verify new structure
        pass
    
    def test_migration_rollback(self):
        """Test migration rollback"""
        # Run migration
        # Rollback
        # Verify original state
        pass
```

### Testing with Custom Fields

```python
from frappe.custom.doctype.custom_field.custom_field import create_custom_field

class TestCustomFields(FrappeTestCase):
    def setUp(self):
        super().setUp()
        # Create custom field
        self.custom_field = create_custom_field(
            "MyDocType",
            {
                "label": "Custom Field",
                "fieldname": "custom_field",
                "fieldtype": "Data"
            }
        )
    
    def tearDown(self):
        # Cleanup custom field
        if self.custom_field:
            self.custom_field.delete()
        super().tearDown()
    
    def test_custom_field_usage(self):
        """Test using custom field"""
        doc = frappe.get_doc({
            "doctype": "MyDocType",
            "field1": "value1",
            "custom_field": "custom_value"
        })
        doc.insert()
        
        self.assertEqual(doc.custom_field, "custom_value")
```

### Testing with Patches

```python
class TestPatches(FrappeTestCase):
    def test_patch_execution(self):
        """Test patch execution"""
        # Verify patch hasn't run
        # Run patch
        # Verify patch has run
        pass
    
    def test_patch_idempotency(self):
        """Test that patches are idempotent"""
        # Run patch multiple times
        # Should not cause errors
        pass
```

### Testing Error Recovery

```python
class TestErrorRecovery(FrappeTestCase):
    def test_retry_on_failure(self):
        """Test retry logic on failures"""
        attempt_count = []
        
        def failing_function():
            attempt_count.append(1)
            if len(attempt_count) < 3:
                raise Exception("Temporary failure")
            return "success"
        
        # Retry logic
        max_retries = 5
        for i in range(max_retries):
            try:
                result = failing_function()
                break
            except Exception:
                if i == max_retries - 1:
                    raise
                time.sleep(0.1)
        
        self.assertEqual(result, "success")
        self.assertEqual(len(attempt_count), 3)
```

---

## Summary

This guide has covered advanced testing techniques for Frappe:

### Key Advanced Techniques

1. **Mocking and Patching**: Isolate code under test and avoid side effects
2. **Background Jobs**: Test async operations and job queues
3. **Hooks**: Test Frappe's hook system and extensions
4. **External Services**: Mock HTTP requests and external APIs
5. **Transactions**: Test transaction behavior and isolation
6. **Concurrency**: Test race conditions and locking
7. **Performance**: Test query optimization and caching
8. **Caching**: Test cache behavior and invalidation
9. **Custom Methods**: Test custom business logic
10. **Context Managers**: Use advanced context managers for test setup
11. **Multiple Sites**: Test multi-tenant scenarios
12. **Async Operations**: Test asynchronous and event-driven code

### Best Practices for Advanced Testing

1. **Use Mocking Sparingly**: Only mock when necessary
2. **Test Real Behavior**: Prefer testing actual behavior over mocks
3. **Isolate Tests**: Each test should be independent
4. **Test Edge Cases**: Test error conditions and edge cases
5. **Performance Testing**: Monitor query counts and cache usage
6. **Document Complex Tests**: Explain complex test scenarios

### When to Use Advanced Techniques

- **Mocking**: External APIs, expensive operations, time-dependent code
- **Background Jobs**: Long-running operations, scheduled tasks
- **Hooks**: Testing app extensions and customizations
- **Transactions**: Testing data integrity and rollback scenarios
- **Concurrency**: Testing race conditions and locking
- **Performance**: Identifying bottlenecks and optimization opportunities

### Additional Resources

- [Frappe Testing Documentation](https://docs.frappe.io/framework/user/en/testing)
- [Python unittest Documentation](https://docs.python.org/3/library/unittest.html)
- [Frappe Source Code Tests](https://github.com/frappe/frappe/tree/develop/frappe/tests)

### Next Steps

Continue to:
- [Part 1: Fundamentals](./63-Frappe_Unit_Testing_Guide_Part_1_Fundamentals.md)
- [Part 2: Test Commands and Execution](./64-Frappe_Unit_Testing_Guide_Part_2_Test_Commands.md)
- [Part 3: Test Patterns and Best Practices](./65-Frappe_Unit_Testing_Guide_Part_3_Patterns.md)
- [Part 5: Test Data Management](./67-Frappe_Unit_Testing_Guide_Part_5_Test_Data.md)
- [Part 6: Test Utilities and Techniques](./68-Frappe_Unit_Testing_Guide_Part_6_Utilities.md)
- [Part 7: Assertions](./69-Frappe_Unit_Testing_Guide_Part_7_Assertions.md)
- [Part 8: Reports](./80-Frappe_Unit_Testing_Guide_Part_8_Reports.md)
- [Part 9: Test Records](./82-Frappe_Unit_Testing_Guide_Part_9_Test_Records.md)

---

**Remember**: Advanced testing techniques should be used judiciously. Start with simple tests and add complexity only when necessary. The goal is to write maintainable, reliable tests that provide confidence in your code.


# Frappe Unit Testing Guide - Part 5: Test Data Management

## Table of Contents
1. [Introduction](#introduction)
2. [test_records.json Files](#test_recordsjson-files)
3. [Test Dependencies](#test-dependencies)
4. [Programmatic Test Data Creation](#programmatic-test-data-creation)
5. [The _make_test_records Function](#the-_make_test_records-function)
6. [Test Data in Test Files](#test-data-in-test-files)
7. [Managing Test Fixtures](#managing-test-fixtures)
8. [Test Data Cleanup](#test-data-cleanup)
9. [Best Practices](#best-practices)
10. [Common Patterns](#common-patterns)
11. [Troubleshooting Test Data](#troubleshooting-test-data)

---

## Introduction

Effective test data management is crucial for reliable and maintainable tests. Frappe provides several mechanisms for creating and managing test data:

- **test_records.json**: JSON files containing test data definitions
- **test_dependencies**: Automatic dependency resolution
- **_make_test_records()**: Programmatic test data creation
- **test_records variable**: In-memory test data definitions

This guide covers all aspects of test data management in Frappe.

---

## test_records.json Files

The simplest way to define test data is using `test_records.json` files. These files are automatically discovered and used by Frappe's test runner.

### File Location

Test records JSON files must be located in the DocType's directory:

```
your_app/
└── your_app/
    └── module/
        └── doctype/
            └── doctype_name/
                ├── doctype_name.py
                ├── test_doctype_name.py
                └── test_records.json  ← Here
```

**Example Path**: `apps/frappe/frappe/core/doctype/user/test_records.json`

### File Structure

`test_records.json` is a JSON array where each object represents a test record:

```json
[
  {
    "doctype": "MyDocType",
    "field1": "value1",
    "field2": "value2"
  },
  {
    "doctype": "MyDocType",
    "field1": "value3",
    "field2": "value4"
  }
]
```

### Complete Example

```json
[
  {
    "doctype": "User",
    "email": "test@example.com",
    "enabled": 1,
    "first_name": "_Test",
    "new_password": "SecurePassword123",
    "roles": [
      {
        "doctype": "Has Role",
        "parentfield": "roles",
        "role": "System Manager"
      }
    ]
  },
  {
    "doctype": "User",
    "email": "test1@example.com",
    "first_name": "_Test1",
    "new_password": "SecurePassword123",
    "enabled": 1
  }
]
```

### Key Features

1. **Automatic Discovery**: Frappe automatically finds and loads `test_records.json` files
2. **Automatic Creation**: Records are created automatically when tests run
3. **Dependency Resolution**: Linked DocTypes are automatically created first
4. **Naming Series**: Automatic naming series handling
5. **Child Tables**: Support for child table records

### Child Table Records

Include child table records in the JSON:

```json
[
  {
    "doctype": "Sales Invoice",
    "customer": "_Test Customer",
    "company": "_Test Company",
    "items": [
      {
        "doctype": "Sales Invoice Item",
        "parentfield": "items",
        "item_code": "_Test Item",
        "qty": 10,
        "rate": 100
      },
      {
        "doctype": "Sales Invoice Item",
        "parentfield": "items",
        "item_code": "_Test Item 2",
        "qty": 5,
        "rate": 50
      }
    ]
  }
]
```

### Submitted Documents

Set `docstatus` to 1 to create submitted documents:

```json
[
  {
    "doctype": "Sales Invoice",
    "customer": "_Test Customer",
    "company": "_Test Company",
    "docstatus": 1,
    "items": [
      {
        "doctype": "Sales Invoice Item",
        "parentfield": "items",
        "item_code": "_Test Item",
        "qty": 10,
        "rate": 100
      }
    ]
  }
]
```

**Note**: Documents with `docstatus: 1` are automatically submitted after insertion.

### Fixed Names

You can specify fixed names for test records:

```json
[
  {
    "doctype": "MyDocType",
    "name": "_Test Fixed Name",
    "field1": "value1"
  }
]
```

**Important**: If a document with the specified name already exists, it won't be recreated unless `force=True` is used.

### Naming Series

If you don't specify a name, Frappe will:
1. Use the naming series if specified in the record
2. Use default naming series `_T-{DocType}-` if no series is specified
3. Generate a unique name automatically

```json
[
  {
    "doctype": "MyDocType",
    "naming_series": "TEST-",
    "field1": "value1"
  }
]
```

---

## Test Dependencies

Frappe automatically resolves dependencies when creating test records. Dependencies are DocTypes that are linked to your DocType.

### Automatic Dependency Resolution

Frappe automatically:
1. Finds all Link fields in your DocType
2. Finds all Link fields in child tables
3. Creates test records for all linked DocTypes first
4. Handles circular dependencies

### Explicit Dependencies

You can explicitly declare dependencies in your test file:

```python
# test_my_doctype.py
import frappe
from frappe.tests.utils import FrappeTestCase

# Declare explicit dependencies
test_dependencies = ["Company", "Customer", "Item"]

class TestMyDocType(FrappeTestCase):
    def test_something(self):
        # Company, Customer, and Item test records are created first
        pass
```

### How Dependencies Work

1. **Link Fields**: All Link fields are automatically detected
2. **Child Tables**: Link fields in child tables are also detected
3. **Explicit Dependencies**: `test_dependencies` list adds additional dependencies
4. **Recursive**: Dependencies of dependencies are also created
5. **Ordering**: Dependencies are created in the correct order

### Example: Complex Dependencies

```python
# test_sales_invoice.py
test_dependencies = ["Company", "Customer", "Item", "Price List"]

class TestSalesInvoice(FrappeTestCase):
    # Sales Invoice has:
    # - Link to Company
    # - Link to Customer
    # - Child table with Link to Item
    # - Link to Price List (explicit dependency)
    
    # All these will be created automatically:
    # 1. Company (and its dependencies)
    # 2. Customer (and its dependencies)
    # 3. Item (and its dependencies)
    # 4. Price List (and its dependencies)
    # 5. Sales Invoice
    pass
```

### Ignoring Dependencies

You can ignore certain dependencies:

```python
# test_my_doctype.py
test_dependencies = ["Company", "Customer"]
test_ignore = ["User"]  # Don't create User test records

class TestMyDocType(FrappeTestCase):
    pass
```

**Use Cases**:
- When a dependency is too expensive to create
- When a dependency is not needed for your tests
- When a dependency causes issues

### Global Test Dependencies

Define dependencies that apply to all tests in an app:

```python
# your_app/your_app/tests/__init__.py
global_test_dependencies = ["User", "Company"]
```

These dependencies are created once for all tests in the app.

---

## Programmatic Test Data Creation

Sometimes you need to create test data programmatically, especially when:
- Data depends on runtime conditions
- Data needs to be generated dynamically
- Complex logic is required

### Using frappe.get_doc()

The most common way to create test data programmatically:

```python
class TestMyDocType(FrappeTestCase):
    def test_with_programmatic_data(self):
        # Create test document
        doc = frappe.get_doc({
            "doctype": "MyDocType",
            "field1": "value1",
            "field2": "value2"
        })
        doc.insert()
        
        # Use the document in tests
        self.assertEqual(doc.field1, "value1")
```

### Using frappe.new_doc()

Create a new document instance:

```python
def test_with_new_doc(self):
    doc = frappe.new_doc("MyDocType")
    doc.field1 = "value1"
    doc.field2 = "value2"
    doc.insert()
    
    self.assertIsNotNone(doc.name)
```

### Creating Multiple Records

```python
def test_multiple_records(self):
    records = []
    for i in range(5):
        doc = frappe.get_doc({
            "doctype": "MyDocType",
            "field1": f"value_{i}",
            "field2": i * 10
        })
        doc.insert()
        records.append(doc.name)
    
    # Verify all records created
    self.assertEqual(len(records), 5)
    for name in records:
        self.assertTrue(frappe.db.exists("MyDocType", name))
```

### Creating Records with Child Tables

```python
def test_with_child_table(self):
    doc = frappe.get_doc({
        "doctype": "Sales Invoice",
        "customer": "_Test Customer",
        "company": "_Test Company",
        "items": []
    })
    
    # Add child records
    doc.append("items", {
        "item_code": "_Test Item",
        "qty": 10,
        "rate": 100
    })
    doc.append("items", {
        "item_code": "_Test Item 2",
        "qty": 5,
        "rate": 50
    })
    
    doc.insert()
    
    self.assertEqual(len(doc.items), 2)
```

### Using Helper Functions

Create reusable helper functions:

```python
class TestMyDocType(FrappeTestCase):
    def create_test_document(self, **kwargs):
        """Helper to create test document"""
        defaults = {
            "doctype": "MyDocType",
            "field1": "default_value1",
            "field2": "default_value2"
        }
        defaults.update(kwargs)
        doc = frappe.get_doc(defaults)
        doc.insert()
        return doc
    
    def test_scenario_one(self):
        doc = self.create_test_document(field1="custom_value")
        # Test logic
    
    def test_scenario_two(self):
        doc = self.create_test_document(
            field1="value1",
            field2="value2"
        )
        # Test logic
```

### Creating Related Records

```python
def test_related_records(self):
    # Create parent
    parent = frappe.get_doc({
        "doctype": "Company",
        "company_name": "_Test Company",
        "abbr": "_TC"
    })
    parent.insert()
    
    # Create child with reference to parent
    child = frappe.get_doc({
        "doctype": "Customer",
        "customer_name": "_Test Customer",
        "company": parent.name
    })
    child.insert()
    
    # Verify relationship
    self.assertEqual(child.company, parent.name)
```

---

## The _make_test_records Function

For complex test data that requires programmatic generation, use the `_make_test_records()` function.

### Function Signature

```python
def _make_test_records(verbose=None):
    """
    Create test records programmatically.
    
    Args:
        verbose: If True, print progress messages
    
    Returns:
        List of document names created
    """
    pass
```

### When to Use _make_test_records

Use `_make_test_records()` when:
- Test data depends on other records that must be created first
- You need to create records for multiple companies/sites
- Complex logic is required to generate test data
- You need to create many variations of records

### Basic Example

```python
# test_my_doctype.py
from frappe.test_runner import make_test_objects

def _make_test_records(verbose=None):
    """Create test records for MyDocType"""
    records = []
    
    # Create test records
    test_data = [
        {
            "doctype": "MyDocType",
            "field1": "value1",
            "field2": "value2"
        },
        {
            "doctype": "MyDocType",
            "field1": "value3",
            "field2": "value4"
        }
    ]
    
    records = make_test_objects("MyDocType", test_data, verbose=verbose)
    return records
```

### Advanced Example: Multiple Companies

```python
def _make_test_records(verbose=None):
    """Create test records for multiple companies"""
    from frappe.test_runner import make_test_objects
    
    records = []
    
    companies = [
        ("_Test Company", "_TC"),
        ("_Test Company 1", "_TC1")
    ]
    
    for company_name, abbr in companies:
        test_data = [
            {
                "doctype": "Account",
                "account_name": f"_Test Account - {company_name}",
                "company": company_name,
                "parent_account": f"Accounts Receivable - {abbr}",
                "account_type": "Receivable"
            }
        ]
        
        company_records = make_test_objects("Account", test_data, verbose=verbose)
        records.extend(company_records)
    
    return records
```

### Using make_test_objects

The `make_test_objects()` function is used internally by Frappe:

```python
from frappe.test_runner import make_test_objects

def _make_test_records(verbose=None):
    test_data = [
        {
            "doctype": "MyDocType",
            "field1": "value1"
        }
    ]
    
    # make_test_objects returns list of document names
    records = make_test_objects(
        "MyDocType",
        test_data,
        verbose=verbose,
        reset=False,  # Don't recreate if exists
        commit=False  # Don't commit after each record
    )
    
    return records
```

### Parameters for make_test_objects

- `doctype`: DocType name
- `test_records`: List of dictionaries (test data)
- `verbose`: Print progress messages
- `reset`: If True, recreate records even if they exist
- `commit`: If True, commit after each record

### Real-World Example

From `erpnext/accounts/doctype/account/test_account.py`:

```python
def _make_test_records(verbose=None):
    from frappe.test_runner import make_test_objects
    
    accounts = [
        # [account_name, parent_account, is_group, account_type, currency]
        ["_Test Bank", "Bank Accounts", 0, "Bank", None],
        ["_Test Cash", "Cash In Hand", 0, "Cash", None],
        ["_Test Account Stock Expenses", "Direct Expenses", 1, None, None],
    ]
    
    records = []
    for company, abbr in [
        ("_Test Company", "_TC"),
        ("_Test Company 1", "_TC1"),
    ]:
        test_objects = make_test_objects(
            "Account",
            [
                {
                    "doctype": "Account",
                    "account_name": account_name,
                    "parent_account": parent_account + " - " + abbr,
                    "company": company,
                    "is_group": is_group,
                    "account_type": account_type,
                    "account_currency": currency,
                }
                for account_name, parent_account, is_group, account_type, currency in accounts
            ],
        )
        records.extend(test_objects)
    
    return records
```

---

## Test Data in Test Files

You can also define test data directly in your test files.

### Using test_records Variable

```python
# test_my_doctype.py
import frappe
from frappe.tests.utils import FrappeTestCase

# Define test records in the test file
test_records = frappe.get_test_records("MyDocType")

# Or define directly
test_records = [
    {
        "doctype": "MyDocType",
        "field1": "value1"
    },
    {
        "doctype": "MyDocType",
        "field1": "value2"
    }
]

class TestMyDocType(FrappeTestCase):
    def setUp(self):
        # Load test records
        self.test_records = frappe.get_test_records("MyDocType")
        # Or use the module variable
        self.test_records = test_records
    
    def test_with_test_records(self):
        # Use test records
        doc = frappe.get_doc(self.test_records[0])
        doc.insert()
        
        self.assertEqual(doc.field1, "value1")
```

### Loading from JSON

```python
# Load from test_records.json
test_records = frappe.get_test_records("MyDocType")

class TestMyDocType(FrappeTestCase):
    def test_using_json_records(self):
        # Use records from JSON file
        for record in test_records:
            doc = frappe.get_doc(record)
            doc.insert()
            # Test logic
```

### Example from Frappe Core

```python
# frappe/desk/doctype/event/test_event.py
test_records = frappe.get_test_records("Event")

class TestEvent(FrappeTestCase):
    def setUp(self):
        self.test_records = frappe.get_test_records("Event")
    
    def test_with_records(self):
        ev = frappe.get_doc(self.test_records[0])
        ev.insert()
        name = ev.name
        
        # Delete and recreate
        frappe.delete_doc("Event", ev.name)
        ev = frappe.get_doc(self.test_records[0])
        ev.insert()
        
        # Name should be the same (due to naming series reversion)
        self.assertEqual(ev.name, name)
```

---

## Managing Test Fixtures

Test fixtures are reusable test data that can be shared across multiple tests.

### Class-Level Fixtures

Use `setUpClass` for expensive fixtures:

```python
class TestMyDocType(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Create shared fixtures
        cls.company = frappe.get_doc({
            "doctype": "Company",
            "company_name": "_Test Company",
            "abbr": "_TC"
        })
        if not frappe.db.exists("Company", cls.company.company_name):
            cls.company.insert()
        else:
            cls.company = frappe.get_doc("Company", "_Test Company")
        
        cls.customer = frappe.get_doc({
            "doctype": "Customer",
            "customer_name": "_Test Customer"
        })
        if not frappe.db.exists("Customer", cls.customer.customer_name):
            cls.customer.insert()
        else:
            cls.customer = frappe.get_doc("Customer", "_Test Customer")
        
        frappe.db.commit()  # Commit for sharing across tests
    
    def test_with_fixtures(self):
        # Use cls.company and cls.customer
        doc = frappe.get_doc({
            "doctype": "MyDocType",
            "company": self.company.name,
            "customer": self.customer.name
        })
        doc.insert()
```

### Method-Level Fixtures

Use `setUp` for per-test fixtures:

```python
class TestMyDocType(FrappeTestCase):
    def setUp(self):
        super().setUp()
        
        # Create fresh fixtures for each test
        self.test_doc = frappe.get_doc({
            "doctype": "MyDocType",
            "field1": "test_value"
        })
        self.test_doc.insert()
    
    def test_one(self):
        # Use self.test_doc
        pass
    
    def test_two(self):
        # Use self.test_doc (fresh instance)
        pass
```

### Shared Fixture Functions

Create reusable fixture functions:

```python
# test_fixtures.py or in test file
def create_test_company(company_name="_Test Company", abbr="_TC"):
    """Create a test company"""
    if frappe.db.exists("Company", company_name):
        return frappe.get_doc("Company", company_name)
    
    company = frappe.get_doc({
        "doctype": "Company",
        "company_name": company_name,
        "abbr": abbr
    })
    company.insert()
    return company

def create_test_customer(customer_name="_Test Customer"):
    """Create a test customer"""
    if frappe.db.exists("Customer", customer_name):
        return frappe.get_doc("Customer", customer_name)
    
    customer = frappe.get_doc({
        "doctype": "Customer",
        "customer_name": customer_name
    })
    customer.insert()
    return customer

# Use in tests
class TestMyDocType(FrappeTestCase):
    def test_with_fixtures(self):
        company = create_test_company()
        customer = create_test_customer()
        
        doc = frappe.get_doc({
            "doctype": "MyDocType",
            "company": company.name,
            "customer": customer.name
        })
        doc.insert()
```

### Fixture Cleanup

Frappe automatically rolls back database changes, but you may need to clean up:

```python
class TestMyDocType(FrappeTestCase):
    def setUp(self):
        super().setUp()
        self.created_docs = []
    
    def tearDown(self):
        # Cleanup if needed (usually not required due to auto-rollback)
        for doc_name in self.created_docs:
            if frappe.db.exists("MyDocType", doc_name):
                frappe.delete_doc("MyDocType", doc_name, force=1)
        super().tearDown()
    
    def test_something(self):
        doc = frappe.get_doc({
            "doctype": "MyDocType",
            "field1": "value1"
        })
        doc.insert()
        self.created_docs.append(doc.name)
```

---

## Test Data Cleanup

Frappe automatically handles test data cleanup, but understanding the process helps.

### Automatic Rollback

Frappe automatically rolls back all database changes after each test:

```python
class TestMyDocType(FrappeTestCase):
    def test_creates_data(self):
        # Create documents
        doc1 = frappe.get_doc({"doctype": "MyDocType", "field1": "value1"}).insert()
        doc2 = frappe.get_doc({"doctype": "MyDocType", "field1": "value2"}).insert()
        
        # Documents exist during test
        self.assertTrue(frappe.db.exists("MyDocType", doc1.name))
        self.assertTrue(frappe.db.exists("MyDocType", doc2.name))
    
    # After test: All changes are automatically rolled back
    # doc1 and doc2 no longer exist
```

### Test Record Log

Frappe maintains a log of created test records in `.test_log`:

```python
# Location: sites/{site}/.test_log
# Contains list of DocTypes for which test records were created
```

This log prevents recreating test records unnecessarily.

### Force Recreation

Force recreation of test records:

```python
# In test file
from frappe.test_runner import make_test_records_for_doctype

class TestMyDocType(FrappeTestCase):
    def setUp(self):
        super().setUp()
        # Force recreation of test records
        make_test_records_for_doctype("MyDocType", force=True)
```

Or when running tests:

```bash
bench --site test_site run-tests --doctype MyDocType --force
```

### Manual Cleanup

Sometimes manual cleanup is needed:

```python
class TestMyDocType(FrappeTestCase):
    def setUp(self):
        super().setUp()
        # Delete existing test records
        frappe.db.delete("MyDocType", {"name": ["like", "_Test%"]})
        frappe.db.commit()
    
    def test_something(self):
        # Create fresh test data
        pass
```

### Cleaning Up Test Records

```python
def cleanup_test_records(doctype, pattern="_Test%"):
    """Clean up test records matching pattern"""
    names = frappe.db.get_all(
        doctype,
        filters={"name": ["like", pattern]},
        pluck="name"
    )
    
    for name in names:
        try:
            frappe.delete_doc(doctype, name, force=1)
        except Exception:
            pass
    
    frappe.db.commit()
```

---

## Best Practices

### 1. Use Descriptive Names

**Good**:
```json
{
  "doctype": "User",
  "email": "test_accounts_manager@example.com",
  "first_name": "_Test Accounts Manager"
}
```

**Bad**:
```json
{
  "doctype": "User",
  "email": "test1@example.com",
  "first_name": "Test"
}
```

### 2. Use Consistent Naming Patterns

Use a consistent prefix for test data:

```json
[
  {
    "doctype": "Customer",
    "customer_name": "_Test Customer"
  },
  {
    "doctype": "Item",
    "item_code": "_Test Item"
  },
  {
    "doctype": "Company",
    "company_name": "_Test Company"
  }
]
```

**Common Prefixes**:
- `_Test` - Standard test prefix
- `_T-` - For naming series
- `TEST-` - Alternative prefix

### 3. Include All Required Fields

Ensure test records have all mandatory fields:

```json
{
  "doctype": "Sales Invoice",
  "customer": "_Test Customer",  // Required
  "company": "_Test Company",     // Required
  "posting_date": "2024-01-15",   // Required
  "items": [                      // Required child table
    {
      "doctype": "Sales Invoice Item",
      "parentfield": "items",
      "item_code": "_Test Item",  // Required
      "qty": 1,                   // Required
      "rate": 100                 // Required
    }
  ]
}
```

### 4. Use Realistic Data

Use realistic test data that represents real-world scenarios:

```json
{
  "doctype": "Item",
  "item_code": "_Test Laptop",
  "item_name": "Test Laptop Computer",
  "item_group": "Electronics",
  "stock_uom": "Unit",
  "is_stock_item": 1,
  "valuation_rate": 999.99
}
```

### 5. Document Complex Test Data

Add comments in code for complex test data:

```python
def _make_test_records(verbose=None):
    """
    Create test accounts for multiple companies.
    
    Creates:
    - Bank accounts for each company
    - Cash accounts for each company
    - Expense accounts for each company
    """
    # Implementation
    pass
```

### 6. Avoid Hard-Coded IDs

**Bad**:
```python
doc = frappe.get_doc("MyDocType", "DOC-00001")  # Assumes document exists
```

**Good**:
```python
doc = frappe.get_doc({
    "doctype": "MyDocType",
    "field1": "value1"
})
doc.insert()
# Use doc.name
```

### 7. Handle Dependencies Explicitly

```python
# Explicitly declare dependencies
test_dependencies = ["Company", "Customer", "Item"]

class TestMyDocType(FrappeTestCase):
    # Dependencies are created automatically
    pass
```

### 8. Reuse Test Records

```python
class TestMyDocType(FrappeTestCase):
    def setUp(self):
        super().setUp()
        # Load test records once
        self.test_records = frappe.get_test_records("MyDocType")
    
    def test_one(self):
        # Use test records
        doc = frappe.get_doc(self.test_records[0])
        doc.insert()
    
    def test_two(self):
        # Reuse same test records
        doc = frappe.get_doc(self.test_records[1])
        doc.insert()
```

### 9. Keep Test Data Minimal

Only include fields necessary for tests:

**Good**:
```json
{
  "doctype": "MyDocType",
  "field1": "value1",  // Only required fields
  "field2": "value2"   // Only fields used in tests
}
```

**Bad**:
```json
{
  "doctype": "MyDocType",
  "field1": "value1",
  "field2": "value2",
  "field3": "unused_value",  // Not used in tests
  "field4": "unused_value",  // Not used in tests
  // ... 20 more unused fields
}
```

### 10. Version Control Test Data

Keep test data in version control:
- `test_records.json` files should be committed
- Test data should be stable and predictable
- Avoid test data that changes frequently

---

## Common Patterns

### Pattern 1: Creating Test Data with Defaults

```python
class TestMyDocType(FrappeTestCase):
    DEFAULT_DATA = {
        "doctype": "MyDocType",
        "field1": "default_value1",
        "field2": "default_value2"
    }
    
    def create_test_doc(self, **overrides):
        """Create test document with defaults and overrides"""
        data = self.DEFAULT_DATA.copy()
        data.update(overrides)
        doc = frappe.get_doc(data)
        doc.insert()
        return doc
    
    def test_with_defaults(self):
        doc = self.create_test_doc()
        self.assertEqual(doc.field1, "default_value1")
    
    def test_with_overrides(self):
        doc = self.create_test_doc(field1="custom_value")
        self.assertEqual(doc.field1, "custom_value")
```

### Pattern 2: Factory Functions

```python
def make_test_user(email=None, roles=None, **kwargs):
    """Factory function to create test users"""
    if email is None:
        email = f"test_{frappe.generate_hash(length=8)}@example.com"
    
    defaults = {
        "doctype": "User",
        "email": email,
        "first_name": "_Test",
        "new_password": "TestPassword123",
        "enabled": 1,
        "roles": roles or []
    }
    defaults.update(kwargs)
    
    if frappe.db.exists("User", email):
        return frappe.get_doc("User", email)
    
    user = frappe.get_doc(defaults)
    user.insert()
    return user

# Use in tests
class TestMyDocType(FrappeTestCase):
    def test_with_factory(self):
        user = make_test_user(
            email="custom@test.com",
            roles=[{"role": "System Manager"}]
        )
        # Use user
```

### Pattern 3: Test Data Builders

```python
class TestDataBuilder:
    """Builder pattern for complex test data"""
    
    def __init__(self, doctype):
        self.doctype = doctype
        self.data = {"doctype": doctype}
        self.child_tables = {}
    
    def with_field(self, field, value):
        self.data[field] = value
        return self
    
    def with_child(self, child_field, child_data):
        if child_field not in self.child_tables:
            self.child_tables[child_field] = []
        self.child_tables[child_field].append(child_data)
        return self
    
    def build(self):
        """Build and insert document"""
        for field, children in self.child_tables.items():
            self.data[field] = children
        
        doc = frappe.get_doc(self.data)
        doc.insert()
        return doc

# Use builder
class TestMyDocType(FrappeTestCase):
    def test_with_builder(self):
        doc = (TestDataBuilder("Sales Invoice")
            .with_field("customer", "_Test Customer")
            .with_field("company", "_Test Company")
            .with_child("items", {
                "item_code": "_Test Item",
                "qty": 10,
                "rate": 100
            })
            .build())
        
        self.assertEqual(doc.customer, "_Test Customer")
```

### Pattern 4: Test Data Templates

```python
# Define templates
TEMPLATES = {
    "minimal_invoice": {
        "doctype": "Sales Invoice",
        "customer": "_Test Customer",
        "company": "_Test Company",
        "items": [{
            "item_code": "_Test Item",
            "qty": 1,
            "rate": 100
        }]
    },
    "full_invoice": {
        "doctype": "Sales Invoice",
        "customer": "_Test Customer",
        "company": "_Test Company",
        "posting_date": "2024-01-15",
        "due_date": "2024-02-15",
        "items": [
            {"item_code": "_Test Item", "qty": 10, "rate": 100},
            {"item_code": "_Test Item 2", "qty": 5, "rate": 50}
        ],
        "taxes": [{
            "charge_type": "On Net Total",
            "rate": 10
        }]
    }
}

def create_from_template(template_name, **overrides):
    """Create document from template"""
    template = TEMPLATES[template_name].copy()
    template.update(overrides)
    doc = frappe.get_doc(template)
    doc.insert()
    return doc

# Use templates
class TestSalesInvoice(FrappeTestCase):
    def test_minimal(self):
        doc = create_from_template("minimal_invoice")
        # Test minimal invoice
    
    def test_full(self):
        doc = create_from_template("full_invoice")
        # Test full invoice
    
    def test_customized(self):
        doc = create_from_template(
            "minimal_invoice",
            posting_date="2024-02-01"
        )
        # Test with custom date
```

### Pattern 5: Test Data Inheritance

```python
def get_base_test_data():
    """Base test data that can be extended"""
    return {
        "doctype": "MyDocType",
        "field1": "base_value1",
        "field2": "base_value2"
    }

def get_extended_test_data(**overrides):
    """Extended test data"""
    data = get_base_test_data()
    data.update(overrides)
    return data

# Use inheritance
class TestMyDocType(FrappeTestCase):
    def test_base(self):
        doc = frappe.get_doc(get_base_test_data())
        doc.insert()
    
    def test_extended(self):
        doc = frappe.get_doc(get_extended_test_data(
            field3="extended_value"
        ))
        doc.insert()
```

---

## Troubleshooting Test Data

### Problem: Test Records Not Created

**Symptoms**: Tests fail with "Record not found" errors

**Solutions**:
1. Check `test_records.json` exists and is valid JSON
2. Verify file location is correct
3. Check for JSON syntax errors
4. Ensure `test_dependencies` are correct
5. Run with `--verbose` to see creation messages

```bash
# Check JSON validity
python -m json.tool test_records.json

# Run with verbose output
bench --site test_site run-tests --doctype MyDocType --verbose
```

### Problem: Circular Dependencies

**Symptoms**: Tests hang or fail with dependency errors

**Solutions**:
1. Use `test_ignore` to break circular dependencies
2. Create records manually in `setUp`
3. Use `_make_test_records()` for complex scenarios

```python
# Break circular dependency
test_dependencies = ["Company"]
test_ignore = ["Account"]  # Ignore Account to break cycle

class TestMyDocType(FrappeTestCase):
    def setUp(self):
        super().setUp()
        # Create Account manually if needed
        if not frappe.db.exists("Account", "_Test Account"):
            # Create account
            pass
```

### Problem: Test Records Already Exist

**Symptoms**: Test records not recreated, tests use old data

**Solutions**:
1. Use `force=True` to recreate
2. Delete existing records in `setUp`
3. Use unique names for test records

```python
class TestMyDocType(FrappeTestCase):
    def setUp(self):
        super().setUp()
        # Delete existing test records
        frappe.db.delete("MyDocType", {"name": ["like", "_Test%"]})
        frappe.db.commit()
        
        # Recreate
        from frappe.test_runner import make_test_records_for_doctype
        make_test_records_for_doctype("MyDocType", force=True)
```

### Problem: Missing Required Fields

**Symptoms**: Validation errors when creating test records

**Solutions**:
1. Check DocType meta for required fields
2. Add all mandatory fields to test records
3. Use `ignore_mandatory` flag if appropriate

```python
def _make_test_records(verbose=None):
    # Check required fields
    meta = frappe.get_meta("MyDocType")
    required_fields = [f.fieldname for f in meta.fields if f.reqd]
    
    # Ensure all required fields are included
    test_data = {
        "doctype": "MyDocType",
        # Include all required fields
    }
    # ...
```

### Problem: Test Data Not Isolated

**Symptoms**: Tests interfere with each other

**Solutions**:
1. Use unique names for each test
2. Clean up in `tearDown`
3. Use `setUp` to create fresh data

```python
class TestMyDocType(FrappeTestCase):
    def setUp(self):
        super().setUp()
        # Create unique test data
        self.unique_id = frappe.generate_hash(length=8)
        self.test_doc = frappe.get_doc({
            "doctype": "MyDocType",
            "field1": f"test_{self.unique_id}"
        })
        self.test_doc.insert()
```

### Problem: Slow Test Data Creation

**Symptoms**: Tests run slowly due to test data creation

**Solutions**:
1. Use `setUpClass` for shared data
2. Skip test record creation when not needed
3. Optimize `_make_test_records()` function
4. Use `--skip-test-records` when records exist

```python
class TestMyDocType(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create expensive test data once
        cls.company = create_expensive_company()
        frappe.db.commit()
    
    def test_one(self):
        # Use cls.company (created once)
        pass
    
    def test_two(self):
        # Use cls.company (reused)
        pass
```

### Problem: Test Records with Special Characters

**Symptoms**: JSON parsing errors or validation issues

**Solutions**:
1. Escape special characters properly in JSON
2. Use Unicode escape sequences if needed
3. Validate JSON before committing

```json
{
  "doctype": "User",
  "email": "test'5@example.com",  // Single quote in email
  "first_name": "_Test'5"         // Single quote in name
}
```

### Problem: Child Table Records Not Created

**Symptoms**: Parent document created but child records missing

**Solutions**:
1. Ensure `doctype` and `parentfield` are specified
2. Check child table field name is correct
3. Verify child table structure matches DocType

```json
{
  "doctype": "Sales Invoice",
  "items": [
    {
      "doctype": "Sales Invoice Item",  // Required
      "parentfield": "items",            // Required
      "item_code": "_Test Item",
      "qty": 10,
      "rate": 100
    }
  ]
}
```

---

## Advanced Test Data Scenarios

### Scenario 1: Multi-Company Test Data

```python
def _make_test_records(verbose=None):
    """Create test data for multiple companies"""
    from frappe.test_runner import make_test_objects
    
    companies = [
        ("_Test Company", "_TC"),
        ("_Test Company 1", "_TC1"),
        ("_Test Company with perpetual inventory", "TCP1")
    ]
    
    records = []
    for company_name, abbr in companies:
        # Create company-specific test data
        test_data = [
            {
                "doctype": "Account",
                "account_name": "_Test Account",
                "company": company_name,
                "parent_account": f"Accounts Receivable - {abbr}"
            }
        ]
        
        company_records = make_test_objects("Account", test_data, verbose=verbose)
        records.extend(company_records)
    
    return records
```

### Scenario 2: Conditional Test Data

```python
def _make_test_records(verbose=None):
    """Create test data conditionally"""
    from frappe.test_runner import make_test_objects
    
    records = []
    
    # Create base records
    base_records = make_test_objects("MyDocType", [
        {"doctype": "MyDocType", "field1": "base"}
    ])
    records.extend(base_records)
    
    # Create conditional records based on settings
    if frappe.db.get_single_value("System Settings", "enable_feature_x"):
        conditional_records = make_test_objects("MyDocType", [
            {"doctype": "MyDocType", "field1": "conditional"}
        ])
        records.extend(conditional_records)
    
    return records
```

### Scenario 3: Test Data with Relationships

```python
def create_test_invoice_with_dependencies():
    """Create invoice with all dependencies"""
    # Create company
    company = frappe.get_doc({
        "doctype": "Company",
        "company_name": "_Test Company",
        "abbr": "_TC"
    })
    if not frappe.db.exists("Company", company.company_name):
        company.insert()
    
    # Create customer
    customer = frappe.get_doc({
        "doctype": "Customer",
        "customer_name": "_Test Customer"
    })
    if not frappe.db.exists("Customer", customer.customer_name):
        customer.insert()
    
    # Create item
    item = frappe.get_doc({
        "doctype": "Item",
        "item_code": "_Test Item",
        "item_name": "_Test Item",
        "item_group": "_Test Item Group",
        "stock_uom": "_Test UOM"
    })
    if not frappe.db.exists("Item", item.item_code):
        item.insert()
    
    # Create invoice
    invoice = frappe.get_doc({
        "doctype": "Sales Invoice",
        "company": company.name,
        "customer": customer.name,
        "items": [{
            "item_code": item.item_code,
            "qty": 10,
            "rate": 100
        }]
    })
    invoice.insert()
    
    return invoice
```

### Scenario 4: Test Data with Hooks

```python
def _make_test_records(verbose=None):
    """Create test data using hooks"""
    from frappe.test_runner import make_test_objects
    
    # Get test data from hooks
    test_data_hooks = frappe.get_hooks("test_data", app_name="my_app")
    
    records = []
    for hook_function in test_data_hooks:
        hook_data = frappe.get_attr(hook_function)()
        records.extend(hook_data)
    
    return records
```

---

## Summary

This guide has covered comprehensive test data management in Frappe:

### Key Concepts

1. **test_records.json**: Simple JSON-based test data definition
2. **test_dependencies**: Automatic dependency resolution
3. **_make_test_records()**: Programmatic test data creation
4. **Test Fixtures**: Reusable test data patterns
5. **Test Data Cleanup**: Automatic and manual cleanup strategies

### Test Data Methods

| Method | When to Use | Complexity |
|--------|-------------|------------|
| `test_records.json` | Simple, static test data | Low |
| `test_records` variable | In-memory test data | Low |
| `_make_test_records()` | Complex, dynamic test data | High |
| Programmatic creation | Test-specific data | Medium |
| Factory functions | Reusable test data | Medium |

### Best Practices Summary

1. ✅ Use descriptive, consistent naming
2. ✅ Include all required fields
3. ✅ Use realistic test data
4. ✅ Handle dependencies explicitly
5. ✅ Keep test data minimal
6. ✅ Document complex test data
7. ✅ Avoid hard-coded IDs
8. ✅ Reuse test records when possible
9. ✅ Clean up test data properly
10. ✅ Version control test data

### Quick Reference

**Create test records from JSON**:
```python
test_records = frappe.get_test_records("MyDocType")
doc = frappe.get_doc(test_records[0])
doc.insert()
```

**Declare dependencies**:
```python
test_dependencies = ["Company", "Customer", "Item"]
```

**Create programmatically**:
```python
def _make_test_records(verbose=None):
    from frappe.test_runner import make_test_objects
    return make_test_objects("MyDocType", test_data)
```

**Force recreation**:
```bash
bench --site test_site run-tests --doctype MyDocType --force
```

**Skip test records**:
```bash
bench --site test_site run-tests --skip-test-records
```

---

### Additional Resources

- [Frappe Testing Documentation](https://docs.frappe.io/framework/user/en/testing)
- [Python unittest Documentation](https://docs.python.org/3/library/unittest.html)
- [Frappe Source Code Tests](https://github.com/frappe/frappe/tree/develop/frappe/tests)

### Next Steps

Continue to:
- [Part 1: Fundamentals](./63-Frappe_Unit_Testing_Guide_Part_1_Fundamentals.md)
- [Part 2: Test Commands and Execution](./64-Frappe_Unit_Testing_Guide_Part_2_Test_Commands.md)
- [Part 3: Test Patterns and Best Practices](./65-Frappe_Unit_Testing_Guide_Part_3_Patterns.md)
- [Part 4: Advanced Testing Techniques](./66-Frappe_Unit_Testing_Guide_Part_4_Advanced.md)
- [Part 6: Test Utilities and Techniques](./68-Frappe_Unit_Testing_Guide_Part_6_Utilities.md)
- [Part 7: Assertions](./69-Frappe_Unit_Testing_Guide_Part_7_Assertions.md)
- [Part 8: Reports](./80-Frappe_Unit_Testing_Guide_Part_8_Reports.md)
- [Part 9: Test Records](./82-Frappe_Unit_Testing_Guide_Part_9_Test_Records.md)
# ERPNext & HRMS Test Utilities and Techniques Guide

## Table of Contents
1. [Introduction](#introduction)
2. [Factory Functions (make_ functions)](#factory-functions-make_-functions)
3. [Test Setup and Teardown Patterns](#test-setup-and-teardown-patterns)
4. [Helper Utilities](#helper-utilities)
5. [Assertion Helpers](#assertion-helpers)
6. [Test Mixins](#test-mixins)
7. [Common Test Patterns](#common-test-patterns)
8. [Best Practices](#best-practices)
9. [Complete Function Reference](#complete-function-reference)
10. [Advanced Patterns](#advanced-patterns)
11. [Quick Reference Cheat Sheet](#quick-reference-cheat-sheet)

---

## Introduction

This guide documents all the useful test utilities, helper functions, and techniques found in ERPNext and HRMS test files. These patterns can be reused in any custom Frappe application to write better, more maintainable tests.

### Key Concepts

- **Factory Functions**: Functions that create test objects (usually prefixed with `make_` or `create_`)
- **Test Mixins**: Reusable test classes that provide common functionality
- **Helper Utilities**: Utility functions for common test operations
- **Assertion Helpers**: Custom assertion methods for complex validations

---

## Factory Functions (make_ functions)

Factory functions are the most common pattern in ERPNext/HRMS tests. They create test documents with sensible defaults and allow customization through keyword arguments.

### Pattern Structure

```python
def make_doctype_name(**args):
    """Create a test document with defaults"""
    args = frappe._dict(args)
    
    doc = frappe.new_doc("DocType Name")
    doc.field1 = args.field1 or "default_value"
    doc.field2 = args.field2 or "default_value"
    
    if not args.do_not_save:
        doc.insert()
        if not args.do_not_submit:
            doc.submit()
    
    return doc
```

### Key Features

1. **Default Values**: Sensible defaults for all required fields
2. **Flexible Arguments**: Accept `**args` for customization
3. **Control Flags**: `do_not_save` and `do_not_submit` flags
4. **Return Document**: Always return the created document

### Example: make_purchase_receipt

```python
def make_purchase_receipt(**args):
    """Create a Purchase Receipt with defaults"""
    args = frappe._dict(args)
    pr = frappe.new_doc("Purchase Receipt")
    
    # Set defaults
    pr.posting_date = args.posting_date or today()
    pr.company = args.company or "_Test Company"
    pr.supplier = args.supplier or "_Test Supplier"
    pr.currency = args.currency or "INR"
    
    # Add item
    qty = args.qty if args.qty is not None else 5
    item_code = args.item or args.item_code or "_Test Item"
    
    pr.append("items", {
        "item_code": item_code,
        "warehouse": args.warehouse or "_Test Warehouse - _TC",
        "qty": qty,
        "rate": args.rate if args.rate is not None else 50,
    })
    
    # Control flags
    if not args.do_not_save:
        pr.insert()
        if not args.do_not_submit:
            pr.submit()
        pr.load_from_db()
    
    return pr
```

### Usage Examples

```python
# Basic usage
pr = make_purchase_receipt()

# Custom quantity
pr = make_purchase_receipt(qty=10)

# Custom item and rate
pr = make_purchase_receipt(item_code="_Test Item 2", rate=100)

# Don't submit
pr = make_purchase_receipt(do_not_submit=True)

# Don't save (for validation testing)
pr = make_purchase_receipt(do_not_save=True)
```

### Common Factory Functions in ERPNext

| Function | Location | Purpose |
|----------|----------|---------|
| `make_item()` | `erpnext.stock.doctype.item.test_item` | Create test items |
| `make_purchase_receipt()` | `erpnext.stock.doctype.purchase_receipt.test_purchase_receipt` | Create purchase receipts |
| `make_sales_invoice()` | `erpnext.accounts.doctype.sales_invoice.test_sales_invoice` | Create sales invoices |
| `make_stock_entry()` | `erpnext.stock.doctype.stock_entry.test_stock_entry` | Create stock entries |
| `make_purchase_order()` | `erpnext.buying.doctype.purchase_order.test_purchase_order` | Create purchase orders |
| `make_sales_order()` | `erpnext.selling.doctype.sales_order.test_sales_order` | Create sales orders |
| `make_delivery_note()` | `erpnext.stock.doctype.delivery_note.test_delivery_note` | Create delivery notes |
| `make_journal_entry()` | `erpnext.accounts.doctype.journal_entry.test_journal_entry` | Create journal entries |
| `make_payment_entry()` | `erpnext.accounts.doctype.payment_entry.test_payment_entry` | Create payment entries |
| `make_serial_batch_bundle()` | `erpnext.stock.doctype.serial_and_batch_bundle.test_serial_and_batch_bundle` | Create serial/batch bundles |
| `make_employee()` | `erpnext.setup.doctype.employee.test_employee` | **Create test employees (MOST IMPORTANT!)** |

### Common Factory Functions in HRMS

| Function | Location | Purpose |
|----------|----------|---------|
| `make_employee_salary_slip()` | `hrms.payroll.doctype.salary_slip.test_salary_slip` | Create salary slips |
| `make_salary_structure()` | `hrms.payroll.doctype.salary_structure.test_salary_structure` | Create salary structures |
| `make_leave_application()` | `hrms.hr.doctype.leave_application.test_leave_application` | Create leave applications |
| `make_holiday_list()` | `hrms.payroll.doctype.salary_slip.test_salary_slip` | Create holiday lists |
| `make_payroll_period()` | `hrms.payroll.doctype.salary_slip.test_salary_slip` | Create payroll periods |
| `make_shift_assignment()` | `hrms.hr.doctype.shift_type.test_shift_type` | Create shift assignments |
| `make_shift_request()` | `hrms.hr.doctype.shift_request.test_shift_request` | Create shift requests |
| `make_expense_claim()` | `hrms.hr.doctype.expense_claim.test_expense_claim` | Create expense claims |
| `make_employee_advance()` | `hrms.hr.doctype.employee_advance.test_employee_advance` | Create employee advances |

---

## Test Setup and Teardown Patterns

### Class-Level Setup (setUpClass)

Use `setUpClass` for expensive operations that can be shared across all tests in a class:

```python
class TestMyDocType(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create shared test data
        cls.company = create_company()
        cls.customer = create_customer()
        frappe.db.commit()  # Commit for sharing across tests
    
    def test_one(self):
        # Use cls.company and cls.customer
        pass
    
    def test_two(self):
        # Reuse cls.company and cls.customer
        pass
```

### Method-Level Setup (setUp)

Use `setUp` for per-test setup that needs to be fresh for each test:

```python
class TestMyDocType(FrappeTestCase):
    def setUp(self):
        super().setUp()
        # Create fresh test data for each test
        self.test_doc = make_test_document()
    
    def test_one(self):
        # Use self.test_doc
        pass
    
    def test_two(self):
        # Use self.test_doc (fresh instance)
        pass
```

### Cleanup Patterns

```python
class TestMyDocType(FrappeTestCase):
    def setUp(self):
        super().setUp()
        # Clean up before test
        frappe.db.delete("MyDocType", {"name": ["like", "_Test%"]})
        frappe.db.commit()
    
    def tearDown(self):
        # Clean up after test (usually not needed due to auto-rollback)
        frappe.db.rollback()
        super().tearDown()
```

### before_tests Hook

Use `before_tests` hook for global test setup:

```python
# In your_app/your_app/tests/__init__.py or hooks.py
def before_tests():
    frappe.clear_cache()
    
    # Setup if missing
    if not frappe.db.a_row_exists("Company"):
        setup_complete({...})
    
    # Set defaults
    set_defaults_for_tests()
    frappe.db.commit()
```

---

## Helper Utilities

### Date Utilities

```python
from frappe.utils import (
    add_days,
    add_months,
    get_first_day,
    get_last_day,
    get_year_start,
    get_year_ending,
    getdate,
    nowdate,
    today,
)

# Get first Sunday of month (HRMS pattern)
def get_first_sunday(holiday_list="Salary Slip Test Holiday List", for_date=None):
    date = for_date or getdate()
    month_start_date = get_first_day(date)
    month_end_date = get_last_day(date)
    
    first_sunday = frappe.db.sql(
        """
        select holiday_date from `tabHoliday`
        where parent = %s
            and holiday_date between %s and %s
        order by holiday_date
        """,
        (holiday_list, month_start_date, month_end_date),
    )[0][0]
    
    return first_sunday
```

### Company Utilities

```python
def create_company(name="_Test Company", is_group=0, parent_company=None):
    """Create a test company"""
    if frappe.db.exists("Company", name):
        return frappe.get_doc("Company", name)
    
    return frappe.get_doc({
        "doctype": "Company",
        "company_name": name,
        "default_currency": "INR",
        "country": "India",
        "is_group": is_group,
        "parent_company": parent_company,
    }).insert()
```

### Department Utilities

```python
def create_department(name, company="_Test Company"):
    """Create a test department"""
    from erpnext.setup.doctype.department.department import get_abbreviated_name
    
    docname = get_abbreviated_name(name, company)
    
    if frappe.db.exists("Department", docname):
        return docname
    
    department = frappe.new_doc("Department")
    department.update({
        "doctype": "Department",
        "department_name": name,
        "company": company
    })
    department.insert()
    return department.name
```

### Email Utilities

```python
def get_email_by_subject(subject):
    """Get email by subject from Email Queue"""
    return frappe.db.exists("Email Queue", {"message": ("like", f"%{subject}%")})
```

### Holiday List Utilities

```python
def add_date_to_holiday_list(date, holiday_list):
    """Add a date to holiday list"""
    if frappe.db.exists("Holiday", {"parent": holiday_list, "holiday_date": date}):
        return
    
    holiday_list_doc = frappe.get_doc("Holiday List", holiday_list)
    holiday_list_doc.append("holidays", {
        "holiday_date": date,
        "description": "test",
    })
    holiday_list_doc.save()
```

---

## Assertion Helpers

### Stock Ledger Entry Assertions

```python
class StockTestMixin:
    """Mixin for stock ledger tests"""
    
    def assertSLEs(self, doc, expected_sles, sle_filters=None):
        """Compare sorted Stock Ledger Entries"""
        filters = {
            "voucher_no": doc.name,
            "voucher_type": doc.doctype,
            "is_cancelled": 0
        }
        if sle_filters:
            filters.update(sle_filters)
        
        sles = frappe.get_all(
            "Stock Ledger Entry",
            fields=["*"],
            filters=filters,
            order_by="timestamp(posting_date, posting_time), creation",
        )
        
        self.assertGreaterEqual(len(sles), len(expected_sles))
        
        for exp_sle, act_sle in zip(expected_sles, sles, strict=False):
            for k, v in exp_sle.items():
                act_value = act_sle[k]
                if k == "stock_queue":
                    act_value = json.loads(act_value)
                    if act_value and act_value[0][0] == 0:
                        continue
                
                self.assertEqual(v, act_value, msg=f"{k} doesn't match")
```

### GL Entry Assertions

```python
def assertGLEs(self, doc, expected_gles, gle_filters=None, order_by=None):
    """Compare General Ledger Entries"""
    filters = {
        "voucher_no": doc.name,
        "voucher_type": doc.doctype,
        "is_cancelled": 0
    }
    
    if gle_filters:
        filters.update(gle_filters)
    
    actual_gles = frappe.get_all(
        "GL Entry",
        fields=["*"],
        filters=filters,
        order_by=order_by or "posting_date, creation",
    )
    
    self.assertGreaterEqual(len(actual_gles), len(expected_gles))
    
    for exp_gle, act_gle in zip(expected_gles, actual_gles, strict=False):
        for k, exp_value in exp_gle.items():
            act_value = act_gle[k]
            self.assertEqual(exp_value, act_value, msg=f"{k} doesn't match")
```

### Usage Example

```python
class TestStockEntry(FrappeTestCase, StockTestMixin):
    def test_stock_entry_sle(self):
        se = make_stock_entry(
            item_code="_Test Item",
            qty=10,
            source="_Test Warehouse - _TC",
            target="_Test Warehouse 1 - _TC"
        )
        
        expected_sles = [
            {
                "item_code": "_Test Item",
                "warehouse": "_Test Warehouse - _TC",
                "actual_qty": -10,
            },
            {
                "item_code": "_Test Item",
                "warehouse": "_Test Warehouse 1 - _TC",
                "actual_qty": 10,
            },
        ]
        
        self.assertSLEs(se, expected_sles)
```

---

## Test Mixins

### StockTestMixin

```python
class StockTestMixin:
    """Mixin to simplify stock ledger tests"""
    
    def make_item(self, item_code=None, properties=None, *args, **kwargs):
        """Helper to create items"""
        from erpnext.stock.doctype.item.test_item import make_item
        return make_item(item_code, properties, *args, **kwargs)
    
    def assertSLEs(self, doc, expected_sles, sle_filters=None):
        """Assert Stock Ledger Entries"""
        # ... implementation
    
    def assertGLEs(self, doc, expected_gles, gle_filters=None, order_by=None):
        """Assert GL Entries"""
        # ... implementation
```

### Usage

```python
class TestMyStockDocType(FrappeTestCase, StockTestMixin):
    def test_stock_transaction(self):
        item = self.make_item()
        # Use self.assertSLEs() and self.assertGLEs()
```

---

## Common Test Patterns

### Pattern 1: Testing Document Lifecycle

```python
def test_document_lifecycle(self):
    # Create
    doc = make_test_document()
    self.assertEqual(doc.status, "Draft")
    
    # Submit
    doc.submit()
    self.assertEqual(doc.status, "Submitted")
    
    # Cancel
    doc.cancel()
    self.assertEqual(doc.status, "Cancelled")
```

### Pattern 2: Testing with Multiple Items

```python
def test_multiple_items(self):
    doc = make_test_document(do_not_save=True)
    
    # Add multiple items
    for i in range(3):
        doc.append("items", {
            "item_code": f"_Test Item {i}",
            "qty": 10,
            "rate": 100
        })
    
    doc.insert()
    self.assertEqual(len(doc.items), 3)
```

### Pattern 3: Testing Validation

```python
def test_validation(self):
    doc = make_test_document(do_not_save=True)
    doc.required_field = None  # Set invalid value
    
    with self.assertRaises(frappe.ValidationError) as cm:
        doc.save()
    
    self.assertIn("required", str(cm.exception))
```

### Pattern 4: Testing Permissions

```python
def test_permissions(self):
    doc = make_test_document()
    
    # Test as different user
    with self.set_user("test@example.com"):
        doc = frappe.get_doc("MyDocType", doc.name)
        self.assertTrue(doc.has_permission("read"))
        self.assertFalse(doc.has_permission("write"))
```

### Pattern 5: Testing Calculations

```python
def test_calculations(self):
    doc = make_test_document(
        items=[
            {"item_code": "_Test Item", "qty": 10, "rate": 100},
            {"item_code": "_Test Item 2", "qty": 5, "rate": 50}
        ]
    )
    
    expected_total = (10 * 100) + (5 * 50)
    self.assertEqual(doc.total, expected_total)
```

### Pattern 6: Testing Workflow

```python
def test_workflow(self):
    doc = make_test_document()
    doc.submit()
    
    # Test workflow transition
    doc.status = "Approved"
    doc.save()
    
    self.assertEqual(doc.status, "Approved")
```

### Pattern 7: Testing with Settings

```python
@change_settings("Accounts Settings", {"allow_negative_stock": 1})
def test_with_settings(self):
    # Test with specific settings
    doc = make_test_document()
    # ... test logic
```

### Pattern 8: Testing Date-Based Logic

```python
def test_date_based_logic(self):
    from frappe.utils import add_days, getdate
    
    today = getdate()
    future_date = add_days(today, 30)
    
    doc = make_test_document(posting_date=future_date)
    # ... test date-based logic
```

### Pattern 9: Testing Serial/Batch Numbers

```python
def test_serial_batch(self):
    from erpnext.stock.doctype.serial_and_batch_bundle.test_serial_and_batch_bundle import (
        make_serial_batch_bundle
    )
    
    bundle = make_serial_batch_bundle({
        "item_code": "_Test Serial Item",
        "warehouse": "_Test Warehouse - _TC",
        "qty": 5,
        "serial_nos": ["SN001", "SN002", "SN003", "SN004", "SN005"],
        "voucher_type": "Stock Entry",
        "posting_date": today(),
    })
    
    doc = make_stock_entry(
        item_code="_Test Serial Item",
        serial_and_batch_bundle=bundle.name
    )
```

### Pattern 10: Testing Multi-Company

```python
def test_multi_company(self):
    company1 = create_company("_Test Company 1", abbr="_TC1")
    company2 = create_company("_Test Company 2", abbr="_TC2")
    
    doc1 = make_test_document(company=company1.name)
    doc2 = make_test_document(company=company2.name)
    
    # Test company-specific logic
```

---

## Best Practices

### 1. Use Factory Functions

**Good**:
```python
def test_something(self):
    pr = make_purchase_receipt(qty=10)
    # Test logic
```

**Bad**:
```python
def test_something(self):
    pr = frappe.new_doc("Purchase Receipt")
    pr.company = "_Test Company"
    pr.supplier = "_Test Supplier"
    pr.posting_date = today()
    pr.append("items", {
        "item_code": "_Test Item",
        "qty": 10,
        "rate": 50
    })
    pr.insert()
    pr.submit()
    # Test logic
```

### 2. Use Descriptive Test Names

**Good**:
```python
def test_purchase_receipt_creates_stock_ledger_entry(self):
    pass
```

**Bad**:
```python
def test_pr(self):
    pass
```

### 3. Clean Up in setUp

```python
def setUp(self):
    super().setUp()
    # Clean up before test
    frappe.db.delete("MyDocType", {"name": ["like", "_Test%"]})
    frappe.db.commit()
```

### 4. Use do_not_save for Validation Tests

```python
def test_validation(self):
    doc = make_test_document(do_not_save=True)
    doc.required_field = None
    
    with self.assertRaises(frappe.ValidationError):
        doc.save()
```

### 5. Use change_settings Decorator

```python
@change_settings("Accounts Settings", {"allow_negative_stock": 1})
def test_with_settings(self):
    # Test logic
```

### 6. Test Edge Cases

```python
def test_zero_quantity(self):
    with self.assertRaises(InvalidQtyError):
        make_purchase_receipt(qty=0)
```

### 7. Use Assertion Helpers

```python
def test_stock_entry(self):
    se = make_stock_entry(...)
    expected_sles = [...]
    self.assertSLEs(se, expected_sles)
```

### 8. Document Complex Tests

```python
def test_complex_calculation(self):
    """
    Test that complex calculation works correctly:
    1. Creates invoice with multiple items
    2. Applies discount
    3. Calculates tax
    4. Verifies final amount
    """
    # Test implementation
```

### 9. Use setUpClass for Expensive Operations

```python
@classmethod
def setUpClass(cls):
    super().setUpClass()
    # Create expensive test data once
    cls.company = create_company_with_all_setup()
    frappe.db.commit()
```

### 10. Test Both Positive and Negative Cases

```python
def test_positive_case(self):
    # Test normal flow
    pass

def test_negative_case(self):
    # Test error cases
    with self.assertRaises(ValidationError):
        # Invalid operation
        pass
```

---

## HRMS Factory Functions Reference

### Payroll Module

```python
# Holiday List
from hrms.payroll.doctype.salary_slip.test_salary_slip import make_holiday_list
holiday_list = make_holiday_list("Test Holiday List", from_date="2024-01-01", to_date="2024-12-31")

# Payroll Period
from hrms.payroll.doctype.salary_slip.test_salary_slip import make_payroll_period
payroll_period = make_payroll_period()

# Leave Application
from hrms.payroll.doctype.salary_slip.test_salary_slip import make_leave_application
leave_app = make_leave_application(employee="EMP-00001", from_date="2024-01-01", to_date="2024-01-05", leave_type="Annual Leave")

# Expense Claim
from hrms.hr.doctype.expense_claim.test_expense_claim import make_expense_claim
expense_claim = make_expense_claim(employee="EMP-00001", company="_Test Company", posting_date="2024-01-15")

# Employee Advance
from hrms.hr.doctype.employee_advance.test_employee_advance import make_employee_advance
advance = make_employee_advance(employee="EMP-00001", amount=5000)

# Shift Assignment
from hrms.hr.doctype.shift_type.test_shift_type import make_shift_assignment
shift_assignment = make_shift_assignment(employee="EMP-00001", shift_type="Day Shift", start_date="2024-01-01")

# Shift Request
from hrms.hr.doctype.shift_request.test_shift_request import make_shift_request
shift_request = make_shift_request(employee="EMP-00001", shift_type="Night Shift", from_date="2024-01-01", to_date="2024-01-07")

# Vehicle Log
from hrms.hr.doctype.vehicle_log.test_vehicle_log import make_vehicle_log
vehicle_log = make_vehicle_log(license_plate="ABC-123", employee_id="EMP-00001", with_services=True)

# Job Requisition
from hrms.hr.doctype.job_requisition.test_job_requisition import make_job_requisition
job_req = make_job_requisition(designation="Engineer", no_of_positions=2)

# Job Offer
from hrms.hr.doctype.job_offer.test_job_offer import create_job_offer
job_offer = create_job_offer(job_applicant="APP-00001", offer_date="2024-01-15")

# Leave Allocation
from hrms.hr.doctype.leave_allocation.test_leave_allocation import create_leave_allocation
allocation = create_leave_allocation(employee="EMP-00001", leave_type="Annual Leave", from_date="2024-01-01", to_date="2024-12-31", new_leaves_allocated=20)

# Leave Type
from hrms.hr.doctype.leave_type.test_leave_type import create_leave_type
leave_type = create_leave_type(leave_type_name="Test Leave", include_holiday=True)

# Leave Policy
from hrms.hr.doctype.leave_policy.test_leave_policy import create_leave_policy
leave_policy = create_leave_policy(policy_name="Test Policy", leave_type="Annual Leave", annual_allocation=20)

# Leave Period
from hrms.hr.doctype.leave_period.test_leave_period import create_leave_period
leave_period = create_leave_period(from_date="2024-01-01", to_date="2024-12-31", company="_Test Company")

# Leave Encashment
from hrms.hr.doctype.leave_encashment.test_leave_encashment import create_leave_encashment
encashment = create_leave_encashment(employee="EMP-00001", leave_type="Annual Leave", encashment_date="2024-12-31")

# Training Program
from hrms.hr.doctype.training_event.test_training_event import create_training_program
training_program = create_training_program("Python Training")

# Training Event
from hrms.hr.doctype.training_event.test_training_event import create_training_event
training_event = create_training_event(attendees=["EMP-00001", "EMP-00002"])

# Training Feedback
from hrms.hr.doctype.training_feedback.test_training_feedback import create_training_feedback
feedback = create_training_feedback(event="TRAIN-00001", employee="EMP-00001")

# Interview
from hrms.hr.doctype.interview.test_interview import create_interview_and_dependencies
interview = create_interview_and_dependencies(job_applicant="APP-00001", scheduled_on="2024-01-15 10:00:00")

# Interview Round
from hrms.hr.doctype.interview.test_interview import create_interview_round
interview_round = create_interview_round(name="Technical Round", skill_set=["Python", "Django"])

# Interview Feedback
from hrms.hr.doctype.interview_feedback.test_interview_feedback import create_interview_feedback
interview_feedback = create_interview_feedback(interview="INT-00001", interviewer="EMP-00001", skills_ratings={"Python": 5})

# Gratuity
from hrms.payroll.doctype.gratuity.test_gratuity import create_gratuity
gratuity = create_gratuity(employee="EMP-00001", posting_date="2024-01-15")

# Employee Tax Exemption Declaration
from hrms.payroll.doctype.employee_tax_exemption_declaration.test_employee_tax_exemption_declaration import create_exemption_declaration
declaration = create_exemption_declaration(employee="EMP-00001", payroll_period="2024-2025")

# Employee Tax Exemption Proof Submission
from hrms.payroll.doctype.salary_slip.test_salary_slip import create_proof_submission
proof = create_proof_submission(employee="EMP-00001", payroll_period="2024-2025", amount=50000)

# Employee Benefit Application
from hrms.payroll.doctype.employee_benefit_application.test_employee_benefit_application import make_employee_benefit_application
benefit_app = make_employee_benefit_application(employee="EMP-00001", payroll_period="2024-2025", date="2024-01-15")

# Employee Benefit Claim
from hrms.payroll.doctype.salary_slip.test_salary_slip import create_benefit_claim
benefit_claim = create_benefit_claim(employee="EMP-00001", payroll_period="2024-2025", amount=10000, component="Medical Allowance")

# Additional Salary
from hrms.payroll.doctype.salary_slip.test_salary_slip import create_additional_salary
additional_salary = create_additional_salary(employee="EMP-00001", payroll_period="2024-2025", amount=5000)

# Recurring Additional Salary
from hrms.payroll.doctype.salary_slip.test_salary_slip import create_recurring_additional_salary
recurring_salary = create_recurring_additional_salary(employee="EMP-00001", salary_component="Bonus", amount=1000, from_date="2024-01-01", to_date="2024-12-31")

# Employee Other Income
from hrms.payroll.doctype.salary_slip.test_salary_slip import create_employee_other_income
other_income = create_employee_other_income(employee="EMP-00001", payroll_period="2024-2025", company="_Test Company")

# Tax Slab
from hrms.payroll.doctype.salary_slip.test_salary_slip import create_tax_slab
tax_slab = create_tax_slab(payroll_period="2024-2025", effective_date="2024-01-01")

# Salary Withholding
from hrms.payroll.doctype.salary_withholding.test_salary_withholding import create_salary_withholding
withholding = create_salary_withholding(employee="EMP-00001", from_date="2024-01-01", number_of_withholding_cycles=3)

# Payroll Entry
from hrms.payroll.doctype.payroll_entry.test_payroll_entry import make_payroll_entry
payroll_entry = make_payroll_entry(company="_Test Company", posting_date="2024-01-15", payment_date="2024-01-20")

# Shift Schedule Assignment
from hrms.hr.doctype.shift_assignment_tool.test_shift_assignment_tool import make_shift_schedule_assignment
schedule_assignment = make_shift_schedule_assignment(schedule="Schedule 1", employee="EMP-00001", create_shifts_after="2024-01-01")

# Employee Checkin
from hrms.hr.doctype.employee_checkin.test_employee_checkin import make_checkin
checkin = make_checkin(employee="EMP-00001", time="2024-01-15 09:00:00", log_type="IN")

# Multiple Checkins
from hrms.hr.doctype.employee_checkin.test_employee_checkin import make_n_checkins
checkins = make_n_checkins(employee="EMP-00001", n=5, hours_to_reverse=1)

# Shift Location
from hrms.hr.doctype.employee_checkin.test_employee_checkin import make_shift_location
location = make_shift_location(location_name="Office", latitude=28.6139, longitude=77.2090, checkin_radius=500)
```

### ERPNext Setup Functions

```python
# Employee (CRITICAL - Most commonly used!)
from erpnext.setup.doctype.employee.test_employee import make_employee
employee = make_employee("test@example.com", company="_Test Company", designation="Engineer", department="IT")

# Customer
from erpnext.selling.doctype.customer.test_customer import get_customer_dict, create_customer
customer = create_customer(customer_name="_Test Customer", customer_group="All Customer Groups")

# Supplier
from erpnext.buying.doctype.supplier.test_supplier import create_supplier
supplier = create_supplier(supplier_name="_Test Supplier", supplier_group="Local")

# Company
from erpnext.accounts.doctype.opening_invoice_creation_tool.test_opening_invoice_creation_tool import make_company
company = make_company(company_name="_Test Company", abbr="_TC")

# Account
from erpnext.accounts.doctype.account.test_account import create_account, get_inventory_account
account = create_account(account_name="_Test Account", company="_Test Company", parent_account="Accounts Receivable - _TC")

# Warehouse
from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse
warehouse = create_warehouse(warehouse_name="_Test Warehouse", company="_Test Company")

# Item Group
from erpnext.stock.doctype.item_group.test_item_group import make_item_group
item_group = make_item_group(item_group_name="_Test Item Group", parent_item_group="All Item Groups")

# Brand
from erpnext.stock.doctype.brand.test_brand import make_brand
brand = make_brand(brand_name="_Test Brand")

# UOM
from erpnext.stock.doctype.uom.test_uom import make_uom
uom = make_uom(uom_name="_Test UOM")

# Designation
from erpnext.setup.doctype.designation.test_designation import create_designation
designation = create_designation(designation_name="Engineer")

# Department
from hrms.tests.test_utils import create_department
department = create_department("IT", company="_Test Company")

# Employee Grade
from hrms.tests.test_utils import create_employee_grade
employee_grade = create_employee_grade("Senior", default_base=100000)

# Job Applicant
from hrms.tests.test_utils import create_job_applicant
job_applicant = create_job_applicant(applicant_name="John Doe", email_id="john@example.com")

# Mode of Payment
from erpnext.accounts.doctype.mode_of_payment.test_mode_of_payment import set_default_account_for_mode_of_payment
set_default_account_for_mode_of_payment(mode_of_payment, company, account)

# POS Profile
from erpnext.accounts.doctype.pos_profile.test_pos_profile import make_pos_profile
pos_profile = make_pos_profile(company="_Test Company", warehouse="_Test Warehouse - _TC")

# Payment Terms Template
from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_payment_term
payment_term = create_payment_term("_Test Payment Term")

# Pricing Rule
from erpnext.accounts.doctype.pricing_rule.test_pricing_rule import make_pricing_rule
pricing_rule = make_pricing_rule(applicable_for="Item", item_code="_Test Item", selling=1, buying=0, price_or_discount="Price", rate=100)

# Item Price
from erpnext.accounts.doctype.pricing_rule.test_pricing_rule import make_item_price
item_price = make_item_price(item="_Test Item", price_list_name="_Test Price List", item_price=100)

# Budget
from erpnext.accounts.doctype.budget.test_budget import make_budget
budget = make_budget(budget_against="Cost Center", cost_center="_Test Cost Center - _TC", fiscal_year="2024-2025", company="_Test Company")

# Cost Center
from erpnext.accounts.doctype.cost_center.test_cost_center import create_cost_center
cost_center = create_cost_center(cost_center_name="_Test Cost Center", company="_Test Company")

# Project
from erpnext.projects.doctype.project.test_project import make_project
project = make_project({"project_name": "_Test Project", "company": "_Test Company"})

# BOM
from erpnext.manufacturing.doctype.bom.test_bom import make_bom
bom = make_bom(item="_Test Item", quantity=1, raw_materials=[{"item_code": "_Test Raw Material", "qty": 2}])

# Work Order
from erpnext.manufacturing.doctype.work_order.test_work_order import make_wo_order_test_record
work_order = make_wo_order_test_record(item="_Test Item", qty=10, company="_Test Company")

# Operation
from erpnext.manufacturing.doctype.work_order.test_work_order import make_operation
operation = make_operation(operation_name="Cutting", workcenter="_Test Work Center")

# Workstation
from erpnext.manufacturing.doctype.work_order.test_work_order import make_workstation
workstation = make_workstation(workstation_name="_Test Workstation", company="_Test Company")

# Lead
from erpnext.crm.doctype.lead.test_lead import make_lead
lead = make_lead(first_name="John", company_name="Test Company", email_id="john@example.com")

# Opportunity
from erpnext.crm.doctype.opportunity.test_opportunity import make_opportunity
opportunity = make_opportunity(customer="_Test Customer", opportunity_type="Sales", company="_Test Company")

# Prospect
from erpnext.crm.doctype.prospect.test_prospect import make_prospect
prospect = make_prospect(company_name="Test Company", email_id="test@example.com")

# Issue
from erpnext.support.doctype.issue.test_issue import make_issue
issue = make_issue(customer="_Test Customer", priority="High", issue_type="Bug")

# Service Level Agreement
from erpnext.support.doctype.service_level_agreement.test_service_level_agreement import make_holiday_list
holiday_list = make_holiday_list()

# Asset
from erpnext.assets.doctype.asset.test_asset import create_asset, create_asset_data
asset = create_asset(item_code="_Test Asset Item", company="_Test Company", location="Test Location")

# Asset Movement
from erpnext.assets.doctype.asset_movement.test_asset_movement import create_asset_movement
asset_movement = create_asset_movement(assets=["AST-00001"], purpose="Transfer", company="_Test Company")

# Asset Value Adjustment
from erpnext.assets.doctype.asset_value_adjustment.test_asset_value_adjustment import make_asset_value_adjustment
adjustment = make_asset_value_adjustment(asset="AST-00001", company="_Test Company", current_value=100000)

# Asset Repair
from erpnext.assets.doctype.asset_repair.test_asset_repair import create_asset_repair
asset_repair = create_asset_repair(asset="AST-00001", company="_Test Company", failure_date="2024-01-15")

# Location
from erpnext.assets.doctype.asset_movement.test_asset_movement import make_location
location = make_location()

# Serial Batch Bundle
from erpnext.stock.doctype.serial_and_batch_bundle.test_serial_and_batch_bundle import (
    make_serial_batch_bundle,
    get_serial_nos_from_bundle,
    get_batch_from_bundle
)
bundle = make_serial_batch_bundle({
    "item_code": "_Test Serial Item",
    "warehouse": "_Test Warehouse - _TC",
    "qty": 5,
    "serial_nos": ["SN001", "SN002", "SN003", "SN004", "SN005"],
    "voucher_type": "Stock Entry",
    "posting_date": today(),
    "do_not_submit": 1
})

# Batch
from erpnext.stock.doctype.batch.test_batch import make_new_batch, create_batch
batch = make_new_batch(item_code="_Test Batch Item", batch_id="BATCH-001")

# Serialized Item
from erpnext.stock.doctype.stock_entry.test_stock_entry import make_serialized_item
serialized_item = make_serialized_item(item_code="_Test Serial Item", warehouse="_Test Warehouse - _TC")

# Inventory Dimension
from erpnext.stock.doctype.inventory_dimension.test_inventory_dimension import create_inventory_dimension, create_store_dimension
dimension = create_inventory_dimension(dimension_name="Store", reference_document="Store")

# Stock Reconciliation
from erpnext.stock.doctype.stock_reconciliation.test_stock_reconciliation import create_stock_reconciliation
stock_reco = create_stock_reconciliation(item_code="_Test Item", warehouse="_Test Warehouse - _TC", qty=100, rate=50)

# Material Request
from erpnext.stock.doctype.material_request.test_material_request import make_material_request
material_request = make_material_request(item_code="_Test Item", qty=10, company="_Test Company")

# Pick List
from erpnext.stock.doctype.pick_list.test_pick_list import create_pick_list
pick_list = create_pick_list(sales_order="SO-00001")

# Delivery Trip
from erpnext.stock.doctype.delivery_trip.test_delivery_trip import make_delivery_trip
delivery_trip = make_delivery_trip(customer="_Test Customer", company="_Test Company")

# Shipment
from erpnext.stock.doctype.shipment.test_shipment import make_shipment
shipment = make_shipment(item_code="_Test Item", qty=10, company="_Test Company")

# Quality Inspection
from erpnext.stock.doctype.quality_inspection.test_quality_inspection import make_quality_inspection
quality_inspection = make_quality_inspection(item_code="_Test Item", inspection_type="Incoming", company="_Test Company")

# Subcontracting Receipt
from erpnext.subcontracting.doctype.subcontracting_receipt.test_subcontracting_receipt import make_return_subcontracting_receipt
subcontracting_receipt = make_return_subcontracting_receipt(company="_Test Company", supplier="_Test Supplier")

# Tax Category
from erpnext.accounts.report.tax_withholding_details.test_tax_withholding_details import create_tax_category
tax_category = create_tax_category(category="TCS", rate=0.075, account="TCS - _TC", cumulative_threshold=0)

# Tax Accounts
from erpnext.accounts.report.tax_withholding_details.test_tax_withholding_details import create_tax_accounts
create_tax_accounts()

# Contact and Address
from erpnext.tests.utils import create_test_contact_and_address
create_test_contact_and_address()
```

---

## Additional Utility Functions

### Stock Utilities

```python
# Get Stock Balance
from erpnext.stock.utils import get_stock_balance
balance = get_stock_balance(item_code="_Test Item", warehouse="_Test Warehouse - _TC")

# Get Incoming Rate
from erpnext.stock.utils import get_incoming_rate
rate = get_incoming_rate(item_code="_Test Item", warehouse="_Test Warehouse - _TC", posting_date="2024-01-15")

# Get Qty After Transaction
from erpnext.stock.doctype.stock_entry.test_stock_entry import get_qty_after_transaction
qty = get_qty_after_transaction(item_code="_Test Item", warehouse="_Test Warehouse - _TC")

# Scan Barcode
from erpnext.stock.utils import scan_barcode
barcode_result = scan_barcode("12399")
```

### Accounts Utilities

```python
# Get GL Entries
def get_gl_entries(voucher_type, voucher_no):
    return frappe.get_all(
        "GL Entry",
        filters={"voucher_type": voucher_type, "voucher_no": voucher_no, "is_cancelled": 0},
        fields=["*"],
        order_by="posting_date, creation"
    )

# Check GL Entries
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import check_gl_entries
check_gl_entries(doc, voucher_no, expected_gle, posting_date, voucher_type="Sales Invoice")

# Get Inventory Account
from erpnext.accounts.doctype.account.test_account import get_inventory_account
inventory_account = get_inventory_account("_Test Item", "_Test Company", "_Test Warehouse - _TC")
```

### Date and Time Utilities

```python
from frappe.utils import (
    add_days,
    add_months,
    add_years,
    get_first_day,
    get_last_day,
    get_year_start,
    get_year_ending,
    getdate,
    nowdate,
    today,
    get_datetime,
    now_datetime,
    format_date,
    format_datetime,
    date_diff,
    time_diff,
    get_first_day_of_week,
    get_last_day_of_week,
    get_quarter_start,
    get_quarter_ending,
    get_fiscal_year,
    get_fiscal_year_start_date,
    get_fiscal_year_end_date,
)

# Get First Sunday (HRMS pattern)
from hrms.tests.test_utils import get_first_sunday
first_sunday = get_first_sunday(holiday_list="Salary Slip Test Holiday List", for_date=getdate())

# Get First Day for Previous Month
from hrms.tests.test_utils import get_first_day_for_prev_month
prev_month_first = get_first_day_for_prev_month()
```

### Attendance Utilities

```python
# Mark Attendance
from hrms.hr.doctype.attendance.attendance import mark_attendance
mark_attendance(employee="EMP-00001", attendance_date="2024-01-15", status="Present", ignore_validate=True)

# Mark Attendance with Leave Type
mark_attendance(
    employee="EMP-00001",
    attendance_date="2024-01-16",
    status="On Leave",
    leave_type="Annual Leave",
    ignore_validate=True
)

# Mark Half Day
mark_attendance(
    employee="EMP-00001",
    attendance_date="2024-01-17",
    status="Half Day",
    leave_type="Annual Leave",
    half_day_status="Present",
    ignore_validate=True
)
```

### Email Utilities

```python
# Get Email by Subject
from hrms.tests.test_utils import get_email_by_subject
email_id = get_email_by_subject("Salary Slip")

# Create Email Template
from hrms.payroll.doctype.salary_slip.test_salary_slip import create_ss_email_template
create_ss_email_template()
```

### Account Creation Utilities

```python
# Create Account
from hrms.payroll.doctype.salary_slip.test_salary_slip import create_account
account = create_account(account_name="_Test Salary Account", company="_Test Company", parent_account="Expenses - _TC", account_type="Expense")

# Set Salary Component Account
from hrms.payroll.doctype.salary_slip.test_salary_slip import set_salary_component_account
set_salary_component_account(salary_component="Basic Salary", company_list=["_Test Company"])
```

### Leave Utilities

```python
# Create Leave Allocation
from hrms.hr.doctype.leave_allocation.test_leave_allocation import create_leave_allocation
allocation = create_leave_allocation(
    employee="EMP-00001",
    from_date="2024-01-01",
    to_date="2024-12-31",
    new_leaves_allocated=20,
    leave_type="_Test Leave Type"
)

# Make Allocation Record
from hrms.hr.doctype.leave_application.test_leave_application import make_allocation_record
allocation = make_allocation_record(
    leave_type="_Test Leave Type",
    from_date="2024-01-01",
    to_date="2024-12-31",
    leaves=20
)

# Create Carry Forwarded Allocation
from hrms.hr.doctype.leave_application.test_leave_application import create_carry_forwarded_allocation
allocation = create_carry_forwarded_allocation(employee="EMP-00001", leave_type="_Test Leave Type", date="2024-01-01")
```

### Shift Utilities

```python
# Setup Shift Type
from hrms.hr.doctype.shift_type.test_shift_type import setup_shift_type
shift_type = setup_shift_type(
    shift_type="Day Shift",
    start_time="08:00:00",
    end_time="17:00:00",
    working_hours_threshold_for_half_day=4,
    working_hours_threshold_for_absent=2
)

# Make Shift Assignment
from hrms.hr.doctype.shift_type.test_shift_type import make_shift_assignment
shift_assignment = make_shift_assignment(
    employee="EMP-00001",
    shift_type="Day Shift",
    start_date="2024-01-01",
    end_date="2024-12-31"
)
```

### Payroll Utilities

```python
# Make Income Tax Components
from hrms.payroll.doctype.salary_slip.test_salary_slip import make_income_tax_components
make_income_tax_components()

# Make Salary Component
from hrms.payroll.doctype.salary_slip.test_salary_slip import make_salary_component
salary_component = make_salary_component(salary_components=["Basic Salary", "HRA"], test_tax=True, company_list=["_Test Company"])

# Make Earning Salary Component
from hrms.payroll.doctype.salary_slip.test_salary_slip import make_earning_salary_component
earning_component = make_earning_salary_component(
    salary_components=["Basic Salary", "HRA"],
    setup=False,
    test_tax=False,
    company_list=["_Test Company"]
)

# Make Deduction Salary Component
from hrms.payroll.doctype.salary_slip.test_salary_slip import make_deduction_salary_component
deduction_component = make_deduction_salary_component(
    setup=False,
    test_tax=False,
    company_list=["_Test Company"]
)

# Create Salary Component
from hrms.payroll.doctype.salary_component.test_salary_component import create_salary_component
salary_component = create_salary_component(component_name="Basic Salary", type="Earning", is_tax_applicable=1)

# Create Salary Structure Assignment
from hrms.payroll.doctype.salary_structure.test_salary_structure import create_salary_structure_assignment
assignment = create_salary_structure_assignment(
    employee="EMP-00001",
    salary_structure="Test Structure",
    from_date="2024-01-01"
)

# Create Salary Slips for Payroll Period
from hrms.payroll.doctype.salary_slip.test_salary_slip import create_salary_slips_for_payroll_period
salary_slips = create_salary_slips_for_payroll_period(
    employee="EMP-00001",
    payroll_period="2024-2025",
    salary_structure="Test Structure"
)

# Get Tax Paid in Period
from hrms.payroll.doctype.salary_slip.test_salary_slip import get_tax_paid_in_period
tax_paid = get_tax_paid_in_period(employee="EMP-00001")

# Make Salary Structure for Payment Days Based Component
from hrms.payroll.doctype.salary_slip.test_salary_slip import make_salary_structure_for_payment_days_based_component_dependency
salary_structure = make_salary_structure_for_payment_days_based_component_dependency(test_statistical_comp=False)

# Make Salary Structure for Timesheet
from hrms.payroll.doctype.salary_slip.test_salary_slip import make_salary_structure_for_timesheet
salary_structure = make_salary_structure_for_timesheet(employee="EMP-00001", company="_Test Company")

# Make Salary Structure for Statistical Component
from hrms.payroll.doctype.salary_slip.test_salary_slip import make_salary_structure_for_statistical_component
salary_structure = make_salary_structure_for_statistical_component(company="_Test Company")

# Make Salary Slip with Non-Taxable Component
from hrms.payroll.doctype.salary_slip.test_salary_slip import make_salary_slip_with_non_taxable_component
salary_slip = make_salary_slip_with_non_taxable_component()
```

### Appraisal Utilities

```python
# Create Appraisal Cycle
from hrms.hr.doctype.appraisal_cycle.test_appraisal_cycle import create_appraisal_cycle
appraisal_cycle = create_appraisal_cycle(
    cycle_name="Annual Appraisal 2024",
    company="_Test Company",
    start_date="2024-01-01",
    end_date="2024-12-31"
)

# Create Appraisal Template
from hrms.hr.doctype.appraisal_template.test_appraisal_template import create_appraisal_template
template = create_appraisal_template(template_name="Engineer Appraisal")

# Create Performance Feedback
from hrms.hr.doctype.employee_performance_feedback.test_employee_performance_feedback import create_performance_feedback
feedback = create_performance_feedback(employee="EMP-00001", review="Good performance")
```

### Interview Utilities

```python
# Create Interview and Dependencies
from hrms.hr.doctype.interview.test_interview import create_interview_and_dependencies
interview = create_interview_and_dependencies(
    job_applicant="APP-00001",
    scheduled_on="2024-01-15 10:00:00",
    interview_round="Technical Round"
)

# Create Interview Round
from hrms.hr.doctype.interview.test_interview import create_interview_round
interview_round = create_interview_round(
    name="Technical Round",
    skill_set=["Python", "Django"],
    interviewers=["EMP-00001"],
    designation="Engineer"
)

# Create Skill Set
from hrms.hr.doctype.interview.test_interview import create_skill_set
skill_set = create_skill_set(skill_set="Technical Skills")

# Create Interview Type
from hrms.hr.doctype.interview.test_interview import create_interview_type
interview_type = create_interview_type(name="Technical Interview")
```

### Exit Management Utilities

```python
# Create Exit Interview
from hrms.hr.report.employee_exits.test_employee_exits import create_exit_interview
exit_interview = create_exit_interview(employee="EMP-00001")

# Create Full and Final Statement
from hrms.hr.report.employee_exits.test_employee_exits import create_full_and_final_statement
fnf = create_full_and_final_statement(employee="EMP-00001")
```

---

## Test Mixins and Helper Classes

### AccountsTestMixin

```python
from erpnext.accounts.test.accounts_mixin import AccountsTestMixin

class TestMyDocType(FrappeTestCase, AccountsTestMixin):
    def setUp(self):
        super().setUp()
        # Use mixin methods
        self.create_customer()
        self.create_supplier()
        self.create_item()
        self.create_company()
    
    def test_something(self):
        # Use self.customer, self.supplier, self.item, self.company
        pass
```

### StockTestMixin

```python
from erpnext.stock.tests.test_utils import StockTestMixin

class TestMyStockDocType(FrappeTestCase, StockTestMixin):
    def test_stock_transaction(self):
        # Use mixin methods
        item = self.make_item()
        
        # Use assertion helpers
        expected_sles = [
            {"item_code": item.name, "warehouse": "_Test Warehouse - _TC", "actual_qty": 10}
        ]
        self.assertSLEs(doc, expected_sles)
        
        expected_gles = [
            {"account": "_Test Account - _TC", "debit": 1000, "credit": 0}
        ]
        self.assertGLEs(doc, expected_gles)
```

---

## Advanced Patterns

### Pattern 1: Testing with Multiple Companies

```python
def test_multi_company(self):
    company1 = create_company("_Test Company 1", abbr="_TC1")
    company2 = create_company("_Test Company 2", abbr="_TC2")
    
    # Create documents for each company
    doc1 = make_test_document(company=company1.name)
    doc2 = make_test_document(company=company2.name)
    
    # Test company-specific logic
    self.assertEqual(doc1.company, company1.name)
    self.assertEqual(doc2.company, company2.name)
```

### Pattern 2: Testing with Serial Numbers

```python
def test_serial_numbers(self):
    from erpnext.stock.doctype.serial_and_batch_bundle.test_serial_and_batch_bundle import (
        make_serial_batch_bundle,
        get_serial_nos_from_bundle
    )
    
    # Create serialized item
    item = make_item(properties={"has_serial_no": 1})
    
    # Create bundle with serial numbers
    bundle = make_serial_batch_bundle({
        "item_code": item.name,
        "warehouse": "_Test Warehouse - _TC",
        "qty": 5,
        "serial_nos": ["SN001", "SN002", "SN003", "SN004", "SN005"],
        "voucher_type": "Stock Entry",
        "posting_date": today(),
        "do_not_submit": 1
    })
    
    # Get serial numbers from bundle
    serial_nos = get_serial_nos_from_bundle(bundle.name)
    self.assertEqual(len(serial_nos), 5)
```

### Pattern 3: Testing with Batch Numbers

```python
def test_batch_numbers(self):
    from erpnext.stock.doctype.batch.test_batch import make_new_batch
    from erpnext.stock.doctype.serial_and_batch_bundle.test_serial_and_batch_bundle import (
        make_serial_batch_bundle,
        get_batch_from_bundle
    )
    
    # Create batch item
    item = make_item(properties={"has_batch_no": 1, "create_new_batch": 1})
    
    # Create batch
    batch = make_new_batch(item_code=item.name, batch_id="BATCH-001")
    
    # Create bundle with batch
    bundle = make_serial_batch_bundle({
        "item_code": item.name,
        "warehouse": "_Test Warehouse - _TC",
        "qty": 10,
        "batches": {batch.name: 10},
        "voucher_type": "Stock Entry",
        "posting_date": today(),
        "do_not_submit": 1
    })
    
    # Get batch from bundle
    batch_no = get_batch_from_bundle(bundle.name)
    self.assertEqual(batch_no, batch.name)
```

### Pattern 4: Testing Payroll Calculations

```python
def test_payroll_calculations(self):
    # Create employee
    employee = make_employee("test@payroll.com", company="_Test Company")
    
    # Create salary structure
    salary_structure = make_salary_structure(
        "Test Structure",
        "Monthly",
        employee=employee,
        company="_Test Company"
    )
    
    # Create salary slip
    salary_slip = make_employee_salary_slip(employee, "Monthly", salary_structure.name)
    
    # Test calculations
    self.assertEqual(salary_slip.gross_pay, 50000)
    self.assertEqual(salary_slip.total_deduction, 5000)
    self.assertEqual(salary_slip.net_pay, 45000)
```

### Pattern 5: Testing Leave Balance

```python
def test_leave_balance(self):
    # Create employee
    employee = make_employee("test@leave.com", company="_Test Company")
    
    # Create leave allocation
    allocation = create_leave_allocation(
        employee=employee,
        from_date="2024-01-01",
        to_date="2024-12-31",
        new_leaves_allocated=20,
        leave_type="_Test Leave Type"
    )
    allocation.submit()
    
    # Create leave application
    leave_app = make_leave_application(
        employee=employee,
        from_date="2024-01-15",
        to_date="2024-01-20",
        leave_type="_Test Leave Type"
    )
    leave_app.submit()
    
    # Check balance
    from hrms.hr.doctype.leave_application.leave_application import get_leave_balance_on
    balance = get_leave_balance_on(employee, "_Test Leave Type", "2024-01-21")
    self.assertEqual(balance, 15)  # 20 allocated - 5 used
```

### Pattern 6: Testing Attendance Processing

```python
def test_attendance_processing(self):
    # Create employee
    employee = make_employee("test@attendance.com", company="_Test Company")
    
    # Create shift
    shift_type = setup_shift_type(
        shift_type="Day Shift",
        start_time="08:00:00",
        end_time="17:00:00"
    )
    
    # Assign shift
    shift_assignment = make_shift_assignment(
        employee=employee,
        shift_type=shift_type.name,
        start_date="2024-01-01"
    )
    
    # Create checkins
    make_checkin(employee, "2024-01-15 08:00:00", "IN")
    make_checkin(employee, "2024-01-15 17:00:00", "OUT")
    
    # Mark attendance
    mark_attendance(
        employee=employee,
        attendance_date="2024-01-15",
        status="Present"
    )
    
    # Verify attendance
    attendance = frappe.get_doc("Attendance", {
        "employee": employee,
        "attendance_date": "2024-01-15"
    })
    self.assertEqual(attendance.status, "Present")
```

### Pattern 7: Testing Workflow States

```python
def test_workflow_states(self):
    doc = make_test_document()
    
    # Submit to change state
    doc.submit()
    self.assertEqual(doc.workflow_state, "Submitted")
    
    # Approve
    doc.workflow_state = "Approved"
    doc.save()
    self.assertEqual(doc.workflow_state, "Approved")
    
    # Reject
    doc.workflow_state = "Rejected"
    doc.save()
    self.assertEqual(doc.workflow_state, "Rejected")
```

### Pattern 8: Testing with change_settings Decorator

```python
@change_settings("Accounts Settings", {
    "allow_negative_stock": 1,
    "maintain_same_internal_transaction_rate": 1
})
def test_with_settings(self):
    # Test with specific settings enabled
    doc = make_test_document()
    # ... test logic
```

### Pattern 9: Testing Email Notifications

```python
def test_email_notification(self):
    # Create document that triggers email
    doc = make_test_document()
    doc.submit()
    
    # Check if email was sent
    from hrms.tests.test_utils import get_email_by_subject
    email_id = get_email_by_subject("Test Document Notification")
    self.assertIsNotNone(email_id)
    
    # Verify email content
    email = frappe.get_doc("Email Queue", email_id)
    self.assertIn("Test Document", email.message)
```

### Pattern 10: Testing with Time Freezing

```python
def test_with_frozen_time(self):
    from frappe.tests.utils import freeze_time
    
    with freeze_time("2024-01-15 10:00:00"):
        doc = make_test_document()
        self.assertEqual(doc.posting_date, "2024-01-15")
        self.assertEqual(doc.posting_time, "10:00:00")
```

---

## Complete Import Reference

### Most Commonly Used Imports

```python
# Core Frappe
import frappe
from frappe.tests.utils import FrappeTestCase, change_settings
from frappe.utils import (
    add_days, add_months, getdate, nowdate, today,
    get_first_day, get_last_day, flt, cint, cstr
)

# ERPNext Setup (CRITICAL!)
from erpnext.setup.doctype.employee.test_employee import make_employee
from erpnext.setup.doctype.designation.test_designation import create_designation
from hrms.tests.test_utils import create_company, create_department, create_employee_grade

# ERPNext Stock
from erpnext.stock.doctype.item.test_item import make_item, create_item
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry
from erpnext.stock.doctype.delivery_note.test_delivery_note import make_delivery_note
from erpnext.stock.doctype.serial_and_batch_bundle.test_serial_and_batch_bundle import (
    make_serial_batch_bundle,
    get_serial_nos_from_bundle,
    get_batch_from_bundle
)

# ERPNext Accounts
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry
from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_payment_entry
from erpnext.accounts.doctype.account.test_account import create_account, get_inventory_account

# ERPNext Buying
from erpnext.buying.doctype.purchase_order.test_purchase_order import make_purchase_order
from erpnext.buying.doctype.supplier.test_supplier import create_supplier

# ERPNext Selling
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.selling.doctype.customer.test_customer import get_customer_dict, create_customer

# HRMS Payroll
from hrms.payroll.doctype.salary_slip.test_salary_slip import (
    make_employee_salary_slip,
    make_holiday_list,
    make_payroll_period,
    make_leave_application,
    make_salary_component,
    make_earning_salary_component,
    make_deduction_salary_component
)
from hrms.payroll.doctype.salary_structure.test_salary_structure import (
    make_salary_structure,
    create_salary_structure_assignment
)

# HRMS HR
from hrms.hr.doctype.leave_application.test_leave_application import make_leave_application
from hrms.hr.doctype.leave_allocation.test_leave_allocation import create_leave_allocation
from hrms.hr.doctype.leave_type.test_leave_type import create_leave_type
from hrms.hr.doctype.shift_type.test_shift_type import setup_shift_type, make_shift_assignment
from hrms.hr.doctype.expense_claim.test_expense_claim import make_expense_claim
from hrms.hr.doctype.employee_advance.test_employee_advance import make_employee_advance
from hrms.hr.doctype.attendance.attendance import mark_attendance

# HRMS Utilities
from hrms.tests.test_utils import (
    create_company,
    create_department,
    create_employee_grade,
    create_job_applicant,
    get_first_sunday,
    get_email_by_subject
)

# Test Mixins
from erpnext.accounts.test.accounts_mixin import AccountsTestMixin
from erpnext.stock.tests.test_utils import StockTestMixin
```

---

## Quick Reference Cheat Sheet

### Top 20 Most Used Functions

1. **`make_employee()`** - Create test employee
2. **`make_item()`** - Create test item
3. **`make_purchase_receipt()`** - Create purchase receipt
4. **`make_sales_invoice()`** - Create sales invoice
5. **`make_stock_entry()`** - Create stock entry
6. **`make_employee_salary_slip()`** - Create salary slip
7. **`make_salary_structure()`** - Create salary structure
8. **`create_company()`** - Create test company
9. **`create_customer()`** - Create test customer
10. **`create_supplier()`** - Create test supplier
11. **`make_leave_application()`** - Create leave application
12. **`create_leave_allocation()`** - Create leave allocation
13. **`mark_attendance()`** - Mark employee attendance
14. **`make_expense_claim()`** - Create expense claim
15. **`make_holiday_list()`** - Create holiday list
16. **`make_payroll_period()`** - Create payroll period
17. **`make_serial_batch_bundle()`** - Create serial/batch bundle
18. **`make_journal_entry()`** - Create journal entry
19. **`create_account()`** - Create account
20. **`create_warehouse()`** - Create warehouse

---

## Summary

This guide has documented **hundreds of useful test utility functions** from ERPNext and HRMS that you can use in your custom Frappe applications. Key takeaways:

1. **Always use factory functions** (`make_*` or `create_*`) instead of manually creating documents
2. **Use test mixins** (`AccountsTestMixin`, `StockTestMixin`) for common functionality
3. **Leverage assertion helpers** (`assertSLEs`, `assertGLEs`) for complex validations
4. **Use `make_employee()`** - it's the most commonly used function in HRMS tests
5. **Follow the patterns** shown in this guide for consistency
6. **Import from test files** - most functions are in `test_*.py` files
7. **Use `do_not_save` and `do_not_submit`** flags for validation testing
8. **Use `change_settings` decorator** for testing with different settings
9. **Use `setUpClass`** for expensive operations shared across tests
10. **Document your tests** with clear docstrings

## Next Steps

Continue to:
- [Part 1: Fundamentals](./63-Frappe_Unit_Testing_Guide_Part_1_Fundamentals.md)
- [Part 2: Test Commands and Execution](./64-Frappe_Unit_Testing_Guide_Part_2_Test_Commands.md)
- [Part 3: Test Patterns and Best Practices](./65-Frappe_Unit_Testing_Guide_Part_3_Patterns.md)
- [Part 4: Advanced Testing Techniques](./66-Frappe_Unit_Testing_Guide_Part_4_Advanced.md)
- [Part 5: Test Data Management](./67-Frappe_Unit_Testing_Guide_Part_5_Test_Data.md)
- [Part 7: Assertions](./69-Frappe_Unit_Testing_Guide_Part_7_Assertions.md)
- [Part 8: Reports](./80-Frappe_Unit_Testing_Guide_Part_8_Reports.md)
- [Part 9: Test Records](./82-Frappe_Unit_Testing_Guide_Part_9_Test_Records.md)


# Frappe Assertions Complete Guide

## Table of Contents

1. [Introduction](#introduction)
2. [Standard unittest Assertions](#standard-unittest-assertions)
3. [Frappe-Specific Assertions](#frappe-specific-assertions)
4. [Context Manager Assertions](#context-manager-assertions)
5. [Exception Assertions](#exception-assertions)
6. [Document Assertions](#document-assertions)
7. [Database Assertions](#database-assertions)
8. [Performance Assertions](#performance-assertions)
9. [Custom Assertions](#custom-assertions)
10. [Best Practices](#best-practices)
11. [Common Patterns](#common-patterns)
12. [Troubleshooting](#troubleshooting)

---

## Introduction

Assertions are the core of unit testing in Frappe. They verify that your code behaves as expected. Frappe extends Python's standard `unittest.TestCase` with additional assertion methods tailored for Frappe-specific scenarios.

### What are Assertions?

Assertions are statements that check if a condition is true. If the condition is false, the test fails with a descriptive error message.

### Base Test Class

All Frappe tests inherit from `FrappeTestCase`, which extends `unittest.TestCase`:

```python
from frappe.tests.utils import FrappeTestCase

class TestMyFeature(FrappeTestCase):
    def test_something(self):
        # Your assertions here
        pass
```

---

## Standard unittest Assertions

These are the standard assertions inherited from Python's `unittest.TestCase`. They work exactly as in standard Python unit testing.

### Equality Assertions

#### `assertEqual(first, second, msg=None)`

Checks if two values are equal.

```python
def test_equality(self):
    result = calculate_total(10, 20)
    self.assertEqual(result, 30)
    
    # With custom message
    self.assertEqual(result, 30, msg="Total calculation is incorrect")
```

**Use Cases:**
- Comparing calculated values
- Verifying field values
- Checking return values

**Examples:**
```python
# Compare numbers
self.assertEqual(5, 5)

# Compare strings
self.assertEqual("Hello", "Hello")

# Compare lists
self.assertEqual([1, 2, 3], [1, 2, 3])

# Compare document fields
doc = frappe.get_doc("Employee", "EMP-00001")
self.assertEqual(doc.status, "Active")
```

#### `assertNotEqual(first, second, msg=None)`

Checks if two values are NOT equal.

```python
def test_not_equal(self):
    status1 = "Active"
    status2 = "Inactive"
    self.assertNotEqual(status1, status2)
```

**Use Cases:**
- Verifying values changed
- Ensuring different states
- Checking uniqueness

**Examples:**
```python
# Verify status changed
old_status = doc.status
doc.status = "Left"
doc.save()
self.assertNotEqual(old_status, doc.status)

# Verify different employees
self.assertNotEqual(emp1.name, emp2.name)
```

### Boolean Assertions

#### `assertTrue(expr, msg=None)`

Checks if expression is `True`.

```python
def test_boolean(self):
    is_active = check_employee_status("EMP-00001")
    self.assertTrue(is_active)
    
    # Check document exists
    self.assertTrue(frappe.db.exists("Employee", "EMP-00001"))
    
    # Check permission
    doc = frappe.get_doc("Employee", "EMP-00001")
    self.assertTrue(doc.has_permission("read"))
```

**Use Cases:**
- Checking boolean return values
- Verifying document existence
- Checking permissions
- Validating conditions

**Examples:**
```python
# Check existence
self.assertTrue(frappe.db.exists("Employee", emp))

# Check permissions
self.assertTrue(doc.has_permission("write"))

# Check flags
self.assertTrue(frappe.flags.in_test)

# Check conditions
self.assertTrue(len(items) > 0)
```

#### `assertFalse(expr, msg=None)`

Checks if expression is `False`.

```python
def test_false(self):
    is_deleted = check_if_deleted("EMP-00001")
    self.assertFalse(is_deleted)
    
    # Check document doesn't exist
    self.assertFalse(frappe.db.exists("Employee", "NON-EXISTENT"))
```

**Use Cases:**
- Verifying negative conditions
- Checking document doesn't exist
- Validating disabled states

**Examples:**
```python
# Check doesn't exist
self.assertFalse(frappe.db.exists("Employee", "INVALID"))

# Check not deleted
self.assertFalse(doc.is_deleted)

# Check not cancelled
self.assertFalse(doc.docstatus == 2)
```

### Comparison Assertions

#### `assertGreater(first, second, msg=None)`

Checks if `first > second`.

```python
def test_greater(self):
    balance = get_account_balance("ACC-00001")
    self.assertGreater(balance, 0)
    
    # Check quantity
    qty = get_stock_balance("ITEM-00001", "WH-00001")
    self.assertGreater(qty, 10)
```

**Use Cases:**
- Checking minimum values
- Verifying quantities
- Validating thresholds

**Examples:**
```python
# Check balance
self.assertGreater(balance, 0)

# Check quantity
self.assertGreater(qty, minimum_qty)

# Check count
self.assertGreater(len(items), 0)
```

#### `assertGreaterEqual(first, second, msg=None)`

Checks if `first >= second`.

```python
def test_greater_equal(self):
    age = calculate_age("1990-01-01")
    self.assertGreaterEqual(age, 18)
```

**Examples:**
```python
# Check minimum age
self.assertGreaterEqual(age, 18)

# Check minimum service years
self.assertGreaterEqual(service_years, 1)
```

#### `assertLess(first, second, msg=None)`

Checks if `first < second`.

```python
def test_less(self):
    balance = get_account_balance("ACC-00001")
    self.assertLess(balance, 1000000)
```

**Examples:**
```python
# Check maximum balance
self.assertLess(balance, max_balance)

# Check quantity
self.assertLess(qty, max_qty)
```

#### `assertLessEqual(first, second, msg=None)`

Checks if `first <= second`.

```python
def test_less_equal(self):
    discount = calculate_discount(amount)
    self.assertLessEqual(discount, 100)  # Max 100%
```

**Examples:**
```python
# Check maximum discount
self.assertLessEqual(discount, 100)

# Check maximum quantity
self.assertLessEqual(qty, max_qty)
```

### Membership Assertions

#### `assertIn(member, container, msg=None)`

Checks if `member` is in `container`.

```python
def test_in(self):
    roles = get_user_roles("user@example.com")
    self.assertIn("Employee", roles)
    
    # Check in list
    statuses = ["Draft", "Submitted", "Cancelled"]
    self.assertIn(doc.status, statuses)
```

**Use Cases:**
- Checking list membership
- Verifying roles
- Validating status values

**Examples:**
```python
# Check in list
self.assertIn("Active", ["Active", "Inactive", "Left"])

# Check in roles
self.assertIn("System Manager", user_roles)

# Check in dictionary keys
self.assertIn("name", doc.as_dict())

# Check in string
self.assertIn("error", error_message.lower())
```

#### `assertNotIn(member, container, msg=None)`

Checks if `member` is NOT in `container`.

```python
def test_not_in(self):
    roles = get_user_roles("user@example.com")
    self.assertNotIn("Administrator", roles)
```

**Examples:**
```python
# Check not in list
self.assertNotIn("Deleted", statuses)

# Check not in roles
self.assertNotIn("Guest", user_roles)
```

### Type Assertions

#### `assertIsInstance(obj, cls, msg=None)`

Checks if `obj` is an instance of `cls`.

```python
def test_instance(self):
    doc = frappe.get_doc("Employee", "EMP-00001")
    self.assertIsInstance(doc, frappe.model.document.Document)
    
    # Check types
    self.assertIsInstance(doc.salary, (int, float))
```

**Use Cases:**
- Verifying return types
- Checking document types
- Validating data types

**Examples:**
```python
# Check document type
self.assertIsInstance(doc, frappe.model.document.Document)

# Check numeric type
self.assertIsInstance(amount, (int, float))

# Check string type
self.assertIsInstance(name, str)

# Check list type
self.assertIsInstance(items, list)
```

#### `assertIsNotInstance(obj, cls, msg=None)`

Checks if `obj` is NOT an instance of `cls`.

```python
def test_not_instance(self):
    value = get_value()
    self.assertIsNotInstance(value, str)  # Should be number
```

### Identity Assertions

#### `assertIs(first, second, msg=None)`

Checks if `first is second` (same object identity).

```python
def test_is(self):
    doc1 = frappe.get_doc("Employee", "EMP-00001")
    doc2 = frappe.get_doc("Employee", "EMP-00001")
    # These are different objects even if same document
    self.assertIsNot(doc1, doc2)
    
    # But reloaded doc is same object
    doc1.reload()
    self.assertIs(doc1, doc1)
```

**Use Cases:**
- Checking object identity
- Verifying same instance
- Testing singleton patterns

#### `assertIsNot(first, second, msg=None)`

Checks if `first is not second`.

### None Assertions

#### `assertIsNone(expr, msg=None)`

Checks if expression is `None`.

```python
def test_is_none(self):
    deleted_doc = frappe.db.get_value("Employee", "DELETED-001")
    self.assertIsNone(deleted_doc)
    
    # Check optional field
    self.assertIsNone(doc.relieving_date)
```

**Use Cases:**
- Checking deleted documents
- Verifying optional fields
- Validating null values

**Examples:**
```python
# Check deleted document
self.assertIsNone(frappe.db.get_value("Employee", deleted_emp))

# Check optional field
self.assertIsNone(doc.relieving_date)

# Check return value
result = get_optional_value()
self.assertIsNone(result)
```

#### `assertIsNotNone(expr, msg=None)`

Checks if expression is NOT `None`.

```python
def test_is_not_none(self):
    doc = frappe.get_doc("Employee", "EMP-00001")
    self.assertIsNotNone(doc.name)
    self.assertIsNotNone(doc.date_of_joining)
```

**Examples:**
```python
# Check required field
self.assertIsNotNone(doc.name)

# Check created document
self.assertIsNotNone(created_doc)

# Check return value
result = calculate_value()
self.assertIsNotNone(result)
```

### Sequence Assertions

#### `assertSequenceEqual(first, second, msg=None)`

Checks if two sequences are equal.

```python
def test_sequence(self):
    expected = [1, 2, 3]
    actual = get_numbers()
    self.assertSequenceEqual(expected, actual)
```

**Examples:**
```python
# Compare lists
self.assertSequenceEqual([1, 2, 3], [1, 2, 3])

# Compare tuples
self.assertSequenceEqual((1, 2), (1, 2))
```

#### `assertListEqual(first, second, msg=None)`

Checks if two lists are equal.

```python
def test_list(self):
    expected = ["Item 1", "Item 2"]
    actual = get_items()
    self.assertListEqual(expected, actual)
```

#### `assertTupleEqual(first, second, msg=None)`

Checks if two tuples are equal.

#### `assertSetEqual(first, second, msg=None)`

Checks if two sets are equal (order doesn't matter).

```python
def test_set(self):
    expected = {1, 2, 3}
    actual = {3, 2, 1}  # Order doesn't matter
    self.assertSetEqual(expected, actual)
```

**Use Cases:**
- Comparing roles (order doesn't matter)
- Checking permissions
- Validating unique values

**Examples:**
```python
# Compare roles (order doesn't matter)
expected_roles = {"Employee", "Manager"}
actual_roles = {"Manager", "Employee"}
self.assertSetEqual(expected_roles, actual_roles)
```

#### `assertDictEqual(first, second, msg=None)`

Checks if two dictionaries are equal.

```python
def test_dict(self):
    expected = {"name": "Test", "status": "Active"}
    actual = doc.as_dict()
    self.assertDictEqual(expected, actual)
```

**Use Cases:**
- Comparing document dictionaries
- Verifying API responses
- Checking configuration

**Examples:**
```python
# Compare document dicts
expected = {"status": "Active", "name": "EMP-00001"}
actual = doc.as_dict()
self.assertDictEqual(expected, actual)

# Compare API responses
expected_response = {"success": True, "data": []}
self.assertDictEqual(expected_response, response)
```

### String Assertions

#### `assertMultiLineEqual(first, second, msg=None)`

Checks if two multi-line strings are equal (shows diff).

```python
def test_multiline(self):
    expected = """Line 1
Line 2
Line 3"""
    actual = get_multiline_text()
    self.assertMultiLineEqual(expected, actual)
```

**Use Cases:**
- Comparing HTML content
- Verifying email templates
- Checking formatted text

#### `assertRegex(text, regex, msg=None)`

Checks if `text` matches `regex`.

```python
def test_regex(self):
    email = "test@example.com"
    self.assertRegex(email, r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    
    # Check naming series
    doc_name = "EMP-00001"
    self.assertRegex(doc_name, r'^EMP-\d{5}$')
```

**Use Cases:**
- Validating email formats
- Checking naming series
- Verifying patterns

**Examples:**
```python
# Check email format
self.assertRegex(email, r'^[\w\.-]+@[\w\.-]+\.\w+$')

# Check naming series
self.assertRegex(doc_name, r'^EMP-\d{5}$')

# Check phone number
self.assertRegex(phone, r'^\d{10}$')
```

#### `assertNotRegex(text, regex, msg=None)`

Checks if `text` does NOT match `regex`.

### Numeric Assertions

#### `assertAlmostEqual(first, second, places=7, msg=None, delta=None)`

Checks if two numbers are almost equal (for floating point).

```python
def test_almost_equal(self):
    result = calculate_percentage(10, 3)
    # 10 / 3 = 3.333333...
    self.assertAlmostEqual(result, 3.333, places=3)
    
    # Using delta
    self.assertAlmostEqual(result, 3.33, delta=0.01)
```

**Use Cases:**
- Comparing floating point calculations
- Verifying percentages
- Checking currency amounts

**Examples:**
```python
# Compare with precision
self.assertAlmostEqual(10/3, 3.333, places=3)

# Compare currency
self.assertAlmostEqual(amount, 100.50, places=2)

# Compare with delta
self.assertAlmostEqual(result, expected, delta=0.01)
```

#### `assertNotAlmostEqual(first, second, places=7, msg=None, delta=None)`

Checks if two numbers are NOT almost equal.

### Count Assertions

#### `assertCountEqual(first, second, msg=None)`

Checks if two sequences have the same elements (order doesn't matter).

```python
def test_count_equal(self):
    expected = [1, 2, 3, 3]
    actual = [3, 2, 1, 3]
    self.assertCountEqual(expected, actual)  # Same elements, different order
```

**Use Cases:**
- Comparing lists where order doesn't matter
- Checking item collections
- Validating child table rows

**Examples:**
```python
# Compare items (order doesn't matter)
expected_items = ["Item A", "Item B", "Item C"]
actual_items = ["Item C", "Item A", "Item B"]
self.assertCountEqual(expected_items, actual_items)
```

---

## Frappe-Specific Assertions

Frappe extends `unittest.TestCase` with custom assertions for Frappe-specific scenarios.

### Document Assertions

#### `assertDocumentEqual(expected, actual)`

Compares a (partial) expected document with actual Document. This is the most powerful Frappe-specific assertion.

```python
def test_document_equal(self):
    # Create expected document
    expected = {
        "doctype": "Employee",
        "employee_name": "Test Employee",
        "status": "Active",
        "date_of_joining": "2024-01-01"
    }
    
    # Get actual document
    doc = frappe.get_doc("Employee", "EMP-00001")
    
    # Compare
    self.assertDocumentEqual(expected, doc)
```

**Features:**
- Handles float precision automatically
- Compares child tables recursively
- Handles datetime objects
- Supports partial comparison (only specified fields)

**Use Cases:**
- Comparing document fields
- Verifying document creation
- Testing document updates
- Validating child table data

**Examples:**

```python
# Compare full document
expected = {
    "doctype": "Employee",
    "employee_name": "John Doe",
    "status": "Active",
    "date_of_joining": "2024-01-01",
    "salary": 50000.00
}
doc = frappe.get_doc("Employee", "EMP-00001")
self.assertDocumentEqual(expected, doc)

# Partial comparison (only specified fields)
expected = {
    "status": "Active",
    "employee_name": "John Doe"
}
self.assertDocumentEqual(expected, doc)  # Only checks these fields

# Compare with child tables
expected = {
    "doctype": "Sales Invoice",
    "customer": "_Test Customer",
    "items": [
        {"item_code": "_Test Item", "qty": 10, "rate": 100},
        {"item_code": "_Test Item 2", "qty": 5, "rate": 50}
    ]
}
invoice = frappe.get_doc("Sales Invoice", "SI-00001")
self.assertDocumentEqual(expected, invoice)

# Compare using document object
expected_doc = frappe.get_doc("Employee", "EMP-00001")
actual_doc = frappe.get_doc("Employee", "EMP-00001")
self.assertDocumentEqual(expected_doc, actual_doc)
```

**How it works:**
- For floats: Uses document precision for comparison
- For booleans/ints: Converts using `cint()`
- For datetime: Compares string representation
- For lists: Recursively compares child documents
- For other types: Standard equality check

### Sequence Assertions

#### `assertSequenceSubset(larger, smaller, msg=None)`

Asserts that `smaller` is a subset of `larger`.

```python
def test_sequence_subset(self):
    all_roles = ["Employee", "Manager", "Administrator", "Guest"]
    user_roles = ["Employee", "Manager"]
    
    self.assertSequenceSubset(all_roles, user_roles)
```

**Use Cases:**
- Checking user roles
- Verifying permissions
- Validating included items

**Examples:**
```python
# Check roles subset
all_roles = ["Employee", "Manager", "Administrator"]
user_roles = ["Employee", "Manager"]
self.assertSequenceSubset(all_roles, user_roles)

# Check items subset
all_items = ["Item A", "Item B", "Item C", "Item D"]
selected_items = ["Item A", "Item C"]
self.assertSequenceSubset(all_items, selected_items)
```

---

## Context Manager Assertions

These assertions are used as context managers to test behavior within a specific scope.

### Database Query Assertions

#### `assertQueryCount(count)`

Asserts that the number of SQL queries executed is less than or equal to `count`.

```python
def test_query_count(self):
    with self.assertQueryCount(5):
        # This block should execute at most 5 queries
        doc = frappe.get_doc("Employee", "EMP-00001")
        doc.status = "Active"
        doc.save()
        doc.submit()
```

**Use Cases:**
- Performance testing
- Detecting N+1 query problems
- Optimizing database access
- Ensuring efficient queries

**Examples:**
```python
# Test query efficiency
with self.assertQueryCount(3):
    doc = frappe.get_doc("Employee", "EMP-00001")
    doc.reload()
    doc.save()

# Test bulk operations
with self.assertQueryCount(10):
    for i in range(100):
        create_employee(f"emp{i}@example.com")

# Test report generation
with self.assertQueryCount(5):
    generate_report("Employee Report")
```

**Error Message:**
If query count exceeds, shows all executed queries for debugging.

#### `assertRowsRead(count)`

Asserts that the number of rows read from database is less than or equal to `count`.

```python
def test_rows_read(self):
    with self.assertRowsRead(100):
        # Should read at most 100 rows
        employees = frappe.get_all("Employee", limit=100)
```

**Use Cases:**
- Testing pagination
- Verifying limit clauses
- Optimizing data retrieval

**Examples:**
```python
# Test pagination
with self.assertRowsRead(50):
    employees = frappe.get_all("Employee", limit=50)

# Test filtered queries
with self.assertRowsRead(10):
    active_employees = frappe.get_all(
        "Employee",
        filters={"status": "Active"},
        limit=10
    )
```

#### `assertQueryEqual(first, second)`

Asserts that two SQL queries are equal (normalized).

```python
def test_query_equal(self):
    query1 = "SELECT * FROM `tabEmployee` WHERE status = 'Active'"
    query2 = """
        SELECT *
        FROM `tabEmployee`
        WHERE status = 'Active'
    """
    self.assertQueryEqual(query1, query2)  # Same query, different formatting
```

**Use Cases:**
- Testing query builders
- Verifying generated SQL
- Comparing query structures

**Examples:**
```python
# Compare normalized queries
query1 = "SELECT name FROM tabEmployee"
query2 = "SELECT name FROM `tabEmployee`"
self.assertQueryEqual(query1, query2)

# Compare formatted queries
from frappe.query_builder import DocType
Employee = DocType("Employee")
query1 = frappe.qb.from_(Employee).select(Employee.name)
query2 = "SELECT name FROM `tabEmployee`"
self.assertQueryEqual(str(query1), query2)
```

### Redis/Cache Assertions

#### `assertRedisCallCounts(count)`

Asserts that the number of Redis calls is less than or equal to `count`.

```python
def test_redis_calls(self):
    with self.assertRedisCallCounts(5):
        # Should make at most 5 Redis calls
        frappe.cache.get_value("key1")
        frappe.cache.set_value("key2", "value")
        frappe.cache.delete_value("key3")
```

**Use Cases:**
- Testing cache efficiency
- Detecting excessive cache calls
- Optimizing cache usage

**Examples:**
```python
# Test cache operations
with self.assertRedisCallCounts(3):
    frappe.cache.get_value("key1")
    frappe.cache.set_value("key2", "value")
    frappe.cache.delete_value("key3")
```

---

## Exception Assertions

These assertions verify that exceptions are raised correctly.

### `assertRaises(exception, callable, *args, **kwargs)`

Asserts that `callable` raises `exception` when called with `*args` and `**kwargs`.

```python
def test_raises_exception(self):
    # Test that validation error is raised
    self.assertRaises(
        frappe.ValidationError,
        create_invalid_employee
    )
    
    # Test with arguments
    self.assertRaises(
        frappe.ValidationError,
        create_employee,
        "invalid@email"  # Missing required fields
    )
```

**Use Cases:**
- Testing validation errors
- Verifying permission errors
- Checking error handling
- Testing edge cases

**Examples:**

```python
# Test validation error
def test_validation_error(self):
    doc = frappe.new_doc("Employee")
    # Missing required field
    self.assertRaises(frappe.ValidationError, doc.insert)

# Test permission error
def test_permission_error(self):
    with self.set_user("test@example.com"):
        doc = frappe.get_doc("Employee", "EMP-00001")
        self.assertRaises(frappe.PermissionError, doc.submit)

# Test with context manager (preferred)
def test_raises_with_context(self):
    with self.assertRaises(frappe.ValidationError) as cm:
        doc = frappe.new_doc("Employee")
        doc.insert()  # Missing required fields
    
    # Check error message
    self.assertIn("required", str(cm.exception).lower())

# Test specific exception message
def test_exception_message(self):
    with self.assertRaises(frappe.ValidationError) as cm:
        create_invalid_document()
    
    error_message = str(cm.exception)
    self.assertIn("required field", error_message)
```

### `assertRaisesRegex(exception, regex, callable, *args, **kwargs)`

Asserts that `callable` raises `exception` and the message matches `regex`.

```python
def test_raises_regex(self):
    self.assertRaisesRegex(
        frappe.ValidationError,
        r"required.*field",
        create_invalid_document
    )
```

**Examples:**

```python
# Test error message pattern
def test_error_message_pattern(self):
    self.assertRaisesRegex(
        frappe.ValidationError,
        r"required.*field.*name",
        create_employee_without_name
    )

# Test with context manager
def test_regex_with_context(self):
    with self.assertRaisesRegex(frappe.ValidationError, r"invalid.*email"):
        validate_email("invalid-email")
```

### Common Exception Types in Frappe

```python
# ValidationError - For validation failures
self.assertRaises(frappe.ValidationError, invalid_operation)

# PermissionError - For permission issues
self.assertRaises(frappe.PermissionError, unauthorized_operation)

# DoesNotExistError - For missing documents
self.assertRaises(frappe.DoesNotExistError, get_nonexistent_doc)

# DuplicateEntryError - For duplicate entries
self.assertRaises(frappe.DuplicateEntryError, create_duplicate)

# LinkValidationError - For invalid links
self.assertRaises(frappe.LinkValidationError, link_invalid_doc)

# MandatoryError - For missing mandatory fields
self.assertRaises(frappe.MandatoryError, save_without_required_field)

# InvalidStatusError - For invalid status transitions
self.assertRaises(frappe.InvalidStatusError, invalid_status_change)

# DocstatusTransitionError - For invalid docstatus transitions
self.assertRaises(frappe.DocstatusTransitionError, cancel_draft_doc)
```

---

## Document Assertions (Advanced)

### Complete Document Comparison

```python
def test_complete_document(self):
    # Create expected document structure
    expected = {
        "doctype": "Sales Invoice",
        "customer": "_Test Customer",
        "posting_date": "2024-01-15",
        "due_date": "2024-01-30",
        "items": [
            {
                "item_code": "_Test Item",
                "qty": 10,
                "rate": 100.00,
                "amount": 1000.00
            },
            {
                "item_code": "_Test Item 2",
                "qty": 5,
                "rate": 50.00,
                "amount": 250.00
            }
        ],
        "grand_total": 1250.00,
        "outstanding_amount": 1250.00
    }
    
    invoice = frappe.get_doc("Sales Invoice", "SI-00001")
    self.assertDocumentEqual(expected, invoice)
```

### Testing Child Tables

```python
def test_child_table(self):
    expected = {
        "doctype": "Purchase Order",
        "supplier": "_Test Supplier",
        "items": [
            {"item_code": "ITEM-001", "qty": 10},
            {"item_code": "ITEM-002", "qty": 20}
        ]
    }
    
    po = frappe.get_doc("Purchase Order", "PO-00001")
    self.assertDocumentEqual(expected, po)
    
    # Verify child table count
    self.assertEqual(len(po.items), 2)
    
    # Verify specific child row
    self.assertEqual(po.items[0].item_code, "ITEM-001")
    self.assertEqual(po.items[0].qty, 10)
```

### Testing Calculated Fields

```python
def test_calculated_fields(self):
    doc = frappe.get_doc("Sales Invoice", "SI-00001")
    
    # Test calculation
    expected_total = sum(item.amount for item in doc.items)
    self.assertEqual(doc.grand_total, expected_total)
    
    # Test with precision
    self.assertAlmostEqual(doc.grand_total, 1250.00, places=2)
```

---

## Database Assertions

### Document Existence

```python
def test_document_exists(self):
    # Check document exists
    self.assertTrue(frappe.db.exists("Employee", "EMP-00001"))
    
    # Check document doesn't exist
    self.assertFalse(frappe.db.exists("Employee", "INVALID"))
    
    # Check with filters
    exists = frappe.db.exists("Employee", {"status": "Active", "company": "_Test Company"})
    self.assertTrue(exists)
```

### Field Value Assertions

```python
def test_field_value(self):
    # Get single value
    status = frappe.db.get_value("Employee", "EMP-00001", "status")
    self.assertEqual(status, "Active")
    
    # Get multiple values
    values = frappe.db.get_value("Employee", "EMP-00001", ["status", "company"])
    self.assertEqual(values["status"], "Active")
    self.assertEqual(values["company"], "_Test Company")
    
    # Check None for deleted
    deleted_value = frappe.db.get_value("Employee", "DELETED-001")
    self.assertIsNone(deleted_value)
```

### Count Assertions

```python
def test_count(self):
    # Count all documents
    total = frappe.db.count("Employee")
    self.assertGreater(total, 0)
    
    # Count with filters
    active_count = frappe.db.count("Employee", {"status": "Active"})
    self.assertGreaterEqual(active_count, 1)
    
    # Count child table rows
    items_count = frappe.db.count("Sales Invoice Item", {"parent": "SI-00001"})
    self.assertGreater(items_count, 0)
```

### SQL Assertions

```python
def test_sql_results(self):
    # Execute SQL and verify
    result = frappe.db.sql("""
        SELECT COUNT(*) as count
        FROM `tabEmployee`
        WHERE status = 'Active'
    """, as_dict=True)
    
    self.assertGreater(result[0]["count"], 0)
    
    # Verify specific query result
    employees = frappe.db.sql("""
        SELECT name, status
        FROM `tabEmployee`
        WHERE company = %s
    """, ("_Test Company",), as_dict=True)
    
    self.assertGreater(len(employees), 0)
    for emp in employees:
        self.assertIn("name", emp)
        self.assertIn("status", emp)
```

### Transaction Assertions

```python
def test_transaction(self):
    # Test that changes are rolled back
    initial_count = frappe.db.count("Employee")
    
    # Create document (will be rolled back)
    make_employee("test@example.com")
    
    # After rollback, count should be same
    # (This happens automatically in FrappeTestCase)
    final_count = frappe.db.count("Employee")
    # Note: In actual test, rollback happens in tearDown
```

---

## Performance Assertions

### Query Performance

```python
def test_query_performance(self):
    # Ensure query count is reasonable
    with self.assertQueryCount(5):
        doc = frappe.get_doc("Employee", "EMP-00001")
        doc.reload()
        doc.save()
    
    # Test bulk operations
    with self.assertQueryCount(20):
        for i in range(100):
            create_employee(f"emp{i}@example.com")
```

### Row Read Performance

```python
def test_row_read_performance(self):
    # Ensure we don't read too many rows
    with self.assertRowsRead(50):
        employees = frappe.get_all("Employee", limit=50)
    
    # Test with filters
    with self.assertRowsRead(10):
        active_employees = frappe.get_all(
            "Employee",
            filters={"status": "Active"},
            limit=10
        )
```

### Cache Performance

```python
def test_cache_performance(self):
    # Ensure cache calls are reasonable
    with self.assertRedisCallCounts(5):
        # Multiple cache operations
        frappe.cache.get_value("key1")
        frappe.cache.set_value("key2", "value")
        frappe.cache.get_value("key3")
```

---

## Custom Assertions

### Creating Custom Assertions

You can create custom assertion methods for your specific use cases:

```python
class TestMyFeature(FrappeTestCase):
    def assertEmployeeActive(self, employee):
        """Custom assertion to check employee is active"""
        emp = frappe.get_doc("Employee", employee)
        self.assertEqual(emp.status, "Active")
        self.assertIsNone(emp.relieving_date)
        self.assertTrue(emp.enabled)
    
    def assertDocumentSubmitted(self, doctype, name):
        """Custom assertion to check document is submitted"""
        doc = frappe.get_doc(doctype, name)
        self.assertEqual(doc.docstatus, 1)
        self.assertIsNotNone(doc.submitted_by)
        self.assertIsNotNone(doc.submitted_on)
    
    def assertGLEntriesMatch(self, voucher_type, voucher_no, expected_entries):
        """Custom assertion for GL entries"""
        gl_entries = frappe.get_all(
            "GL Entry",
            filters={
                "voucher_type": voucher_type,
                "voucher_no": voucher_no,
                "is_cancelled": 0
            },
            fields=["account", "debit", "credit"],
            order_by="account"
        )
        
        self.assertEqual(len(gl_entries), len(expected_entries))
        for expected, actual in zip(expected_entries, gl_entries):
            self.assertEqual(expected["account"], actual["account"])
            self.assertAlmostEqual(expected["debit"], actual["debit"], places=2)
            self.assertAlmostEqual(expected["credit"], actual["credit"], places=2)
    
    def test_custom_assertions(self):
        employee = make_employee("test@example.com")
        self.assertEmployeeActive(employee)
        
        invoice = make_sales_invoice()
        invoice.submit()
        self.assertDocumentSubmitted("Sales Invoice", invoice.name)
```

### ERPNext/HRMS Custom Assertions

```python
# From ERPNext StockTestMixin
class StockTestMixin:
    def assertSLEs(self, doc, expected_sles, sle_filters=None):
        """Assert Stock Ledger Entries"""
        filters = {
            "voucher_no": doc.name,
            "voucher_type": doc.doctype,
            "is_cancelled": 0
        }
        if sle_filters:
            filters.update(sle_filters)
        
        sles = frappe.get_all(
            "Stock Ledger Entry",
            fields=["*"],
            filters=filters,
            order_by="timestamp(posting_date, posting_time), creation",
        )
        
        self.assertGreaterEqual(len(sles), len(expected_sles))
        for exp_sle, act_sle in zip(expected_sles, sles, strict=False):
            for k, v in exp_sle.items():
                self.assertEqual(v, act_sle[k], msg=f"{k} doesn't match")
    
    def assertGLEs(self, doc, expected_gles, gle_filters=None):
        """Assert General Ledger Entries"""
        filters = {
            "voucher_no": doc.name,
            "voucher_type": doc.doctype,
            "is_cancelled": 0
        }
        if gle_filters:
            filters.update(gle_filters)
        
        gles = frappe.get_all(
            "GL Entry",
            fields=["*"],
            filters=filters,
            order_by="posting_date, creation",
        )
        
        self.assertGreaterEqual(len(gles), len(expected_gles))
        for exp_gle, act_gle in zip(expected_gles, gles, strict=False):
            for k, exp_value in exp_gle.items():
                act_value = act_gle[k]
                self.assertEqual(exp_value, act_value, msg=f"{k} doesn't match")
```

---

## Best Practices

### 1. Use Descriptive Messages

```python
# Good
self.assertEqual(result, expected, msg="Total calculation failed")

# Bad
self.assertEqual(result, expected)
```

### 2. Test One Thing Per Assertion

```python
# Good
self.assertEqual(doc.status, "Active")
self.assertEqual(doc.company, "_Test Company")

# Bad
self.assertTrue(doc.status == "Active" and doc.company == "_Test Company")
```

### 3. Use Appropriate Assertions

```python
# Good - Use assertIsNone for None checks
self.assertIsNone(deleted_doc)

# Bad - Don't use assertEqual for None
self.assertEqual(deleted_doc, None)

# Good - Use assertTrue for boolean
self.assertTrue(doc.enabled)

# Bad - Don't use assertEqual for boolean
self.assertEqual(doc.enabled, True)
```

### 4. Use assertDocumentEqual for Documents

```python
# Good - Use Frappe-specific assertion
expected = {"status": "Active", "company": "_Test Company"}
self.assertDocumentEqual(expected, doc)

# Bad - Manual field-by-field comparison
self.assertEqual(doc.status, "Active")
self.assertEqual(doc.company, "_Test Company")
# ... many more lines
```

### 5. Use Context Managers for Exceptions

```python
# Good - Can access exception
with self.assertRaises(frappe.ValidationError) as cm:
    invalid_operation()
self.assertIn("required", str(cm.exception))

# Bad - Can't access exception details
self.assertRaises(frappe.ValidationError, invalid_operation)
```

### 6. Use assertAlmostEqual for Floating Point

```python
# Good - Handles floating point precision
self.assertAlmostEqual(result, 3.333, places=3)

# Bad - May fail due to precision
self.assertEqual(result, 3.333333333)
```

### 7. Use Performance Assertions

```python
# Good - Test query performance
with self.assertQueryCount(5):
    expensive_operation()

# Bad - No performance check
expensive_operation()  # May be slow
```

### 8. Group Related Assertions

```python
# Good - Logical grouping
def test_employee_creation(self):
    employee = make_employee("test@example.com")
    
    # Basic fields
    self.assertIsNotNone(employee.name)
    self.assertEqual(employee.status, "Active")
    
    # Dates
    self.assertIsNotNone(employee.date_of_joining)
    self.assertIsNone(employee.relieving_date)
    
    # Permissions
    self.assertTrue(employee.has_permission("read"))
```

---

## Common Patterns

### Pattern 1: Testing Document Lifecycle

```python
def test_document_lifecycle(self):
    # Create
    doc = make_test_document()
    self.assertEqual(doc.docstatus, 0)  # Draft
    self.assertIsNotNone(doc.name)
    
    # Submit
    doc.submit()
    self.assertEqual(doc.docstatus, 1)  # Submitted
    self.assertIsNotNone(doc.submitted_by)
    
    # Cancel
    doc.cancel()
    self.assertEqual(doc.docstatus, 2)  # Cancelled
```

### Pattern 2: Testing Calculations

```python
def test_calculations(self):
    doc = make_test_document()
    
    # Test individual calculations
    expected_total = sum(item.amount for item in doc.items)
    self.assertEqual(doc.total, expected_total)
    
    # Test with precision
    self.assertAlmostEqual(doc.grand_total, 1250.00, places=2)
    
    # Test percentage
    discount_percent = (doc.discount_amount / doc.total) * 100
    self.assertLessEqual(discount_percent, 100)
```

### Pattern 3: Testing Validations

```python
def test_validations(self):
    # Test required field
    doc = frappe.new_doc("Employee")
    with self.assertRaises(frappe.ValidationError) as cm:
        doc.insert()
    self.assertIn("required", str(cm.exception).lower())
    
    # Test invalid value
    doc.employee_name = "Test"
    doc.email = "invalid-email"
    with self.assertRaises(frappe.ValidationError):
        doc.insert()
```

### Pattern 4: Testing Permissions

```python
def test_permissions(self):
    doc = make_test_document()
    
    # Test as different user
    with self.set_user("test@example.com"):
        doc = frappe.get_doc("Employee", doc.name)
        self.assertTrue(doc.has_permission("read"))
        self.assertFalse(doc.has_permission("write"))
        
        # Test submit permission
        with self.assertRaises(frappe.PermissionError):
            doc.submit()
```

### Pattern 5: Testing Child Tables

```python
def test_child_table(self):
    doc = make_test_document()
    
    # Test child table count
    self.assertEqual(len(doc.items), 2)
    
    # Test child table values
    self.assertEqual(doc.items[0].item_code, "_Test Item")
    self.assertEqual(doc.items[0].qty, 10)
    
    # Test child table calculations
    expected_amount = doc.items[0].qty * doc.items[0].rate
    self.assertEqual(doc.items[0].amount, expected_amount)
```

### Pattern 6: Testing Database State

```python
def test_database_state(self):
    # Before
    initial_count = frappe.db.count("Employee")
    
    # Action
    make_employee("test@example.com")
    
    # After
    final_count = frappe.db.count("Employee")
    self.assertEqual(final_count, initial_count + 1)
    
    # Verify document exists
    self.assertTrue(frappe.db.exists("Employee", {"email": "test@example.com"}))
```

### Pattern 7: Testing Performance

```python
def test_performance(self):
    # Test query count
    with self.assertQueryCount(5):
        doc = frappe.get_doc("Employee", "EMP-00001")
        doc.reload()
        doc.save()
    
    # Test row reads
    with self.assertRowsRead(100):
        employees = frappe.get_all("Employee", limit=100)
```

---

## Troubleshooting

### Common Issues

#### Issue 1: Floating Point Precision

**Problem:**
```python
self.assertEqual(10/3, 3.333333333)  # Fails due to precision
```

**Solution:**
```python
self.assertAlmostEqual(10/3, 3.333, places=3)
# or
self.assertAlmostEqual(10/3, 3.33, delta=0.01)
```

#### Issue 2: Document Comparison

**Problem:**
```python
# Comparing documents field by field is tedious
self.assertEqual(doc.field1, expected1)
self.assertEqual(doc.field2, expected2)
# ... many lines
```

**Solution:**
```python
expected = {"field1": expected1, "field2": expected2}
self.assertDocumentEqual(expected, doc)
```

#### Issue 3: Exception Message Testing

**Problem:**
```python
# Can't access exception message
self.assertRaises(frappe.ValidationError, invalid_operation)
```

**Solution:**
```python
with self.assertRaises(frappe.ValidationError) as cm:
    invalid_operation()
self.assertIn("required", str(cm.exception))
```

#### Issue 4: Query Count Failures

**Problem:**
```python
# Query count assertion fails unexpectedly
with self.assertQueryCount(5):
    operation()  # Executes 10 queries
```

**Solution:**
- Check if operation is doing unnecessary queries
- Use `frappe.db.explain()` to see queries
- Consider caching or optimization
- Adjust expected count if operation legitimately needs more queries

#### Issue 5: Time-Dependent Tests

**Problem:**
```python
# Test fails due to time differences
self.assertEqual(doc.creation, now())
```

**Solution:**
```python
# Use freeze_time context manager
with self.freeze_time("2024-01-15 10:00:00"):
    doc = make_test_document()
    self.assertEqual(str(doc.creation), "2024-01-15 10:00:00")
```

### Debugging Failed Assertions

#### 1. Use Descriptive Messages

```python
self.assertEqual(result, expected, 
    msg=f"Calculation failed: expected {expected}, got {result}")
```

#### 2. Print Values Before Assertion

```python
def test_debug(self):
    result = calculate_value()
    print(f"Result: {result}")  # Debug output
    print(f"Type: {type(result)}")
    self.assertEqual(result, expected)
```

#### 3. Use maxDiff for Long Comparisons

```python
class TestMyFeature(FrappeTestCase):
    maxDiff = 10000  # Show more diff details
    
    def test_long_comparison(self):
        expected = {"very": "long", "dictionary": "with", "many": "fields"}
        actual = get_actual_dict()
        self.assertDictEqual(expected, actual)
```

#### 4. Check Assertion Order

```python
# Good - Check prerequisites first
def test_order(self):
    self.assertIsNotNone(doc)  # Check exists first
    self.assertEqual(doc.status, "Active")  # Then check value
```

---

## Quick Reference

### Standard Assertions

| Assertion | Purpose | Example |
|-----------|---------|---------|
| `assertEqual(a, b)` | a == b | `self.assertEqual(5, 5)` |
| `assertNotEqual(a, b)` | a != b | `self.assertNotEqual(1, 2)` |
| `assertTrue(x)` | x is True | `self.assertTrue(doc.enabled)` |
| `assertFalse(x)` | x is False | `self.assertFalse(doc.deleted)` |
| `assertIs(a, b)` | a is b | `self.assertIs(obj1, obj1)` |
| `assertIsNot(a, b)` | a is not b | `self.assertIsNot(obj1, obj2)` |
| `assertIsNone(x)` | x is None | `self.assertIsNone(deleted_doc)` |
| `assertIsNotNone(x)` | x is not None | `self.assertIsNotNone(doc.name)` |
| `assertIn(a, b)` | a in b | `self.assertIn("Active", statuses)` |
| `assertNotIn(a, b)` | a not in b | `self.assertNotIn("Deleted", statuses)` |
| `assertIsInstance(a, b)` | isinstance(a, b) | `self.assertIsInstance(doc, Document)` |
| `assertGreater(a, b)` | a > b | `self.assertGreater(balance, 0)` |
| `assertGreaterEqual(a, b)` | a >= b | `self.assertGreaterEqual(age, 18)` |
| `assertLess(a, b)` | a < b | `self.assertLess(balance, 1000)` |
| `assertLessEqual(a, b)` | a <= b | `self.assertLessEqual(discount, 100)` |
| `assertAlmostEqual(a, b)` | a ≈ b | `self.assertAlmostEqual(10/3, 3.333, places=3)` |
| `assertRaises(ex, fn)` | fn raises ex | `self.assertRaises(ValidationError, invalid_op)` |

### Frappe-Specific Assertions

| Assertion | Purpose | Example |
|-----------|---------|---------|
| `assertDocumentEqual(exp, act)` | Compare documents | `self.assertDocumentEqual(expected, doc)` |
| `assertSequenceSubset(larger, smaller)` | smaller ⊆ larger | `self.assertSequenceSubset(all_roles, user_roles)` |
| `assertQueryCount(n)` | ≤ n queries | `with self.assertQueryCount(5): ...` |
| `assertRowsRead(n)` | ≤ n rows | `with self.assertRowsRead(100): ...` |
| `assertQueryEqual(q1, q2)` | Queries equal | `self.assertQueryEqual(query1, query2)` |
| `assertRedisCallCounts(n)` | ≤ n Redis calls | `with self.assertRedisCallCounts(5): ...` |

---

## Summary

This guide covers all assertion methods available in Frappe testing:

1. **Standard unittest assertions** - Basic equality, comparison, membership, type checks
2. **Frappe-specific assertions** - Document comparison, sequence subsets
3. **Context manager assertions** - Query counts, row reads, Redis calls
4. **Exception assertions** - Testing error conditions
5. **Custom assertions** - Creating your own assertion methods
6. **Best practices** - How to write effective assertions
7. **Common patterns** - Real-world testing scenarios
8. **Troubleshooting** - Solving common issues

Remember:
- Use descriptive messages
- Choose the right assertion for the job
- Test one thing per assertion
- Use Frappe-specific assertions when appropriate

---

## Next Steps

Continue to:
- [Part 1: Fundamentals](./63-Frappe_Unit_Testing_Guide_Part_1_Fundamentals.md)
- [Part 2: Test Commands and Execution](./64-Frappe_Unit_Testing_Guide_Part_2_Test_Commands.md)
- [Part 3: Test Patterns and Best Practices](./65-Frappe_Unit_Testing_Guide_Part_3_Patterns.md)
- [Part 4: Advanced Testing Techniques](./66-Frappe_Unit_Testing_Guide_Part_4_Advanced.md)
- [Part 5: Test Data Management](./67-Frappe_Unit_Testing_Guide_Part_5_Test_Data.md)
- [Part 6: Test Utilities and Techniques](./68-Frappe_Unit_Testing_Guide_Part_6_Utilities.md)
- [Part 8: Reports](./80-Frappe_Unit_Testing_Guide_Part_8_Reports.md)
- [Part 9: Test Records](./82-Frappe_Unit_Testing_Guide_Part_9_Test_Records.md)
