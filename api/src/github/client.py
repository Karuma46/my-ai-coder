import logging
import re
import traceback
from typing import Any

from fastmcp import Client
from fastmcp.client.transports import StdioTransport, StreamableHttpTransport
from fastmcp.exceptions import ToolError
from mcp import McpError

from src.github.config import GithubSettings
from src.github.exceptions import GithubConfigurationError, GithubUpstreamError

logger = logging.getLogger("uvicorn.error")

GITHUB_TOKEN_PATTERN = re.compile(r"\b(?:github_pat_[A-Za-z0-9_]+|gh[pousr]_[A-Za-z0-9]+)\b")


def _redact_sensitive_text(settings: GithubSettings, value: str) -> str:
    token = settings.personal_access_token
    if token is not None:
        token_value = token.get_secret_value()
        if token_value:
            value = value.replace(token_value, "[REDACTED]")
    return GITHUB_TOKEN_PATTERN.sub("[REDACTED]", value)


def _safe_error_detail(settings: GithubSettings, exc: Exception) -> str:
    detail = str(exc).strip() or exc.__class__.__name__
    return _redact_sensitive_text(settings, detail)


def _safe_traceback(settings: GithubSettings, exc: Exception) -> str:
    formatted = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    return _redact_sensitive_text(settings, formatted).rstrip()


def create_github_client(settings: GithubSettings) -> Client:
    if not settings.enabled:
        raise GithubConfigurationError("GitHub MCP integration is disabled")

    token = settings.personal_access_token
    if token is None or not token.get_secret_value():
        raise GithubConfigurationError("GITHUB_PERSONAL_ACCESS_TOKEN is not configured")
    if not settings.owner:
        raise GithubConfigurationError("GITHUB_OWNER is not configured")

    if settings.mcp_transport == "http":
        return Client(
            StreamableHttpTransport(
                url=settings.mcp_url,
                headers={"Authorization": f"Bearer {token.get_secret_value()}"},
            )
        )

    transport = StdioTransport(
        command="docker",
        args=[
            "run",
            "-i",
            "--rm",
            "-e",
            "GITHUB_PERSONAL_ACCESS_TOKEN",
            "-e",
            "GITHUB_TOOLSETS",
            settings.mcp_image,
            "stdio",
        ],
        env={
            "GITHUB_PERSONAL_ACCESS_TOKEN": token.get_secret_value(),
            "GITHUB_TOOLSETS": settings.toolsets,
        },
        keep_alive=False,
    )
    return Client(transport)


async def call_github_tool(
    settings: GithubSettings,
    tool_name: str,
    arguments: dict[str, Any],
) -> Any:
    try:
        client = create_github_client(settings)
        async with client:
            return await client.call_tool(tool_name, arguments)
    except GithubConfigurationError:
        raise
    except (McpError, ToolError, OSError, RuntimeError) as exc:
        detail = _safe_error_detail(settings, exc)
        logger.error(
            "GitHub MCP operation '%s' failed for repository '%s': %s\n%s",
            tool_name,
            arguments.get("repo", "<unknown>"),
            detail,
            _safe_traceback(settings, exc),
        )
        raise GithubUpstreamError(f"GitHub MCP operation '{tool_name}' failed: {detail}") from exc


async def list_github_tools(settings: GithubSettings) -> list[Any]:
    try:
        client = create_github_client(settings)
        async with client:
            return list(await client.list_tools())
    except GithubConfigurationError:
        raise
    except (McpError, ToolError, OSError, RuntimeError) as exc:
        detail = _safe_error_detail(settings, exc)
        logger.error(
            "Unable to list GitHub MCP tools: %s\n%s",
            detail,
            _safe_traceback(settings, exc),
        )
        raise GithubUpstreamError(f"Unable to list GitHub MCP tools: {detail}") from exc
