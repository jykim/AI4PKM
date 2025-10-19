# HelloWorld Agent

Simple demonstration of AI-driven agent using AGENT.md.

## How It Works

This agent uses `AGENT.md` with the prompt: "Say Hello World"

When a YAML file is placed in `Requests/`, the AI receives:
- Framework context from `Agents/AGENT.md`
- Agent prompt from `Agents/HelloWorld/AGENT.md`
- The YAML content automatically

## Usage

```bash
cat > Agents/HelloWorld/Requests/test.yaml << 'EOF'
message: Hello World
name: AI4PKM User
EOF
```

The agent will:
1. Detect YAML file
2. Process with AI (framework prompts + agent prompts + YAML content)
3. Save AI response to Completed/
4. Remove original file from Requests/

## Example Result

Check `Completed/` folder:

```yaml
request:
  message: Hello World
  name: AI4PKM User
response: |
  Hello World! Welcome, AI4PKM User!
  
  I've processed your request according to the agent instructions.
timestamp: '2025-10-18T00:20:15.123456'
```

## Note

This is a minimal example. For real use cases, see **EmailSender** agent.
