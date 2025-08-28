"""Integration tests for Python execution tools."""

import asyncio
import json
import sys
import tempfile
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Add files to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestPythonExecution:
    """Test Python execution tools."""

    @pytest.fixture
    def server_script(self):
        """Get the server script path."""
        return (
            Path(__file__).parent.parent.parent / "scripts" / "run_filesys_fastmcp.py"
        )

    @pytest.fixture
    def venv_python(self):
        """Get the venv Python executable."""
        from base.backend.utils.environment_setup import EnvironmentSetup

        return EnvironmentSetup.get_module_venv_python(Path(__file__))

    async def _get_client_session(self, venv_python, server_script, temp_dir):
        """Helper to get client session."""
        server_params = StdioServerParameters(
            command=str(venv_python),
            args=["-u", str(server_script), "--root-dir", str(temp_dir)],
            env=None,
        )
        return stdio_client(server_params)

    @pytest.mark.asyncio
    async def test_python_run_simple_code(self, venv_python, server_script):
        """Test executing simple Python code."""
        with tempfile.TemporaryDirectory() as temp_dir:
            async with await self._get_client_session(
                venv_python, server_script, temp_dir
            ) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as client:
                    await client.initialize()

                    result = await client.call_tool(
                        "python_run",
                        arguments={"script": "print('Hello, World!')", "timeout": 5},
                    )

                    assert result.content[0].text is not None
                    # FastMCP returns JSON string of the tool result
                    print(f"RESPONSE: {result.content[0].text!r}")
                    response = json.loads(result.content[0].text)

                    # Check if it's a timeout error
                    if "error" in response and "timeout" in response:
                        raise AssertionError(f"Python execution timed out: {response}")
                    assert response["success"] is True
                    assert "Hello, World!" in response["stdout"]
                    assert response["returncode"] == 0

    @pytest.mark.asyncio
    async def test_python_run_with_error(self, venv_python, server_script):
        """Test executing Python code with error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            async with await self._get_client_session(
                venv_python, server_script, temp_dir
            ) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as client:
                    await client.initialize()

                    result = await client.call_tool(
                        "python_run",
                        arguments={
                            "script": "raise ValueError('Test error')",
                            "timeout": 5,
                        },
                    )

                    response = json.loads(result.content[0].text)
                    assert response["success"] is False
                    assert response["returncode"] != 0
                    assert "ValueError: Test error" in response["stderr"]

    @pytest.mark.asyncio
    async def test_python_run_with_timeout(self, venv_python, server_script):
        """Test Python execution timeout."""
        with tempfile.TemporaryDirectory() as temp_dir:
            async with await self._get_client_session(
                venv_python, server_script, temp_dir
            ) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as client:
                    await client.initialize()

                    result = await client.call_tool(
                        "python_run",
                        arguments={
                            "script": "import time; time.sleep(10)",
                            "timeout": 1,
                        },
                    )

                    response = json.loads(result.content[0].text)
                    assert "error" in response
                    assert "timeout" in response.get(
                        "error", ""
                    ).lower() or response.get("timeout", False)

    @pytest.mark.asyncio
    async def test_python_run_script_file(self, venv_python, server_script):
        """Test running a Python script file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create a script file
            script_file = temp_path / "test_script.py"
            script_content = """
import sys
print("Python version:", sys.version.split()[0])
print("Script executed successfully")
sys.exit(0)
"""
            script_file.write_text(script_content)

            async with await self._get_client_session(
                venv_python, server_script, temp_dir
            ) as (read_stream, write_stream), ClientSession(
                read_stream, write_stream
            ) as client:
                await client.initialize()

                # Run the script file
                result = await client.call_tool(
                    "python_run",
                    arguments={"script": str(script_file), "timeout": 5},
                )

                response = json.loads(result.content[0].text)
                assert response["success"] is True
                assert "Script executed successfully" in response["stdout"]
                assert response["returncode"] == 0

    @pytest.mark.asyncio
    async def test_python_run_with_args(self, venv_python, server_script):
        """Test running Python with arguments."""
        with tempfile.TemporaryDirectory() as temp_dir:
            async with await self._get_client_session(
                venv_python, server_script, temp_dir
            ) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as client:
                    await client.initialize()

                    script = """
import sys
print("Arguments:", sys.argv[1:])
"""
                    result = await client.call_tool(
                        "python_run",
                        arguments={
                            "script": script,
                            "args": ["arg1", "arg2", "arg3"],
                            "timeout": 5,
                        },
                    )

                    response = json.loads(result.content[0].text)
                    assert response["success"] is True
                    assert "['arg1', 'arg2', 'arg3']" in response["stdout"]

    @pytest.mark.asyncio
    async def test_python_run_with_cwd(self, venv_python, server_script):
        """Test running Python with custom working directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create subdirectory
            subdir = temp_path / "subdir"
            subdir.mkdir()

            # Create a file in subdir
            test_file = subdir / "test.txt"
            test_file.write_text("test content")

            async with await self._get_client_session(
                venv_python, server_script, temp_dir
            ) as (read_stream, write_stream), ClientSession(
                read_stream, write_stream
            ) as client:
                await client.initialize()

                # Run script that checks current directory
                script = """
