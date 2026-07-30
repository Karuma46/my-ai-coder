from fastmcp.client.client import CallToolResult
from mcp.types import TextContent

from src.github.service import serialize_result
from src.projects.utils import extract_github_number, extract_github_value


def test_extracts_issue_reference_from_mcp_minimal_response() -> None:
    result = CallToolResult(
        content=[
            TextContent(
                type="text",
                text=('{"id":"2468013579","url":"https://github.com/rumatech/shoppa/issues/42"}'),
            )
        ],
        structured_content=None,
        meta=None,
        data=None,
        is_error=False,
    )

    serialized = serialize_result(result)

    assert (
        extract_github_number(
            serialized,
            ("number", "issue_number"),
            url_segment="issues",
        )
        == 42
    )
    assert (
        extract_github_value(serialized, ("url", "html_url", "issue_url"))
        == "https://github.com/rumatech/shoppa/issues/42"
    )


def test_extracts_pull_request_reference_from_mcp_minimal_response() -> None:
    result = {
        "content": [
            {
                "type": "text",
                "text": ('{"id":"975318642","url":"https://github.com/rumatech/shoppa/pull/17"}'),
            }
        ]
    }

    assert (
        extract_github_number(
            result,
            ("number", "pull_number", "pullNumber"),
            url_segment="pull",
        )
        == 17
    )
