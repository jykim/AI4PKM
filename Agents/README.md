# AI4PKM Agents

Agents are autonomous processors that monitor for JSON request files and execute tasks automatically.

## How Agents Work

### Discovery
The CLI automatically discovers any folder under `Agents/` (at any depth) that contains:
- `AGENT.md` - Prompts for AI-driven processing
- `agent.py` - Python handler for custom logic

### File Lifecycle
When a `.json` file is created in an agent's `Requests/` folder:

```
Requests/ → InProgress/ → [Processing] → Completed/
```

1. **Requests/** - JSON file placed here triggers the agent
2. **InProgress/** - File moved here immediately (with timestamp)
3. **Processing** - Agent processes the request
4. **Completed/** - File moved here when done (with timestamp)

### Processing Methods

**Priority: AGENT.md > agent.py**

#### AGENT.md (AI-Driven)
If `AGENT.md` exists, the AI agent processes the request:
- Reads prompts from `AGENT.md`
- **Automatically includes JSON content in the prompt**
- Executes with AI agent

Example prompt sent to AI:
```
{Content from AGENT.md}

---

Request File: example.json

JSON Content:
```json
{
  "key": "value"
}
```

Please process this request according to the instructions above.
```

#### agent.py (Python Handler)
If no `AGENT.md`, calls the `process()` function in `agent.py`:

```python
def process(json_content, file_path, event_type, logger, workspace_path):
    """
    Args:
        json_content: Parsed JSON dict from request file
        file_path: Path to file in InProgress folder
        event_type: 'created' or 'modified'
        logger: Logger instance
        workspace_path: Workspace root path
    """
    # Your processing logic here
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
├── Requests/                # Put *.json files here to trigger
├── InProgress/              # Auto-created during processing
├── Completed/               # Auto-created after processing
└── Responses/               # Optional: for agent outputs
```

## Important Rules

1. **✅ JSON files only** - Only `.json` files in `Requests/` trigger agents
2. **⚠️ Never write to Requests/** - Causes infinite loops
3. **📦 Automatic lifecycle** - Files move through folders automatically
4. **🎯 One handler** - Use either `AGENT.md` OR `agent.py`, not both

## Examples

See existing agents:
- **EmailSender** - Python handler that sends emails via Gmail
- **HelloWorld** - AI-driven agent for simple demonstrations

