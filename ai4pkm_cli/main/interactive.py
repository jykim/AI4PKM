"""Interactive mode for ai4pkm CLI using Claude Code with streaming JSON I/O."""

import json
import os
import platform
import shutil
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
        
            # Message delta - partial message updates
            if event_type == 'message_delta':
                delta = event.get('delta', {})
                delta_type = delta.get('type')

                if delta.get('stop_reason'):
                    self.emit('message_delta_stop', delta.get('stop_reason'))
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


def _build_claude_cmd(system_prompt: str = None, system_prompt_file: Path = None, append_system_prompt: str = None, append_system_prompt_file: Path = None, session_id: str = None, use_resume: bool = True) -> list:
    """Build Claude CLI command with appropriate flags."""
    cmd = [
        'claude',
        '--permission-mode', 'bypassPermissions',
        '--input-format', 'stream-json',
        '--output-format', 'stream-json',
        '--verbose',
        '--include-partial-messages',
    ]
    
    if system_prompt_file:
        cmd.extend(['--system-prompt-file', str(system_prompt_file)])
    
    if system_prompt:
        cmd.extend(['--system-prompt', system_prompt])
    
    if append_system_prompt_file:
        cmd.extend(['--append-system-prompt-file', str(append_system_prompt_file)])
    
    if append_system_prompt:
        cmd.extend(['--append-system-prompt', append_system_prompt])
    
    if session_id:
        if use_resume:
            cmd.extend(['--resume', session_id])
        else:
            cmd.extend(['--session-id', session_id])
    
    return cmd


def _spawn_claude_process(cmd: list, cwd: Path):
    """Spawn Claude CLI subprocess."""
    # On Windows, resolve .cmd/.bat files to their full paths
    if platform.system() == 'Windows' and cmd:
        executable = cmd[0]
        # Try to find the executable (handles .cmd, .bat, .exe)
        resolved = shutil.which(executable)
        if resolved:
            # Use the resolved full path
            cmd = [resolved] + cmd[1:]
        elif not os.path.splitext(executable)[1]:  # No extension
            # Try .cmd extension explicitly
            cmd_cmd = executable + '.cmd'
            resolved_cmd = shutil.which(cmd_cmd)
            if resolved_cmd:
                cmd = [resolved_cmd] + cmd[1:]
    
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


def _encode_project_path(path: str) -> str:
    """
    Encode a path to Claude CLI's project path format.
    
    Claude CLI:
    1. Splits path by separators (/, \\)
    2. Encodes each part:
       - keeps ASCII alphanumerics as-is
       - converts all other characters to dashes
       - non-ASCII characters are converted to dashes based on UTF-8 byte length
    3. Joins with dashes, but skips separator if next part starts with dash
    
    Example: /Users/foo/주식AI → -Users-foo------AI
    
    Note: macOS returns paths in NFD (decomposed) form, but Claude CLI
    uses NFC (composed) form, so we normalize first.
    """
    import unicodedata
    import re

    def _encode_part(part: str) -> str:
        out = []
        for ch in part:
            if ch.isascii() and ch.isalnum():
                out.append(ch)
            elif ch.isascii():
                out.append('-')
            else:
                # Non-ASCII: one dash per UTF-8 byte
                out.append('-' * len(ch.encode('utf-8')))
        return ''.join(out)

    # Normalize to NFC (composed form) - macOS often uses NFD which has more chars
    normalized = unicodedata.normalize('NFC', path)
    encoded_parts = [_encode_part(p) for p in re.split(r'[/\\]', normalized)]

    # Join with dashes, but skip separator if next part starts with dash
    result = []
    for i, part in enumerate(encoded_parts):
        if i and part and not part.startswith('-'):
            result.append('-')
        result.append(part)
    return ''.join(result)


