# Testing Guide

This document describes the testing strategy and how to run tests for both the ETL pipeline and Django web application.

## Test Coverage

### **1. ETL Scripts Unit Tests** ([tests/](tests/))

#### **Extract Layer Tests** ([test_extract.py](tests/test_extract.py))
- ✅ Spotify API authentication setup
- ✅ Environment-based configuration (local vs Docker)
- ✅ Playlist track extraction with mocked API
- ✅ Pagination handling for large playlists
- ✅ Missing/deleted track handling
- ✅ Artist genre fetching with rate limiting

#### **Transform Layer Tests** ([test_transform.py](tests/test_transform.py))
- ✅ Duration conversion (ms → seconds)
- ✅ Date parsing and year extraction
- ✅ Null value handling (popularity, album names)
- ✅ String-to-list parsing for JSON fields
- ✅ Data type validations
- ✅ Edge cases (empty DataFrames, all-null values)

### **2. Django Application Tests** ([playlist_analyzer/dashboard/tests.py](playlist_analyzer/dashboard/tests.py))

#### **Model Tests**
- ✅ Playlist creation and string representation
- ✅ Track creation with JSONField arrays
- ✅ `unique_together` constraints (prevents duplicates)
- ✅ Foreign key relationships

#### **View Tests**
- ✅ Index page rendering
- ✅ Authentication requirements
- ✅ Dashboard data aggregation (top artists, genres)
- ✅ User playlist listing
- ✅ End-to-end playlist analysis workflow (mocked)

#### **UPSERT Logic Tests**
- ✅ Creating new tracks from DataFrame
- ✅ Updating existing tracks (idempotent behavior)
- ✅ Bulk operations performance

## Running Tests

### **Prerequisites**
```bash
pip install pytest pytest-django pytest-cov
```

### **1. Run ETL Unit Tests**

**All tests:**
```bash
pytest tests/
```

**Specific test file:**
```bash
pytest tests/test_extract.py
pytest tests/test_transform.py
```

**With coverage report:**
```bash
pytest tests/ --cov=scripts --cov-report=html
```

**Verbose output:**
```bash
pytest tests/ -v
```

### **2. Run Django Tests**

**All Django tests:**
```bash
cd playlist_analyzer
python manage.py test dashboard
```

**Specific test class:**
```bash
python manage.py test dashboard.tests.PlaylistModelTest
python manage.py test dashboard.tests.TrackModelTest
python manage.py test dashboard.tests.DashboardViewsTest
```

**With coverage:**
```bash
coverage run --source='.' manage.py test dashboard
coverage report
coverage html  # Generates htmlcov/index.html
```

**Verbose output:**
```bash
python manage.py test dashboard --verbosity=2
```

### **3. Run All Tests**

**Quick test suite:**
```bash
# ETL tests
pytest tests/

# Django tests
cd playlist_analyzer && python manage.py test dashboard
```

## Test Strategy

### **Unit Tests**
- **Purpose**: Test individual functions and components in isolation
- **Mocking**: Uses `unittest.mock` to mock external dependencies (Spotify API, database)
- **Fast**: No real API calls or database writes
- **Run Frequency**: On every code change

### **Integration Tests** (Future Enhancement)
- **Purpose**: Test complete workflows end-to-end
- **Real Dependencies**: Use test database and mock Spotify API
- **Slower**: Involves actual database operations
- **Run Frequency**: Before commits and in CI/CD pipeline

## Writing New Tests

### **For ETL Scripts**

```python
# tests/test_new_feature.py
import unittest
from unittest.mock import patch, Mock
from scripts.new_feature import some_function

class TestNewFeature(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures"""
        self.test_data = [...]

    @patch('scripts.new_feature.external_dependency')
    def test_some_function(self, mock_dependency):
        """Test function with mocked dependency"""
        mock_dependency.return_value = "mocked_result"
        result = some_function()
        self.assertEqual(result, "expected_value")
```

