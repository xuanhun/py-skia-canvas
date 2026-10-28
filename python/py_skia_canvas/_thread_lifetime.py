"""Windows Python host lifetime for original owner-local Rust/Skia resources."""
import atexit
import sys
import threading

_owners = threading.local()


class _Owner:
    """ID-free lifetime token; destruction stays on its creating Python thread."""
    def __init__(self, release):
        self.release = release

    def __del__(self):
        """Release resources and Vulkan context before Windows DLL thread-detach.

        No units/return value or transfers. A native borrow error remains an
        unraisable Python error, never a fabricated success. Source: original
        VK_CONTEXT Option destructor, invoked earlier by the Python host.
        """
        self.release()


def ensure_owner():
    """Arm once per Windows owner thread; other platforms retain Rust TLS cleanup.

    No units/return/errors under ordinary construction. No GPU objects live in
    Python thread-local storage; its token calls the native owner cleanup hook.
    """
    if sys.platform == 'win32' and not hasattr(_owners, 'token'):
        from . import _native
        _owners.token = _Owner(_native._release_thread)


def _main_exit():
    """Drop main thread token while native module and OS loader are still alive."""
    if hasattr(_owners, 'token'):
        del _owners.token


atexit.register(_main_exit)