def _session_exists(session_id: str, cwd: Path) -> bool:
    """
    Check if a Claude session exists by looking for its session file.
    
    Session files are stored at: ~/.claude/projects/{project-path}/{session-id}.jsonl
    Project path is encoded with non-ASCII chars replaced by dashes.
    
    Returns True if session file exists AND is valid.
    A valid session file must have a first line that is JSON with parentUuid: null.
    If file exists but is invalid/corrupted, deletes it and returns False.
    """
    # Both possible Claude session directories
    claude_dirs = [
        Path.home() / '.claude' / 'projects',
        Path.home() / 'projects',
    ]
    session_filename = f"{session_id}.jsonl"
    
    # Encode path like Claude CLI does (non-ASCII bytes → dashes)
    project_path = _encode_project_path(str(cwd.resolve()))
    
    # Check both possible locations
    for claude_dir in claude_dirs:
        session_file = claude_dir / project_path / session_filename
        
        print(json.dumps({
            "type": "debug",
            "output": f"Checking session: {session_file} (exists: {session_file.exists()})"
        }), flush=True)
        
        if not session_file.exists():
            continue
        
        # Validate session file: first non-queue-operation line must have parentUuid field
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                lines = [f.readline().strip() for _ in range(10)]  # Read up to 10 lines
        except (IOError, OSError, PermissionError) as e:
            # File exists but can't be read - likely locked by another process
            # Assume it's valid and in use
            print(json.dumps({
                "type": "debug",
                "output": f"Session file locked/in-use, assuming valid: {e}"
            }), flush=True)
            return True
        
        # File was read successfully - now validate content
        is_valid = False
        invalid_reason = None
        
        # Filter out empty lines
        lines = [line for line in lines if line]
        
        if not lines:
            invalid_reason = "Empty session file"
        else:
            try:
                # Find first non-queue-operation entry
                first_entry = None
                for line in lines:
                    entry = json.loads(line)
                    if entry.get('type') != 'queue-operation':
                        first_entry = entry
                        break
                
                if first_entry is None:
                    invalid_reason = "No non-queue-operation entries found"
                elif 'parentUuid' in first_entry:
                    is_valid = True
                else:
                    invalid_reason = "First entry missing parentUuid field"
            except json.JSONDecodeError as e:
                invalid_reason = f"Invalid JSON: {e}"
        
        if is_valid:
            print(json.dumps({
                "type": "debug",
                "output": f"Session file valid (parentUuid: null)"
            }), flush=True)
            return True
        
        # Invalid/corrupted session file - delete and treat as new
        print(json.dumps({
            "type": "debug",
            "output": f"Invalid session file, deleting: {invalid_reason}"
        }), flush=True)
        try:
            session_file.unlink()
        except Exception:
            pass
        continue  # Check next location
    
    return False


def run_interactive_mode(working_dir: str = None, system_prompt: str = None, system_prompt_file: Path = None, append_system_prompt: str = None, append_system_prompt_file: Path = None, session_id: str = None):
    """
    Run interactive mode with Claude Code CLI.
    
    Spawns a single Claude CLI process with streaming JSON I/O and maintains
    a REPL loop for user interaction.
    
    Args:
        working_dir: Working directory for Claude Code (defaults to CWD)
        system_prompt: Optional system prompt for Claude Code
        system_prompt_file: Optional path to file containing system prompt
        append_system_prompt: Optional additional system prompt to append
        append_system_prompt_file: Optional path to file containing additional system prompt to append
        session_id: Optional session ID to resume or create
    """
    cwd = Path(working_dir) if working_dir else Path.cwd()
    parser = StreamParser()
    
    # Determine whether to use --resume or --session-id by checking if session exists
    use_resume = False
    if session_id:
        use_resume = _session_exists(session_id, cwd)
    
    cmd = _build_claude_cmd(system_prompt, system_prompt_file, append_system_prompt, append_system_prompt_file, session_id, use_resume=use_resume)
    
    try:
        process = _spawn_claude_process(cmd, cwd)
    except FileNotFoundError:
        print("Error: 'claude' CLI not found. Please install Claude Code CLI.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error starting Claude CLI: {e}", file=sys.stderr)
        sys.exit(1)
    
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
            if exit_code is not None and exit_code != 0:
                parser.emit('error', f"Claude CLI exited with code {exit_code}")
            running = False
            response_complete.set()
    
    def read_stderr():
        """Background thread to read Claude CLI stderr."""
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
            try:
                user_input = input(">> ")
            except EOFError:
                print("\nExiting interactive mode...")
                break
            except KeyboardInterrupt:
                print("\nExiting interactive mode...")
                break
            
            if not user_input.strip():
                continue
            
            if process.poll() is not None:
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
                print("Claude CLI process terminated.", file=sys.stderr)
                break
            except Exception as e:
                print(f"Error sending message: {e}", file=sys.stderr)
                break
            
            while running and not response_complete.is_set():
                if response_complete.wait(timeout=0.1):
                    break
                if process.poll() is not None:
                    running = False
                    break
    
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