import os
print("CWD:", os.getcwd())
print("Files:", os.listdir('.'))
"""
                result = await client.call_tool(
                    "python_run",
                    arguments={"script": script, "cwd": "subdir", "timeout": 5},
                )

                response = json.loads(result.content[0].text)
                assert response["success"] is True
                assert "test.txt" in response["stdout"]

    @pytest.mark.asyncio
    async def test_python_run_with_system_python(self, venv_python, server_script):
        """Test running with system Python."""
        with tempfile.TemporaryDirectory() as temp_dir:
            async with await self._get_client_session(
                venv_python, server_script, temp_dir
            ) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as client:
                    await client.initialize()

                    script = "import sys; print(sys.executable)"
                    result = await client.call_tool(
                        "python_run",
                        arguments={"script": script, "python": "system", "timeout": 5},
                    )

                    response = json.loads(result.content[0].text)
                    assert response["success"] is True
                    assert "python" in response["stdout"].lower()

    @pytest.mark.asyncio
    async def test_python_run_with_venv(self, venv_python, server_script):
        """Test running with venv Python."""
        with tempfile.TemporaryDirectory() as temp_dir:
            async with await self._get_client_session(
                venv_python, server_script, temp_dir
            ) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as client:
                    await client.initialize()

                    # This test assumes we have a .venv in the root dir
                    script = "import sys; print(sys.executable)"
                    result = await client.call_tool(
                        "python_run",
                        arguments={"script": script, "python": "venv", "timeout": 5},
                    )

                    response = json.loads(result.content[0].text)
                    assert response["success"] is True
                    # Should use venv or fall back to system
                    assert "python" in response["stdout"].lower()

    @pytest.mark.asyncio
    async def test_python_run_multiline_output(self, venv_python, server_script):
        """Test handling multiline output."""
        with tempfile.TemporaryDirectory() as temp_dir:
            async with await self._get_client_session(
                venv_python, server_script, temp_dir
            ) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as client:
                    await client.initialize()

                    script = """
for i in range(5):
    print(f"Line {i+1}")
print("Done")
"""
                    result = await client.call_tool(
                        "python_run", arguments={"script": script, "timeout": 5}
                    )

                    response = json.loads(result.content[0].text)
                    assert response["success"] is True
                    for i in range(1, 6):
                        assert f"Line {i}" in response["stdout"]
                    assert "Done" in response["stdout"]

    @pytest.mark.asyncio
    async def test_python_run_with_imports(self, venv_python, server_script):
        """Test running code with standard library imports."""
        with tempfile.TemporaryDirectory() as temp_dir:
            async with await self._get_client_session(
                venv_python, server_script, temp_dir
            ) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as client:
                    await client.initialize()

                    script = """
import json
import datetime
import os

