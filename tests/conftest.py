"""Pytest configuration for OpenCaptchaWorld agent tests."""

import pytest


def pytest_addoption(parser):
    """Add custom command line options for pytest."""
    parser.addoption(
        "--agent-url",
        action="store",
        default="http://localhost:9010",
        help="Agent URL to test against (default: http://localhost:9010)"
    )


@pytest.fixture
def agent_url(request):
    """Fixture to provide the agent URL from command line."""
    return request.config.getoption("--agent-url")
