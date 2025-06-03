import argparse
import pytest

@pytest.fixture
def site_name():
    return "test-site"

@pytest.fixture
def url():
    return "https://example.com"

@pytest.fixture
def args(tmp_path):
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="https://example.com")
    parser.add_argument("--site", default="test-site")
    parser.add_argument("--items", type=int, default=1)
    return parser.parse_args([])

