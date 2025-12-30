"""Interactive mode for ai4pkm CLI using Claude Code with streaming JSON I/O."""

import json
import subprocess
import sys
import threading
from pathlib import Path


class StreamParser:
    """
    Parses Claude CLI stream-json output and converts to ai4pkm format.
    
    Output format: {"type": "system|tool_use|text|result", "output": "..."}
    """
    
    def __init__(self):
        self.current_block_type = None  # 'text', 'tool_use', 'thinking'
        self.current_tool_name = None
        self.tool_input_buffer = ""
    
    def emit(self, msg_type: str, output: str):
        """Print a message in ai4pkm JSON format."""
        print(json.dumps({"type": msg_type, "output": output}), flush=True)
    
    def parse_line(self, line: str) -> bool:
        """
        Parse a Claude CLI JSON line and emit ai4pkm format.
        
        Returns True if this was a 'result' message (response complete).
        """
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            return False
        
        msg_type = msg.get('type')
        
        # System init message
        if msg_type == 'system' and msg.get('subtype') == 'init':
            self.emit('system', f"session:{msg.get('session_id', 'unknown')}")
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
                    self.tool_input_buffer = ""
                # For thinking blocks, we'll emit deltas as they come
                # For text blocks, we'll emit deltas as they come
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
                    # Tool input being built - accumulate
                    self.tool_input_buffer += delta.get('partial_json', '')
                
                return False
            
            # Content block stop - finalize tool_use if needed
            if event_type == 'content_block_stop':
                if self.current_block_type == 'tool_use' and self.current_tool_name:
                    self.emit('tool_use', f"{self.current_tool_name}: {self.tool_input_buffer}")
                    self.current_tool_name = None
                    self.tool_input_buffer = ""
                self.current_block_type = None
                return False
        
        # Result message - final summary
        if msg_type == 'result':
            duration = msg.get('duration_ms', 0) / 1000
            cost = msg.get('total_cost_usd', 0)
            self.emit('result', f"done in {duration:.1f}s, cost ${cost:.4f}")
            return True
        
        return False


def run_interactive_mode(working_dir: str = None, system_prompt: str = None):
    """
    Run interactive mode with Claude Code CLI.
    
    Spawns a single Claude CLI process with streaming JSON I/O and maintains
    a REPL loop for user interaction.
    
    Args:
        working_dir: Working directory for Claude Code (defaults to CWD)
        system_prompt: Optional system prompt for Claude Code
    """
    # Resolve working directory
    cwd = Path(working_dir) if working_dir else Path.cwd()
    
    # Build Claude CLI command with streaming flags
    # Using same base flags as _execute_claude_code in execution_manager.py
    cmd = [
        'claude',
        '--permission-mode', 'bypassPermissions',  # Same as execution_manager
        '--input-format', 'stream-json',
        '--output-format', 'stream-json',
        '--verbose',
        '--include-partial-messages',
    ]
    
    # Add system prompt if provided
    if system_prompt:
        cmd.extend(['--system-prompt', system_prompt])
    
    # Spawn Claude CLI process
    try:
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            cwd=str(cwd),
            bufsize=1,  # Line buffered
        )
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
    # Stream parser for converting Claude output to ai4pkm format
    parser = StreamParser()
    
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
        except Exception:
            pass
        finally:
            running = False
    
    # Start stdout reader thread
    reader_thread = threading.Thread(target=read_stdout, daemon=True)
    reader_thread.start()
    
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
        # Cleanup
        running = False
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()

