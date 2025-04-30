"""
Global pytest configuration.

This file contains global pytest fixtures and configuration.
"""

import os
import socket

import pytest


def pytest_addoption(parser):
    """Add command-line options to pytest."""
    parser.addoption(
        "--allow-net",
        action="store_true",
        default=False,
        help="Allow network connections during tests",
    )


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "allow_net: mark test to allow network connections"
    )
    config.addinivalue_line("markers", "e2e: mark test as end-to-end test")


# Create a custom socket disabler since pytest-socket might not be available
class SocketBlocker:
    """Block socket connections."""

    def __init__(self):
        self._original_socket = socket.socket
        self.is_enabled = True

    def disable(self):
        """Disable socket connections."""
        if self.is_enabled:
            return

        def guarded_socket(*_args, **_kwargs):
            raise RuntimeError("Network connections are disabled during tests")

        socket.socket = guarded_socket
        self.is_enabled = False

    def enable(self):
        """Enable socket connections."""
        if not self.is_enabled:
            socket.socket = self._original_socket
            self.is_enabled = True


@pytest.fixture(scope="session")
def socket_blocker():
    """Fixture to block socket connections."""
    blocker = SocketBlocker()
    blocker.disable()  # Start with sockets disabled
    yield blocker
    blocker.enable()  # Restore original socket at the end


@pytest.fixture(autouse=True)
def disable_network_calls(request, socket_blocker):
    """
    Disable network calls for all tests by default.

    This fixture is automatically applied to all tests. Network calls are allowed only if:
    1. The test is in the e2e folder
    2. The test is marked with @pytest.mark.allow_net
    3. The --allow-net flag is passed to pytest
    """
    # Check if test is in e2e folder
    test_path = request.node.fspath.strpath
    is_e2e_test = os.path.sep + "e2e" + os.path.sep in test_path

    # Check if test has allow_net marker or --allow-net flag is set
    has_allow_net_marker = request.node.get_closest_marker("allow_net") is not None
    allow_net_flag = request.config.getoption("--allow-net")

    # Allow network if any condition is met
    if is_e2e_test or has_allow_net_marker or allow_net_flag:
        # Enable network
        socket_blocker.enable()
        yield
        # Disable network after test
        socket_blocker.disable()
    else:
        # Keep network disabled
        yield