### **For Django Views/Models**

```python
# playlist_analyzer/dashboard/tests.py
from django.test import TestCase
from .models import MyModel

class MyModelTest(TestCase):
    def setUp(self):
        """Create test data"""
        self.user = User.objects.create_user(...)

    def test_model_creation(self):
        """Test model creation"""
        obj = MyModel.objects.create(...)
        self.assertEqual(obj.field, expected_value)
```

## Mock Data Examples

### **Mock Spotify API Response**
```python
mock_track_response = {
    'items': [
        {
            'track': {
                'id': 'track123',
                'name': 'Test Song',
                'duration_ms': 200000,
                'popularity': 80,
                'album': {
                    'id': 'album123',
                    'name': 'Test Album',
                    'release_date': '2023-01-01'
                },
                'artists': [
                    {'id': 'artist123', 'name': 'Test Artist'}
                ]
            }
        }
    ],
    'next': None
}
```

### **Mock DataFrame**
```python
import pandas as pd

mock_df = pd.DataFrame({
    'track_id': ['track1', 'track2'],
    'track_name': ['Song 1', 'Song 2'],
    'track_duration_ms': [200000, 180000],
    'artist_names': [['Artist 1'], ['Artist 2']],
    'track_genres': [['pop'], ['rock']]
})
```

## Continuous Integration (Future)

### **GitHub Actions Workflow**
```yaml
# .github/workflows/tests.yml
name: Run Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run ETL tests
        run: pytest tests/
      - name: Run Django tests
        run: cd playlist_analyzer && python manage.py test
```

## Test Coverage Goals

| Component | Current Coverage | Target |
|-----------|-----------------|--------|
| Extract Scripts | ~80% | 90% |
| Transform Scripts | ~85% | 95% |
| Django Models | ~90% | 95% |
| Django Views | ~75% | 85% |
| Overall | ~80% | 90% |

## Common Testing Patterns

### **1. Testing UPSERT Logic**
```python
def test_upsert_behavior(self):
    # Create initial record
    obj = Model.objects.create(id='test', value=1)

    # Update with same ID
    load_function(df_with_same_id_but_value_2)

    # Verify update, not duplicate
    self.assertEqual(Model.objects.count(), 1)
    self.assertEqual(Model.objects.get(id='test').value, 2)
```

###  **2. Testing Authentication**
```python
def test_requires_login(self):
    response = self.client.get(url)
    # Should redirect to login
    self.assertEqual(response.status_code, 302)

    # After login, should work
    self.client.login(username='user', password='pass')
    response = self.client.get(url)
    self.assertEqual(response.status_code, 200)
```

### **3. Testing with Mocks**
```python
@patch('module.external_api_call')
def test_with_mock(self, mock_api):
    mock_api.return_value = {'data': 'test'}
    result = function_that_calls_api()
    mock_api.assert_called_once()
    self.assertEqual(result, expected)
```

## Troubleshooting

### **Import Errors**
```bash
# Make sure you're in the correct directory
pytest tests/  # From project root
python manage.py test  # From playlist_analyzer/
```

### **Database Issues (Django)**
```bash
# Reset test database
python manage.py migrate --run-syncdb
python manage.py test --keepdb  # Reuse test database
```

### **Mock Not Working**
```python
# Ensure patch target is correct
@patch('module_where_used.function')  # Not where defined!
```

## Next Steps

1. **Add Integration Tests**: Full end-to-end workflows
2. **Set up CI/CD**: Automated testing on every commit
3. **Increase Coverage**: Aim for 90%+ test coverage
4. **Performance Tests**: Load testing for large playlists (1000+ tracks)
5. **Security Tests**: SQL injection, XSS prevention validation

## Additional Resources

- [pytest Documentation](https://docs.pytest.org/)
- [Django Testing Documentation](https://docs.djangoproject.com/en/stable/topics/testing/)
- [unittest.mock Guide](https://docs.python.org/3/library/unittest.mock.html)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
