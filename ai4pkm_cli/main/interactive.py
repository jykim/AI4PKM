"""Interactive mode for ai4pkm CLI using Claude Code with streaming JSON I/O."""

import json
import subprocess
import sys
import threading
from pathlib import Path


class StreamParser:
    """
    Parses Claude CLI stream-json output and converts to ai4pkm format.
    
    Output format: {"type": "system|text|tool_begin|tool_input|tool_end|result", "output": "..."}
    
    Tool lifecycle:
    - tool_begin: tool name (e.g., "WebSearch")
    - tool_input: streaming input JSON fragments
    - tool_end: tool execution result
    """
    
    def __init__(self):
        self.current_block_type = None  # 'text', 'tool_use'
        self.current_tool_name = None
    
    def emit(self, msg_type: str, output):
        """Print a message in ai4pkm JSON format. Output can be str or dict."""
        print(json.dumps({"type": msg_type, "output": output}), flush=True)
    
    def parse_line(self, line: str) -> bool:
        """
        Parse a Claude CLI JSON line and emit ai4pkm format.
        
        Returns True if this was a 'result' message (response complete).
        """
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            # Not JSON - likely an error message from Claude CLI
            if line.strip():
                self.emit('error', line.strip())
            return False
        
        msg_type = msg.get('type')
        
        # System init message - include all available info
        if msg_type == 'system' and msg.get('subtype') == 'init':
            system_info = {
                'session_id': msg.get('session_id'),
                'cwd': msg.get('cwd'),
                'model': msg.get('model'),
                'tools': msg.get('tools', []),
                'mcp_servers': msg.get('mcp_servers', []),
                'permission_mode': msg.get('permissionMode'),
                'slash_commands': msg.get('slash_commands', []),
                'claude_code_version': msg.get('claude_code_version'),
                'agents': msg.get('agents', []),
                'skills': msg.get('skills', []),
                'plugins': msg.get('plugins', []),
            }
            self.emit('system', system_info)
            return False
        
        # Stream events (deltas)
        if msg_type == 'stream_event':
            event = msg.get('event', {})
            event_type = event.get('type')
            
            # Content block start - track what type we're receiving
            if event_type == 'content_block_start':
                block = event.get('content_block', {})
                self.current_block_type = block.get('type')
                
                if self.current_block_type == 'tool_use':
                    self.current_tool_name = block.get('name', 'unknown')
                    # Emit tool_begin with tool name
                    self.emit('tool_begin', self.current_tool_name)
                return False
            
            # Content block delta - emit the delta
            if event_type == 'content_block_delta':
                delta = event.get('delta', {})
                delta_type = delta.get('type')
                
                if delta_type == 'text_delta':
                    text = delta.get('text', '')
                    if text:
                        self.emit('text', text)
                
                elif delta_type == 'input_json_delta':
                    # Stream tool input fragments
                    partial = delta.get('partial_json', '')
                    if partial:
                        self.emit('tool_input', partial)
                
                return False
            
            # Content block stop
            if event_type == 'content_block_stop':
                self.current_block_type = None
                self.current_tool_name = None
                return False
        
        # User message with tool result
        if msg_type == 'user':
            message = msg.get('message', {})
            content = message.get('content', [])
            for item in content:
                if isinstance(item, dict) and item.get('type') == 'tool_result':
                    result_content = item.get('content', '')
                    self.emit('tool_end', result_content)
            return False
        
        # Result message - final summary with all available info
        if msg_type == 'result':
            result_info = {
                'duration_ms': msg.get('duration_ms'),
                'duration_api_ms': msg.get('duration_api_ms'),
                'num_turns': msg.get('num_turns'),
                'is_error': msg.get('is_error'),
                'session_id': msg.get('session_id'),
                'total_cost_usd': msg.get('total_cost_usd'),
                'usage': msg.get('usage'),
            }
            self.emit('result', result_info)
            return True
        
        return False


def _build_claude_cmd(system_prompt: str = None, session_id: str = None, use_resume: bool = True) -> list:
    """Build Claude CLI command with appropriate flags."""
    cmd = [
        'claude',
        '--permission-mode', 'bypassPermissions',
        '--input-format', 'stream-json',
        '--output-format', 'stream-json',
        '--verbose',
        '--include-partial-messages',
    ]
    
    if system_prompt:
        cmd.extend(['--system-prompt', system_prompt])
    
    if session_id:
        if use_resume:
            cmd.extend(['--resume', session_id])
        else:
            cmd.extend(['--session-id', session_id])
    
    return cmd


def _spawn_claude_process(cmd: list, cwd: Path):
    """Spawn Claude CLI subprocess."""
    return subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,  # Capture stderr separately for error detection
        text=True,
        encoding='utf-8',
        cwd=str(cwd),
        bufsize=1,
    )


