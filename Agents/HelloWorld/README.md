# HelloWorld Agent

Simple demonstration of AI-driven agent using AGENT.md.

## How It Works

This agent uses `AGENT.md` with the prompt: "Say Hello World"

When a JSON file is placed in `Requests/`, the AI receives:
- The prompt from AGENT.md
- The JSON content automatically

## Usage

```bash
echo '{"message": "Hello World"}' > Agents/HelloWorld/Requests/test.json
```

The agent will:
1. Detect JSON file
2. Move to InProgress/
3. Process with AI (prompt + JSON content)
4. Move to Completed/

## Note

This is a minimal example. For real use cases, see **EmailSender** agent.