data = {'timestamp': datetime.datetime.now().isoformat(), 'pid': os.getpid()}
print(json.dumps(data))
"""
                    result = await client.call_tool(
                        "python_run", arguments={"script": script, "timeout": 5}
                    )

                    response = json.loads(result.content[0].text)
                    assert response["success"] is True
                    assert "timestamp" in response["stdout"]
                    assert "pid" in response["stdout"]


class TestPythonErrorHandling:
    """Test error handling in Python tools."""

    @pytest.fixture
    def server_script(self):
        """Get the server script path."""
        return (
            Path(__file__).parent.parent.parent / "scripts" / "run_filesys_fastmcp.py"
        )

    @pytest.fixture
    def venv_python(self):
        """Get the venv Python executable."""
        from base.backend.utils.environment_setup import EnvironmentSetup

        return EnvironmentSetup.get_module_venv_python(Path(__file__))

    async def _get_client_session(self, venv_python, server_script, temp_dir):
        """Helper to get client session."""
        server_params = StdioServerParameters(
            command=str(venv_python),
            args=["-u", str(server_script), "--root-dir", str(temp_dir)],
            env=None,
        )
        return stdio_client(server_params)

    @pytest.mark.asyncio
    async def test_syntax_error(self, venv_python, server_script):
        """Test handling of syntax errors."""
        with tempfile.TemporaryDirectory() as temp_dir:
            async with await self._get_client_session(
                venv_python, server_script, temp_dir
            ) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as client:
                    await client.initialize()

                    result = await client.call_tool(
                        "python_run",
                        arguments={"script": "print('unclosed", "timeout": 5},
                    )

                    response = json.loads(result.content[0].text)
                    assert response["success"] is False
                    assert "SyntaxError" in response["stderr"]

    @pytest.mark.asyncio
    async def test_import_error(self, venv_python, server_script):
        """Test handling of import errors."""
        with tempfile.TemporaryDirectory() as temp_dir:
            async with await self._get_client_session(
                venv_python, server_script, temp_dir
            ) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as client:
                    await client.initialize()

                    result = await client.call_tool(
                        "python_run",
                        arguments={"script": "import nonexistent_module", "timeout": 5},
                    )

                    response = json.loads(result.content[0].text)
                    assert response["success"] is False
                    assert (
                        "ModuleNotFoundError" in response["stderr"]
                        or "ImportError" in response["stderr"]
                    )

    @pytest.mark.asyncio
    async def test_runtime_error(self, venv_python, server_script):
        """Test handling of runtime errors."""
        with tempfile.TemporaryDirectory() as temp_dir:
            async with await self._get_client_session(
                venv_python, server_script, temp_dir
            ) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as client:
                    await client.initialize()

                    script = """
def divide(a, b):
    return a / b

result = divide(10, 0)
print(result)
"""
                    result = await client.call_tool(
                        "python_run", arguments={"script": script, "timeout": 5}
                    )

                    response = json.loads(result.content[0].text)
                    assert response["success"] is False
                    assert "ZeroDivisionError" in response["stderr"]

    @pytest.mark.asyncio
    async def test_invalid_cwd(self, venv_python, server_script):
        """Test handling of invalid working directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            async with await self._get_client_session(
                venv_python, server_script, temp_dir
            ) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as client:
                    await client.initialize()

                    result = await client.call_tool(
                        "python_run",
                        arguments={
                            "script": "print('test')",
                            "cwd": "/nonexistent/path",
                            "timeout": 5,
                        },
                    )

                    response = json.loads(result.content[0].text)
                    assert "error" in response

    @pytest.mark.asyncio
    async def test_nonexistent_script_file(self, venv_python, server_script):
        """Test running nonexistent script file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            async with await self._get_client_session(
                venv_python, server_script, temp_dir
            ) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as client:
                    await client.initialize()

                    result = await client.call_tool(
                        "python_run",
                        arguments={"script": "/nonexistent/script.py", "timeout": 5},
                    )

                    response = json.loads(result.content[0].text)
                    # Should either fail to find the file or execute it as code
                    if response.get("success"):
                        # Treated as code, should fail
                        assert (
                            "SyntaxError" in response["stderr"]
                            or "NameError" in response["stderr"]
                        )
                    else:
                        # File not found or other error
                        assert response["returncode"] != 0


class TestPythonComplexScenarios:
    """Test complex Python execution scenarios."""

    @pytest.fixture
    def server_script(self):
        """Get the server script path."""
        return (
            Path(__file__).parent.parent.parent / "scripts" / "run_filesys_fastmcp.py"
        )

    @pytest.fixture
    def venv_python(self):
        """Get the venv Python executable."""
        from base.backend.utils.environment_setup import EnvironmentSetup

        return EnvironmentSetup.get_module_venv_python(Path(__file__))

    async def _get_client_session(self, venv_python, server_script, temp_dir):
        """Helper to get client session."""
        server_params = StdioServerParameters(
            command=str(venv_python),
            args=["-u", str(server_script), "--root-dir", str(temp_dir)],
            env=None,
        )
        return stdio_client(server_params)

    @pytest.mark.asyncio
    async def test_file_io_operations(self, venv_python, server_script):
        """Test Python script doing file I/O."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            async with await self._get_client_session(
                venv_python, server_script, temp_dir
            ) as (read_stream, write_stream), ClientSession(
                read_stream, write_stream
            ) as client:
                await client.initialize()

                script = """
with open('output.txt', 'w') as f:
    f.write('Test output')

with open('output.txt', 'r') as f:
    content = f.read()
    print(f"File content: {content}")
"""
                result = await client.call_tool(
                    "python_run", arguments={"script": script, "timeout": 5}
                )

                response = json.loads(result.content[0].text)
                assert response["success"] is True
                assert "File content: Test output" in response["stdout"]

                # Verify file was created
                assert (temp_path / "output.txt").exists()
                assert (temp_path / "output.txt").read_text() == "Test output"

    @pytest.mark.asyncio
    async def test_concurrent_executions(self, venv_python, server_script):
        """Test multiple concurrent Python executions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            async with await self._get_client_session(
                venv_python, server_script, temp_dir
            ) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as client:
                    await client.initialize()

                    scripts = [f"print('Result {i}')" for i in range(5)]

                    tasks = [
                        client.call_tool(
                            "python_run", arguments={"script": script, "timeout": 5}
                        )
                        for script in scripts
                    ]

                    results = await asyncio.gather(*tasks)

                    for i, result in enumerate(results):
                        response = json.loads(result.content[0].text)
                        assert response["success"] is True
                        assert f"Result {i}" in response["stdout"]

    @pytest.mark.asyncio
    async def test_large_output(self, venv_python, server_script):
        """Test handling of large output."""
        with tempfile.TemporaryDirectory() as temp_dir:
            async with await self._get_client_session(
                venv_python, server_script, temp_dir
            ) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as client:
                    await client.initialize()

                    script = """
