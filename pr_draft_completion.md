# Add MCP completion utility support

This PR implements the completion utility from the MCP specification, addressing issue #1670. The completion utility provides IDE-like autocomplete suggestions for resource templates and prompts.

While FastMCP's client already supported sending completion requests, servers had no way to register handlers to provide custom completion suggestions.

This implementation adds a clean `@server.completion()` decorator that makes it trivial to add autocomplete functionality to any FastMCP server.

## Usage Example

```python
from fastmcp import FastMCP

server = FastMCP("My Server")

@server.prompt
async def analyze_data(dataset: str, analysis_type: str) -> str:
    return f"Analyzing {dataset} with {analysis_type}"

# Add completions for each argument
@server.completion("prompt", "analyze_data", "dataset")
async def complete_dataset(partial: str) -> list[str]:
    datasets = ["customers", "products", "sales", "inventory"]
    return [d for d in datasets if d.startswith(partial)]

@server.completion("prompt", "analyze_data", "analysis_type") 
async def complete_analysis_type(partial: str) -> list[str]:
    types = ["statistical", "trend", "comparative", "predictive"]
    return [t for t in types if t.startswith(partial)]
```
## Demo
Demo: `examples/completion_demo.py`

## MCP SDK Approach

```python
# MCP SDK approach - complex manual routing
@mcp.completion()
async def handle_completion(ref, argument, context):
    if isinstance(ref, PromptReference):
        if ref.name == "analyze_data" and argument.name == "dataset":
            # handle dataset completion
    if isinstance(ref, ResourceTemplateReference):
        if ref.uri == "file:///{path}" and argument.name == "path":
            # handle path completion
    return None
```

### FastMCP's approach

```python
# FastMCP approach - automatic routing, focused handlers
@server.completion("prompt", "analyze_data", "dataset")
async def complete_dataset(partial: str) -> list[str]:
    # focused handler just for dataset completion

@server.completion("resource_template", "file:///{path}", "path")
async def complete_path(partial: str) -> list[str]:
    # focused handler just for path completion
```

## Test Coverage

All existing tests pass with no regressions.

### New Tests:
**Server tests** (11):
- Handler registration and routing
- Prompt and resource template completion
- 100-item limit enforcement
- Error handling (exceptions, null returns)
- Edge cases (unicode, long strings, empty results)
- Multiple handlers per server

**Client tests** (13):
- Both `client.complete()` and `client.complete_mcp()` methods
- Partial matching and filtering
- Non-existent handlers and arguments
- Case-insensitive matching
- Large result sets and unicode support


## Files Changed

- `src/fastmcp/server/server.py`: Core completion implementation (123 lines added)
- `tests/server/test_completion.py`: Server-side test suite
- `tests/client/test_completion.py`: Client-side test suite  
- `examples/completion_demo.py`: Working demonstration server


## Backward Compatibility

Fully backward compatible:
- No changes to existing APIs
- Completion support is optional
- Servers without completion handlers return empty results
