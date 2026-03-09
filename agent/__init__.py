# Markaz Sentinel agent package.
# Import platform_compat FIRST to install the pygetwindow shim on macOS
# before any collectors try to import pygetwindow.
from . import platform_compat  # noqa: F401
