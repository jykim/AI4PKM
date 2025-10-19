# AI4PKM Agents

Agents are autonomous processors that monitor for YAML request files and execute tasks automatically.

## How Agents Work

### Discovery
The CLI automatically discovers any folder under `Agents/` (at any depth) that contains:
- `AGENT.md` - Prompts for AI-driven processing
- `agent.py` - Python handler for custom logic

### File Lifecycle
When a `.yaml` file is created in an agent's `Requests/` folder:

```
Requests/*.yaml → [Processing] → Completed/*.yaml (with response/error)
```

1. **Requests/** - YAML file placed here triggers the agent
2. **Processing** - Agent processes the request
3. **Completed/** - Result saved with request/response or request/error pair
4. **Original file** - Removed from Requests/ after processing

###Processing Methods

**Priority: AGENT.md > agent.py**

#### AGENT.md (AI-Driven)
If `AGENT.md` exists, the AI agent processes the request:
- Reads framework prompts from `Agents/AGENT.md`
- Reads agent-specific prompts from agent's `AGENT.md`
- **Automatically includes YAML request data in the prompt**
- Returns response text

Example result in Completed/:
```yaml
request:
  to: user@example.com
  subject: Test
  body: Hello
response: |
  Email processed successfully
timestamp: 2025-10-18T00:00:00
```

#### agent.py (Python Handler)
If no `AGENT.md`, calls the `process()` function in `agent.py`:

```python
def process(request, logger, workspace_path):
    """
    Args:
        request: Parsed YAML dict from request file
        logger: Logger instance
        workspace_path: Workspace root path
        
    Returns:
        Response data (dict, str, etc.) or raises exception on error
    """
    # Your processing logic here
    return {"status": "success", "result": "..."}
```

Example result in Completed/:
```yaml
request:
  to: user@example.com
  subject: Test
response:
  status: sent
  message: Email sent successfully
timestamp: 2025-10-18T00:00:00
```

Error example:
```yaml
request:
  to: user@example.com
error: "Gmail credentials not configured"
timestamp: 2025-10-18T00:00:00
```

## Creating a New Agent

1. **Create agent folder**: `Agents/YourAgent/`
2. **Create Requests folder**: `Agents/YourAgent/Requests/`
3. **Choose processing method**:
   - `AGENT.md` for AI-driven processing
   - `agent.py` for Python logic
   - ⚠️ If both exist, only `AGENT.md` is used

### Folder Structure
```
Agents/YourAgent/
├── AGENT.md or agent.py    # Handler (choose one)
├── README.md                # Agent documentation
├── Requests/                # Put *.yaml files here to trigger
└── Completed/               # Results saved here (auto-created)
```

## Important Rules

1. **✅ YAML files only** - Only `.yaml` files in `Requests/` trigger agents
2. **✅ Auto-cleanup** - Original request files are removed after processing
3. **✅ Complete audit trail** - Every request gets a response or error in Completed/
4. **🎯 One handler** - Use either `AGENT.md` OR `agent.py`, not both

## Examples

See existing agents:
- **EmailSender** - Python handler that sends emails via Gmail
- **HelloWorld** - AI-driven agent for simple demonstrations

## Framework AGENT.md

The file `Agents/AGENT.md` contains framework-level prompts that explain the agent system to AI agents. This is automatically included when processing with `AGENT.md` handlers.
