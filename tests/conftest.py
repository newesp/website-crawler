import pytest

def pytest_collection_modifyitems(items):
    for item in items:
        fspath = str(item.fspath).replace("\\", "/")
        if "/tests/unit/" in fspath or "tests/unit/" in fspath:
            item.add_marker(pytest.mark.unit)
        elif "/tests/integration/" in fspath or "tests/integration/" in fspath:
            item.add_marker(pytest.mark.integration)