for i in range(1000):
    print(f"Line {i}: " + "x" * 100)
"""
                    result = await client.call_tool(
                        "python_run", arguments={"script": script, "timeout": 10}
                    )

                    response = json.loads(result.content[0].text)
                    assert response["success"] is True
                    assert "Line 0:" in response["stdout"]
                    assert "Line 999:" in response["stdout"]

    @pytest.mark.asyncio
    async def test_mixed_stdout_stderr(self, venv_python, server_script):
        """Test handling mixed stdout and stderr."""
        with tempfile.TemporaryDirectory() as temp_dir:
            async with await self._get_client_session(
                venv_python, server_script, temp_dir
            ) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as client:
                    await client.initialize()

                    script = """
import sys
print("Normal output 1")
sys.stderr.write("Error output 1\\n")
print("Normal output 2")
sys.stderr.write("Error output 2\\n")
"""
                    result = await client.call_tool(
                        "python_run", arguments={"script": script, "timeout": 5}
                    )

                    response = json.loads(result.content[0].text)
                    assert response["success"] is True
                    assert "Normal output 1" in response["stdout"]
                    assert "Normal output 2" in response["stdout"]
                    assert "Error output 1" in response["stderr"]
                    assert "Error output 2" in response["stderr"]

    @pytest.mark.asyncio
    async def test_exit_codes(self, venv_python, server_script):
        """Test different exit codes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            async with await self._get_client_session(
                venv_python, server_script, temp_dir
            ) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as client:
                    await client.initialize()

                    # Test exit code 0
                    result = await client.call_tool(
                        "python_run",
                        arguments={"script": "import sys; sys.exit(0)", "timeout": 5},
                    )
                    response = json.loads(result.content[0].text)
                    assert response["success"] is True
                    assert response["returncode"] == 0

                    # Test exit code 1
                    result = await client.call_tool(
                        "python_run",
                        arguments={"script": "import sys; sys.exit(1)", "timeout": 5},
                    )
                    response = json.loads(result.content[0].text)
                    assert response["success"] is False
                    assert response["returncode"] == 1

                    # Test exit code 42
                    result = await client.call_tool(
                        "python_run",
                        arguments={"script": "import sys; sys.exit(42)", "timeout": 5},
                    )
                    response = json.loads(result.content[0].text)
                    assert response["success"] is False
                    assert response["returncode"] == 42
