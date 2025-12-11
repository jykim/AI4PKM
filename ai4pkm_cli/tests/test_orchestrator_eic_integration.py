"""Integration test for Orchestrator - EIC scenario.

This test validates the complete orchestrator workflow:
1. Starts orchestrator daemon
2. Creates test clipping file
3. Monitors: FileMonitor → Agent Match → Agent Execution → Task File → Output
4. Validates completion and cleanup

Test validates:
- Agent loads correctly
- File event triggers agent execution
- Task file created in tasks directory (from config) with IN_PROGRESS status
- Agent executes successfully
- Task file updated to PROCESSED status
- No duplicate executions
"""

import os
import sys
import time
import subprocess
import signal
import argparse
import re
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logger import Logger
from config import Config

logger = Logger(console_output=True)

class OrchestratorEICIntegrationTest:
    """Integration test for Orchestrator EIC workflow."""

    def __init__(self):
        """Initialize test environment."""

        # Use CWD as workspace (assumes test runs from vault directory)
        self.workspace_path = os.getcwd()

        # Check for config file in CWD
        config_path = os.path.join(self.workspace_path, 'orchestrator.yaml')
        if not os.path.exists(config_path):
            raise ValueError(
                f"orchestrator.yaml not found in current directory: {self.workspace_path}\n"
                f"Test must run from vault directory containing orchestrator.yaml"
            )

        # Load config from CWD
        self.config = Config(config_file=config_path)

        # Get orchestrator paths from config
        orchestrator_config = self.config.get_orchestrator_config()
        prompts_dir = orchestrator_config.get('prompts_dir', '_Settings_/Prompts')
        tasks_dir = orchestrator_config.get('tasks_dir', '_Tasks_')

        # Validate workspace
        required_folders = [tasks_dir, 'Ingest/Clippings', prompts_dir]
        for folder in required_folders:
            full_path = os.path.join(self.workspace_path, folder)
            if not os.path.exists(full_path):
                raise ValueError(f"Invalid test workspace: {full_path} does not exist")

        logger.info(f"Using test workspace: {self.workspace_path}")

        # Flag for existing daemon
        self.use_existing_daemon = False

        # Test file paths
        self.test_timestamp = datetime.now().strftime('%Y-%m-%d-%H%M%S')
        self.test_clipping_name = f"2025-10-17 Test Integration Article {self.test_timestamp}.md"
        self.test_clipping_path = os.path.join(
            self.workspace_path,
            "Ingest",
            "Clippings",
            self.test_clipping_name
        )

        # Task directory (from orchestrator config)
        tasks_dir_path = self.config.get_orchestrator_tasks_dir()
        self.tasks_dir = os.path.join(self.workspace_path, tasks_dir_path)

        # Daemon process
        self.daemon_process = None

        # Track created files
        self.created_files = []
        self.test_results = {
            'start_time': datetime.now(),
            'stages': {},
            'issues': [],
            'success': False
        }

    def start_orchestrator(self):
        """Start the orchestrator daemon."""
        logger.info("=" * 80)
        logger.info("STAGE 0: Starting Orchestrator Daemon")
        logger.info("=" * 80)

        # Skip if using existing daemon
        if self.use_existing_daemon:
            logger.info("⚠️  Using existing daemon (--use-existing-daemon)")
            self.test_results['stages']['daemon_started'] = {
                'success': True,
                'timestamp': datetime.now(),
                'note': 'Using existing daemon'
            }
            return True

        try:
            # Start orchestrator daemon
            daemon_log = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'orchestrator_output.log')
            daemon_log_file = open(daemon_log, 'w')

            logger.info(f"  Starting orchestrator from CWD: {self.workspace_path}")

            # Run orchestrator from CWD (inherits working directory from test)
            # Test assumes it's running from vault directory
            self.daemon_process = subprocess.Popen(
                [sys.executable, '-m', 'ai4pkm_cli.main.cli', '--orchestrator'],
                stdout=daemon_log_file,
                stderr=subprocess.STDOUT,
                text=True
            )

            # Store log file handle
            self.daemon_log_file = daemon_log_file
            self.daemon_log_path = daemon_log

            # Wait for initialization
            logger.info("  Waiting for orchestrator to initialize...")
            time.sleep(5)

            # Check if process is running
            if self.daemon_process.poll() is not None:
                daemon_log_file.close()
                with open(daemon_log, 'r') as f:
                    output = f.read()
                logger.error(f"✗ Orchestrator failed to start")
                logger.error(f"Output:\n{output}")
                self.test_results['issues'].append("Orchestrator failed to start")
                return False

            logger.info(f"✓ Orchestrator started (PID: {self.daemon_process.pid})")
            logger.info(f"  Log file: {daemon_log}")

            self.test_results['stages']['daemon_started'] = {
                'success': True,
                'timestamp': datetime.now(),
                'pid': self.daemon_process.pid,
                'log_file': daemon_log
            }
            return True

        except Exception as e:
            logger.error(f"✗ Failed to start orchestrator: {e}")
            self.test_results['issues'].append(f"Orchestrator start failed: {e}")
            return False

    def stop_orchestrator(self):
        """Stop the orchestrator daemon."""
        if self.use_existing_daemon:
            logger.info("\n⚠️  Leaving daemon running (--use-existing-daemon)")
            return

        if self.daemon_process:
            logger.info("\nStopping orchestrator...")
            try:
                self.daemon_process.send_signal(signal.SIGTERM)
                try:
                    self.daemon_process.wait(timeout=5)
                    logger.info("✓ Orchestrator stopped gracefully")
                except subprocess.TimeoutExpired:
                    logger.warning("Orchestrator didn't stop gracefully, forcing...")
                    self.daemon_process.kill()
                    self.daemon_process.wait()
                    logger.info("✓ Orchestrator force-stopped")

                if hasattr(self, 'daemon_log_file'):
                    self.daemon_log_file.close()

            except Exception as e:
                logger.error(f"Error stopping orchestrator: {e}")

    def create_test_clipping(self):
        """Create a test clipping file to trigger EIC."""
        logger.info("=" * 80)
        logger.info("STAGE 1: Creating test clipping file")
        logger.info("=" * 80)

        # Read template
        template_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'fixtures',
            'test_clipping_template.md'
        )

        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except FileNotFoundError:
            logger.error(f"✗ Template file not found: {template_path}")
            self.test_results['issues'].append(f"Template not found: {template_path}")
            return False

        try:
            os.makedirs(os.path.dirname(self.test_clipping_path), exist_ok=True)

            with open(self.test_clipping_path, 'w', encoding='utf-8') as f:
                f.write(content)

            self.created_files.append(self.test_clipping_path)

            logger.info(f"✓ Created test clipping: {self.test_clipping_path}")
            logger.info(f"  File size: {os.path.getsize(self.test_clipping_path)} bytes")

            # Brief wait for file system
            time.sleep(2)

            self.test_results['stages']['clipping_created'] = {
                'success': True,
                'timestamp': datetime.now(),
                'file': self.test_clipping_path
            }
            return True

        except Exception as e:
            logger.error(f"✗ Failed to create test clipping: {e}")
            self.test_results['issues'].append(f"Clipping creation failed: {e}")
            return False

    def wait_for_task_file(self, timeout=60):
        """Wait for orchestrator to create task file in configured tasks directory.

        Args:
            timeout: Maximum seconds to wait

        Returns:
            Path to task file if found, None otherwise
        """
        logger.info("\n" + "=" * 80)
        logger.info("STAGE 2: Waiting for task file creation")
        logger.info("=" * 80)

        start_time = time.time()
        task_file = None

        # Expected pattern: YYYY-MM-DD EIC - {filename}.md
        expected_pattern = r"^\d{4}-\d{2}-\d{2} EIC - .+\.md$"

        while time.time() - start_time < timeout:
            if os.path.exists(self.tasks_dir):
                for filename in os.listdir(self.tasks_dir):
                    if not re.match(expected_pattern, filename):
                        continue

                    filepath = os.path.join(self.tasks_dir, filename)

                    # Check if file was created after test started
                    file_mtime = os.path.getmtime(filepath)
                    if file_mtime > self.test_results['start_time'].timestamp():
                        # Verify it's for our test file
                        if 'Test Integration' in filename:
                            task_file = filepath
                            self.created_files.append(filepath)
                            break

            if task_file:
                break

            time.sleep(1)

        if task_file:
            logger.info(f"✓ Task file created: {os.path.basename(task_file)}")
            logger.info(f"  Time elapsed: {time.time() - start_time:.1f}s")

            # Read and validate
            try:
                with open(task_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Check initial status
                status_match = re.search(r'status:\s*["\']?(\w+)["\']?', content, re.IGNORECASE)
                if status_match:
                    status = status_match.group(1)
                    logger.info(f"  Initial status: {status}")
                    if status != 'IN_PROGRESS':
                        logger.warning(f"  ⚠ Expected IN_PROGRESS, got {status}")
                        self.test_results['issues'].append(f"Unexpected initial status: {status}")

            except Exception as e:
                logger.warning(f"Could not read task file: {e}")

            self.test_results['stages']['task_created'] = {
                'success': True,
                'timestamp': datetime.now(),
                'file': task_file,
                'elapsed_seconds': time.time() - start_time
            }
        else:
            logger.error(f"✗ Task file not created within {timeout}s")
            self.test_results['issues'].append(f"Task file not created within {timeout}s")
            self.test_results['stages']['task_created'] = {
                'success': False,
                'timestamp': datetime.now()
            }

        return task_file

    def wait_for_task_completion(self, task_file, timeout=300):
        """Wait for task to reach PROCESSED or FAILED status.

        Args:
            task_file: Path to task file
            timeout: Maximum seconds to wait

        Returns:
            True if task completed successfully (PROCESSED), False otherwise
        """
        logger.info("\n" + "=" * 80)
        logger.info("STAGE 3: Waiting for task completion")
        logger.info("=" * 80)

        start_time = time.time()
        last_status = None
        status_history = []

        while time.time() - start_time < timeout:
            try:
                with open(task_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Extract status
                status_match = re.search(r'status:\s*["\']?(\w+)["\']?', content, re.IGNORECASE)

                if status_match:
                    current_status = status_match.group(1)

                    if current_status != last_status:
                        logger.info(f"  Status changed: {last_status or 'None'} → {current_status}")
                        status_history.append({
                            'status': current_status,
                            'timestamp': datetime.now(),
                            'elapsed': time.time() - start_time
                        })
                        last_status = current_status

                    # Check for completion
                    if current_status in ['PROCESSED', 'FAILED']:
                        logger.info(f"✓ Task reached terminal status: {current_status}")

                        # Validate output if PROCESSED
                        if current_status == 'PROCESSED':
                            output_match = re.search(r'output:\s*["\']?\[\[([^\]]+)\]\]["\']?', content, re.IGNORECASE)
                            if output_match:
                                logger.info(f"  ✓ Output file: {output_match.group(1)}")
                            else:
                                logger.warning(f"  ⚠ No output file specified")

                        self.test_results['stages']['task_completion'] = {
                            'success': current_status == 'PROCESSED',
                            'timestamp': datetime.now(),
                            'final_status': current_status,
                            'status_history': status_history,
                            'total_seconds': time.time() - start_time
                        }

                        return current_status == 'PROCESSED'

            except Exception as e:
                logger.warning(f"Error reading task file: {e}")

            time.sleep(5)

        logger.error(f"✗ Task did not complete within {timeout}s")
        logger.error(f"  Last status: {last_status}")
        self.test_results['issues'].append(f"Task timeout after {timeout}s, status: {last_status}")
        self.test_results['stages']['task_completion'] = {
            'success': False,
            'timestamp': datetime.now(),
            'final_status': last_status,
            'status_history': status_history
        }

        return False

    def check_for_duplicates(self):
        """Check if any duplicate tasks were created."""
        logger.info("\n" + "=" * 80)
        logger.info("VALIDATION: Checking for duplicate tasks")
        logger.info("=" * 80)

        test_tasks = []
        pattern = r"^\d{4}-\d{2}-\d{2} EIC - .+\.md$"

        if os.path.exists(self.tasks_dir):
            for filename in os.listdir(self.tasks_dir):
                if not re.match(pattern, filename):
                    continue
                if 'Test Integration' not in filename:
                    continue

                filepath = os.path.join(self.tasks_dir, filename)
                file_mtime = os.path.getmtime(filepath)

                if file_mtime > self.test_results['start_time'].timestamp():
                    test_tasks.append(filename)

        if len(test_tasks) == 0:
            logger.warning("⚠ No test tasks found")
            return False
        elif len(test_tasks) == 1:
            logger.info(f"✓ Exactly one task created (no duplicates)")
            return True
        else:
            logger.error(f"✗ Multiple tasks created: {len(test_tasks)}")
            for task in test_tasks:
                logger.error(f"  - {task}")
            self.test_results['issues'].append(f"Duplicate tasks created: {test_tasks}")
            return False

    def cleanup(self):
        """Clean up test artifacts."""
        logger.info("\n" + "=" * 80)
        logger.info("CLEANUP: Removing test artifacts")
        logger.info("=" * 80)

        cleaned = 0
        failed = 0

        for filepath in reversed(self.created_files):
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
                    logger.info(f"✓ Deleted: {os.path.basename(filepath)}")
                    cleaned += 1
            except Exception as e:
                logger.error(f"✗ Failed to delete {filepath}: {e}")
                failed += 1

        logger.info(f"\nCleanup summary: {cleaned} deleted, {failed} failed")

        self.test_results['cleanup'] = {
            'files_deleted': cleaned,
            'files_failed': failed
        }

    def generate_report(self):
        """Generate test results report."""
        self.test_results['end_time'] = datetime.now()
        self.test_results['total_duration'] = (
            self.test_results['end_time'] - self.test_results['start_time']
        ).total_seconds()

        # Determine overall success
        self.test_results['success'] = (
            len(self.test_results['issues']) == 0 and
            all(stage.get('success', False) for stage in self.test_results['stages'].values())
        )

        report = f"""
{'=' * 80}
ORCHESTRATOR EIC INTEGRATION TEST RESULTS
{'=' * 80}

Test Start: {self.test_results['start_time'].strftime('%Y-%m-%d %H:%M:%S')}
Test End:   {self.test_results['end_time'].strftime('%Y-%m-%d %H:%M:%S')}
Duration:   {self.test_results['total_duration']:.1f}s

Overall Result: {'✓ PASSED' if self.test_results['success'] else '✗ FAILED'}

{'=' * 80}
STAGE RESULTS
{'=' * 80}
"""

        for stage_name, stage_data in self.test_results['stages'].items():
            status = '✓ PASSED' if stage_data.get('success') else '✗ FAILED'
            report += f"\n{stage_name.upper()}: {status}\n"

            if 'elapsed_seconds' in stage_data:
                report += f"  Time: {stage_data['elapsed_seconds']:.1f}s\n"

            if 'file' in stage_data:
                report += f"  File: {os.path.basename(stage_data['file'])}\n"

            if 'status_history' in stage_data:
                report += f"  Status transitions:\n"
                for status in stage_data['status_history']:
                    report += f"    - {status['status']} at {status['elapsed']:.1f}s\n"

        if self.test_results['issues']:
            report += f"\n{'=' * 80}\n"
            report += f"ISSUES FOUND ({len(self.test_results['issues'])})\n"
            report += f"{'=' * 80}\n"
            for i, issue in enumerate(self.test_results['issues'], 1):
                report += f"{i}. {issue}\n"

        report += f"\n{'=' * 80}\n"

        return report

    def run(self):
        """Run the complete integration test."""
        logger.info("\n\n")
        logger.info("*" * 80)
        logger.info("*" + " " * 78 + "*")
        logger.info("*" + " " * 15 + "ORCHESTRATOR EIC INTEGRATION TEST" + " " * 31 + "*")
        logger.info("*" + " " * 78 + "*")
        logger.info("*" * 80)
        logger.info("\n")

        try:
            # Stage 0: Start orchestrator
            print("\n[Stage 0] Starting orchestrator daemon...")
            if not self.start_orchestrator():
                print("❌ Failed to start orchestrator")
                return False
            print("✅ Orchestrator started\n")

            # Stage 1: Create test clipping
            print("[Stage 1] Creating test clipping file...")
            if not self.create_test_clipping():
                print("❌ Failed to create test clipping")
                return False
            print(f"✅ Test clipping created\n")

            # Stage 2: Wait for task file
            print("[Stage 2] Waiting for task file creation (timeout: 60s)...")
            task_file = self.wait_for_task_file(timeout=60)
            if not task_file:
                print("❌ Task file was not created")
                return False
            print(f"✅ Task file created: {os.path.basename(task_file)}\n")

            # Stage 3: Wait for completion
            print("[Stage 3] Waiting for task completion (timeout: 300s)...")
            success = self.wait_for_task_completion(task_file, timeout=300)
            if success:
                print("✅ Task completed successfully\n")
            else:
                print("❌ Task did not complete\n")

            # Validation: Check for duplicates
            print("[Validation] Checking for duplicate tasks...")
            no_duplicates = self.check_for_duplicates()
            if no_duplicates:
                print("✅ No duplicate tasks found\n")
            else:
                print("❌ Duplicate tasks detected\n")

            if not no_duplicates:
                self.test_results['success'] = False

            return success

        finally:
            # Stop daemon
            print("\n[Cleanup] Stopping orchestrator daemon...")
            self.stop_orchestrator()
            print("✅ Orchestrator stopped\n")

            # Generate report
            print("[Report] Generating test report...")
            report = self.generate_report()
            logger.info(report)
            print(report)

            # Save report
            test_dir = os.path.dirname(os.path.abspath(__file__))
            report_path = os.path.join(test_dir, 'Orchestrator_EIC_Test_Results.md')

            try:
                with open(report_path, 'w', encoding='utf-8') as f:
                    f.write(f"# Orchestrator EIC Integration Test Results\n\n")
                    f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                    f.write(report)

                print(f"✅ Test report saved to: {report_path}\n")

            except Exception as e:
                print(f"❌ Failed to save report: {e}\n")

            # Cleanup
            print("[Cleanup] Removing test artifacts...")
            self.cleanup()
            print()

            # Return final result
            return self.test_results.get('success', False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Integration test for Orchestrator EIC workflow'
    )
    parser.add_argument(
        '--use-existing-daemon',
        action='store_true',
        help='Use existing daemon instead of starting/stopping one'
    )
    args = parser.parse_args()

    try:
        test = OrchestratorEICIntegrationTest()
        test.use_existing_daemon = args.use_existing_daemon
        print(f"\n{'='*80}")
        print(f"Running Orchestrator EIC Integration Test")
        print(f"Workspace: {test.workspace_path}")
        print(f"{'='*80}\n")

        success = test.run()

        print(f"\n{'='*80}")
        if success:
            print("✅ TEST PASSED")
        else:
            print("❌ TEST FAILED")
        print(f"{'='*80}\n")

        sys.exit(0 if success else 1)

    except Exception as e:
        print(f"\n{'='*80}")
        print(f"❌ TEST ERROR: {e}")
        print(f"{'='*80}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
