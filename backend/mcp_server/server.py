from mcp.server import MCPServer

# queries.py handles its own sys.path setup for chroma_client/metadata imports
from queries import get_top_stories, get_story_confidence

# The MCP server is a thin adapter: protocol in, queries.py out. All actual
# logic lives in queries.py, which stays testable without any MCP client.
mcp = MCPServer(
    name="cerix",
    instructions=(
        "Cerix is an impact classifier for tech news: it rates stories by "
        "objective impact, not engagement. Use it to find what actually "
        "matters in tech right now and how well-sourced each story is."
    ),
)


@mcp.tool()
def top_stories(
    category: str | None = None,
    min_score: int | None = None,
    limit: int = 10,
) -> list[dict]:
    """Get the highest-impact tech news stories Cerix is currently tracking.

    Every story has an impact score (1-10, where 1-2 is niche, 5-6 clearly
    matters to the tech industry, 9-10 is a generational turning point) and
    one or more categories:
      - industry_shifting: changes how the tech field works going forward
      - cultural_moment: spilling into mainstream/general public awareness
      - hot: plugged-in tech people should know this week (time-sensitive)
      - insight: high-signal opinion or analysis, not news
      - noise: high engagement but low actual impact (quarantined)

    Args:
        category: optional filter to one category slug from the list above
        min_score: optional minimum impact score (1-10)
        limit: maximum number of stories to return (default 10)

    Returns stories sorted by impact score, highest first, each with title,
    url, categories, score, and confidence_state.
    """
    return get_top_stories(category=category, min_score=min_score, limit=limit)


@mcp.tool()
def story_confidence(url: str) -> dict | None:
    """Check how well-sourced a specific news story is in Cerix.

    Looks up an article by URL and returns its confidence state:
      - rumored: a single source is reporting this — treat as unconfirmed
      - corroborated: multiple sources are reporting the same event
      - confirmed: verified against a first-party source (the organization
        or person the story is about, speaking for themselves) whose content
        supports the claim

    Also returns source_count (how many distinct source URLs Cerix has seen
    for this story). Returns null if Cerix has never seen this URL — that
    means "unknown to Cerix", not "false".

    Args:
        url: the article URL to look up (exact match, or a URL that was
             merged into a tracked story as a duplicate)
    """
    return get_story_confidence(url)


if __name__ == "__main__":
    # stdio transport: Claude Desktop (or any MCP client) spawns this process
    # and speaks JSON-RPC over stdin/stdout — no port, no network
    mcp.run(transport="stdio")