def run_interactive_mode(working_dir: str = None, system_prompt: str = None, session_id: str = None):
    """
    Run interactive mode with Claude Code CLI.
    
    Spawns a single Claude CLI process with streaming JSON I/O and maintains
    a REPL loop for user interaction.
    
    Args:
        working_dir: Working directory for Claude Code (defaults to CWD)
        system_prompt: Optional system prompt for Claude Code
        session_id: Optional session ID to resume or create
    """
    cwd = Path(working_dir) if working_dir else Path.cwd()
    parser = StreamParser()
    
    # Try to spawn Claude CLI with session handling
    process = None
    try:
        if session_id:
            import time
            
            # First try --session-id (to create new session)
            cmd = _build_claude_cmd(system_prompt, session_id, use_resume=False)
            process = _spawn_claude_process(cmd, cwd)
            
            # Give Claude CLI time to start and potentially fail
            time.sleep(0.5)
            
            if process.poll() is not None:
                stderr_output = process.stderr.read()
                
                # Check if session already exists - retry with --resume
                if 'already' in stderr_output.lower() or 'exists' in stderr_output.lower() or 'in use' in stderr_output.lower():
                    parser.emit('info', f"Resuming existing session: {session_id}")
                    cmd = _build_claude_cmd(system_prompt, session_id, use_resume=True)
                    process = _spawn_claude_process(cmd, cwd)
                else:
                    parser.emit('error', stderr_output.strip() if stderr_output.strip() else "Claude CLI failed to start")
                    sys.exit(1)
        else:
            # No session ID - just start fresh
            cmd = _build_claude_cmd(system_prompt, None)
            process = _spawn_claude_process(cmd, cwd)
            
    except FileNotFoundError:
        print("Error: 'claude' CLI not found. Please install Claude Code CLI.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error starting Claude CLI: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Event to signal when we're waiting for a response to complete
    response_complete = threading.Event()
    # Flag to track if process is still running
    running = True
    
    def read_stdout():
        """Background thread to read Claude CLI stdout and emit ai4pkm JSON."""
        nonlocal running
        try:
            for line in process.stdout:
                if not running:
                    break
                line = line.rstrip('\n')
                if line:
                    # Parse and emit in ai4pkm format
                    is_result = parser.parse_line(line)
                    if is_result:
                        response_complete.set()
        except Exception as e:
            parser.emit('error', f"Reader error: {e}")
        finally:
            # Check if process exited with error
            exit_code = process.poll()
            if exit_code is not None and exit_code != 0:
                parser.emit('error', f"Claude CLI exited with code {exit_code}")
            running = False
            response_complete.set()  # Unblock main loop
    
    def read_stderr():
        """Background thread to read Claude CLI stderr and emit errors."""
        try:
            for line in process.stderr:
                line = line.rstrip('\n')
                if line:
                    parser.emit('error', line)
        except Exception:
            pass
    
    # Start reader threads
    reader_thread = threading.Thread(target=read_stdout, daemon=True)
    reader_thread.start()
    stderr_thread = threading.Thread(target=read_stderr, daemon=True)
    stderr_thread.start()
    
    # REPL loop
    try:
        while running:
            # Print prompt and wait for input
            try:
                user_input = input(">> ")
            except EOFError:
                # Ctrl+D pressed
                print("\nExiting interactive mode...")
                break
            except KeyboardInterrupt:
                # Ctrl+C pressed
                print("\nExiting interactive mode...")
                break
            
            # Skip empty input
            if not user_input.strip():
                continue
            
            # Check if process is still running
            if process.poll() is not None:
                print("Claude CLI process terminated unexpectedly.", file=sys.stderr)
                break
            
            # Clear response complete flag
            response_complete.clear()
            
            # Send user input as JSON message to Claude CLI stdin
            # Format: type + message object with role/content
            message = json.dumps({
                "type": "user",
                "message": {
                    "role": "user",
                    "content": user_input
                }
            })
            
            try:
                process.stdin.write(message + '\n')
                process.stdin.flush()
            except BrokenPipeError:
                print("Claude CLI process terminated.", file=sys.stderr)
                break
            except Exception as e:
                print(f"Error sending message: {e}", file=sys.stderr)
                break
            
            # Wait for response to complete (with timeout to allow interruption)
            while running and not response_complete.is_set():
                if response_complete.wait(timeout=0.1):
                    break
                # Check if process died
                if process.poll() is not None:
                    running = False
                    break
    
    finally:
        # Cleanup - try graceful shutdown first
        running = False
        if process.poll() is None:
            # Try to send EOF to stdin to signal we're done
            try:
                process.stdin.close()
            except Exception:
                pass
            # Give Claude CLI a moment to exit gracefully
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()

