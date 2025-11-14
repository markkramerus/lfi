# Anthropic SDK top_p Patch

## Problem
Claude Haiku 4.5 and some other Anthropic models do not support using both `top_p` and `temperature` parameters simultaneously. If your code (or a library you're using like `agent_squad`) passes both parameters, you'll get an error:

```
anthropic.BadRequestError: Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error', 'message': 'top_p: Input should be a valid number'}}
```

## Solution
This patch automatically removes the `top_p` parameter from all Anthropic API requests before they are sent.

## Installation

1. The patch file `anthropic_top_p_patch.py` is already in your project directory.

2. Import it at the **very beginning** of your main application file, before any other anthropic imports:

```python
# Import the patch FIRST, before anything else
import anthropic_top_p_patch

# Now import and use your other modules normally
import anthropic
from agent_squad import Orchestrator
# ... rest of your imports
```

For your LFI project, add this to `main.py` at the very top:

```python
#!/usr/bin/env python3
"""Language-First Interoperability (LFI) main entry point."""

# IMPORTANT: Import patch first to fix top_p issue with Claude Haiku 4.5
import anthropic_top_p_patch

import asyncio
import sys
# ... rest of your imports
```

## How It Works

The patch monkey-patches the `transform` function used by the Anthropic SDK to process request parameters. When any request is made to the API, it:

1. Intercepts the request data
2. Removes the `top_p` parameter if present
3. Passes the cleaned data to the original transform function
4. The API receives the request without `top_p`

This is completely transparent - your code doesn't need any other changes.

## Verification

When you run your application, you should see this message at startup:
```
✓ Anthropic SDK patched: top_p parameter will be automatically removed from all API requests
```

If you see this message and no longer get the `top_p` error, the patch is working correctly.

## Important Notes

1. **Import Order Matters**: The patch MUST be imported before `anthropic` or any library that uses it (like `agent_squad`)

2. **No Code Changes Required**: Once imported, all Anthropic API calls will automatically have `top_p` stripped

3. **Temperature Still Works**: The patch only removes `top_p`, so you can still use `temperature` normally

4. **Thread-Safe**: The patch works across all threads and async operations

## Troubleshooting

### Still getting top_p errors?
- Verify the import is at the VERY TOP of your file
- Make sure it's imported before `import anthropic`
- Restart your application completely

### Need to debug?
Add this after the import to see what parameters are being sent:

```python
import anthropic_top_p_patch
# Add debug logging
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Alternative Solutions

If you prefer not to use a monkey patch:

1. **Fix at the Source**: If `agent_squad` is passing `top_p`, you could modify that library directly
2. **Update agent_squad**: Check if there's a newer version that doesn't pass `top_p`
3. **Contact Library Author**: Report the issue to the `agent_squad` maintainers

## Technical Details

The patch modifies:
- `anthropic._utils._transform.transform`
- `anthropic._utils._utils.transform`

Both functions are patched to ensure coverage across different import paths.
