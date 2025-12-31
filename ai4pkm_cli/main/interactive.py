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
    
    # Try with --session-id first (creates new), then --resume if session exists
    # This matches the behavior in execution_manager.py
    use_resume = False
    max_retries = 2
    pending_input = [None]  # Store input that triggered retry, to resend
    
    for attempt in range(max_retries):
        if session_id:
            cmd = _build_claude_cmd(system_prompt, session_id, use_resume=use_resume)
        else:
            cmd = _build_claude_cmd(system_prompt, None)
        
        try:
            process = _spawn_claude_process(cmd, cwd)
        except FileNotFoundError:
            print("Error: 'claude' CLI not found. Please install Claude Code CLI.", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error starting Claude CLI: {e}", file=sys.stderr)
            sys.exit(1)
        
        # Track if we need to retry with different session mode
        session_retry_needed = threading.Event()
        session_error_type = [None]
        
        # Event to signal when we're waiting for a response to complete
        response_complete = threading.Event()
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
                        is_result = parser.parse_line(line)
                        if is_result:
                            response_complete.set()
            except Exception as e:
                parser.emit('error', f"Reader error: {e}")
            finally:
                exit_code = process.poll()
                if exit_code is not None and exit_code != 0 and not session_retry_needed.is_set():
                    parser.emit('error', f"Claude CLI exited with code {exit_code}")
                running = False
                response_complete.set()
        
        def read_stderr():
            """Background thread to read Claude CLI stderr and detect session errors."""
            nonlocal running
            try:
                for line in process.stderr:
                    line = line.rstrip('\n')
                    if line:
                        line_lower = line.lower()
                        # Detect session errors that require retry
                        if session_id and not use_resume:
                            if 'already in use' in line_lower or 'already exists' in line_lower:
                                session_error_type[0] = 'exists'
                                session_retry_needed.set()
                                running = False
                                response_complete.set()
                                return
                        elif session_id and use_resume:
                            if 'no conversation found' in line_lower or 'not found' in line_lower:
                                session_error_type[0] = 'not_found'
                                session_retry_needed.set()
                                running = False
                                response_complete.set()
                                return
                        parser.emit('error', line)
            except Exception:
                pass
        
        # Start reader threads
        reader_thread = threading.Thread(target=read_stdout, daemon=True)
        reader_thread.start()
        stderr_thread = threading.Thread(target=read_stderr, daemon=True)
        stderr_thread.start()
        
        # REPL loop
        user_exited = False
        try:
            while running:
                try:
                    # If we have pending input from a retry, use that first
                    if pending_input[0]:
                        parser.emit('debug', f"Resending pending input: {pending_input[0]}")
                        user_input = pending_input[0]
                        pending_input[0] = None
                    else:
                        user_input = input(">> ")
                except EOFError:
                    print("\nExiting interactive mode...")
                    user_exited = True
                    break
                except KeyboardInterrupt:
                    print("\nExiting interactive mode...")
                    user_exited = True
                    break
                
                if not user_input.strip():
                    continue
                
                # Save input BEFORE checking process - session error may happen on startup
                pending_input[0] = user_input
                
                if process.poll() is not None:
                    if not session_retry_needed.is_set():
                        print("Claude CLI process terminated unexpectedly.", file=sys.stderr)
                    break
                
                response_complete.clear()
                
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
                    if not session_retry_needed.is_set():
                        print("Claude CLI process terminated.", file=sys.stderr)
                    break
                except Exception as e:
                    print(f"Error sending message: {e}", file=sys.stderr)
                    pending_input[0] = None  # Don't retry on other errors
                    break
                
                while running and not response_complete.is_set():
                    if response_complete.wait(timeout=0.1):
                        break
                    if process.poll() is not None:
                        running = False
                        break
                
                # Clear pending input after successful response (no retry needed)
                if not session_retry_needed.is_set():
                    pending_input[0] = None
        
        finally:
            running = False
            if process.poll() is None:
                try:
                    process.stdin.close()
                except Exception:
                    pass
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.terminate()
                    try:
                        process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        process.kill()
        
        # Check if we should retry with different session mode
        if session_retry_needed.is_set() and attempt < max_retries - 1:
            if session_error_type[0] == 'exists':
                parser.emit('info', f"Session exists, resuming: {session_id}")
                use_resume = True
                continue
            elif session_error_type[0] == 'not_found':
                parser.emit('info', f"Session not found, creating: {session_id}")
                use_resume = False
                continue
        
        # If user exited or no retry needed, we're done
        if user_exited or not session_retry_needed.is_set():
            break

