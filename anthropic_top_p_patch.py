"""
Patch for Anthropic SDK to remove top_p parameter before sending to API.

This patch intercepts calls to the Anthropic Messages API and removes
the top_p parameter to ensure compatibility with Claude Haiku 4.5 and
other models that don't support using both top_p and temperature.

Usage:
    import anthropic_top_p_patch
    # Now use anthropic client normally

The patch works by wrapping the Messages.create() method to strip out
the top_p parameter before calling the original method.
"""

import anthropic
from functools import wraps

# Store the original create methods
_original_sync_create = anthropic.resources.messages.Messages.create
_original_async_create = anthropic.resources.messages.AsyncMessages.create

def _create_wrapper(original_func):
    """Wrapper that removes top_p from kwargs before calling the original function."""
    @wraps(original_func)
    def sync_wrapper(self, *args, **kwargs):
        # Remove top_p if present
        kwargs.pop('top_p', None)
        return original_func(self, *args, **kwargs)
    
    @wraps(original_func)
    async def async_wrapper(self, *args, **kwargs):
        # Remove top_p if present
        kwargs.pop('top_p', None)
        return await original_func(self, *args, **kwargs)
    
    # Return appropriate wrapper based on whether function is async
    import inspect
    if inspect.iscoroutinefunction(original_func):
        return async_wrapper
    else:
        return sync_wrapper

# Apply the patches
anthropic.resources.messages.Messages.create = _create_wrapper(_original_sync_create)
anthropic.resources.messages.AsyncMessages.create = _create_wrapper(_original_async_create)

print("✓ Anthropic SDK patched: top_p parameter will be automatically removed from all API requests")
