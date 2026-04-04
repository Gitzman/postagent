"""Reserved handles blocklist and handle format validation."""

import re

RESERVED_HANDLES: frozenset[str] = frozenset(
    {
        # PostAgent system names
        "postagent",
        "admin",
        "root",
        "system",
        "api",
        "server",
        "broker",
        "mqtt",
        "inbox",
        "status",
        "card",
        "agent",
        "agents",
        "health",
        "support",
        "help",
        "info",
        "noreply",
        "postmaster",
        "webmaster",
        # Major tech companies
        "google",
        "microsoft",
        "apple",
        "amazon",
        "aws",
        "meta",
        "facebook",
        "twitter",
        "x",
        "oracle",
        "ibm",
        "intel",
        "nvidia",
        "adobe",
        "cisco",
        "salesforce",
        "vmware",
        "samsung",
        "tiktok",
        "bytedance",
        "alibaba",
        # AI labs and products
        "openai",
        "anthropic",
        "claude",
        "chatgpt",
        "gpt",
        "gemini",
        "bard",
        "deepmind",
        "mistral",
        "cohere",
        "llama",
        "copilot",
        "perplexity",
        "midjourney",
        "stability",
        "huggingface",
        # Cloud providers
        "azure",
        "gcp",
        "digitalocean",
        "heroku",
        "vercel",
        "netlify",
        "cloudflare",
        "fly",
        "railway",
        "render",
    }
)

_HANDLE_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")


def validate_handle(handle: str) -> str | None:
    """Validate a handle. Returns None if valid, error message if invalid."""
    if len(handle) < 3:
        return "Handle must be at least 3 characters."
    if len(handle) > 32:
        return "Handle must be at most 32 characters."
    if handle != handle.lower():
        return "Handle must be lowercase."
    if not _HANDLE_PATTERN.match(handle):
        if handle.startswith("-") or handle.endswith("-"):
            return "Handle must not start or end with a hyphen."
        if "--" in handle:
            return "Handle must not contain consecutive hyphens."
        return "Handle must contain only lowercase letters, digits, and hyphens."
    if "--" in handle:
        return "Handle must not contain consecutive hyphens."
    if handle in RESERVED_HANDLES:
        return f"The handle '{handle}' is reserved."
    return None
