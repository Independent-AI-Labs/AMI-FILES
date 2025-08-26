#!/usr/bin/env python
"""Integration tests for Filesys MCP server in files module."""

import asyncio
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
import websockets

# Add files to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestFilesysMCPServerModes:
    """Test Filesys MCP server in both stdio and websocket modes."""

    @pytest.mark.asyncio
    async def test_filesys_stdio_mode(self):
        """Test Filesys MCP server in stdio mode."""
        # Create a temp directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Start the server
            server_script = (
                Path(__file__).parent.parent.parent / "scripts" / "run_filesys.py"
            )
            proc = subprocess.Popen(
                [sys.executable, str(server_script), "--root-dir", temp_dir],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            try:
                # Send initialize request
                init_request = {
                    "jsonrpc": "2.0",
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "test_client", "version": "1.0.0"},
                    },
                    "id": 1,
                }

                proc.stdin.write(json.dumps(init_request) + "\n")
                proc.stdin.flush()

                # Read response with timeout
                response_line = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None, proc.stdout.readline
                    ),
                    timeout=5.0,
                )
                response = json.loads(response_line)

                assert response["jsonrpc"] == "2.0"
                assert response["id"] == 1
                assert "result" in response
                assert response["result"]["protocolVersion"] == "2024-11-05"
                assert "serverInfo" in response["result"]
                assert response["result"]["serverInfo"]["name"] == "FilesysMCPServer"

                # Send list tools request
                tools_request = {
                    "jsonrpc": "2.0",
                    "method": "tools/list",
                    "params": {},
                    "id": 2,
                }

                proc.stdin.write(json.dumps(tools_request) + "\n")
                proc.stdin.flush()

                response_line = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None, proc.stdout.readline
                    ),
                    timeout=5.0,
                )
                response = json.loads(response_line)

                assert response["jsonrpc"] == "2.0"
                assert response["id"] == 2
                assert "result" in response
                assert "tools" in response["result"]

                # Verify some expected tools exist
                tool_names = [tool["name"] for tool in response["result"]["tools"]]
                assert "read_from_file" in tool_names
                assert "write_to_file" in tool_names
                assert "list_dir" in tool_names
                assert "create_dirs" in tool_names
                assert "delete_paths" in tool_names

            finally:
                proc.terminate()
                proc.wait(timeout=5)

    @pytest.mark.asyncio
    async def test_filesys_websocket_mode(self):
        """Test Filesys MCP server in websocket mode."""
        # Create a temp directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Start the server in websocket mode
            server_script = (
                Path(__file__).parent.parent.parent / "scripts" / "run_filesys.py"
            )
            proc = subprocess.Popen(
                [
                    sys.executable,
                    str(server_script),
                    "--root-dir",
                    temp_dir,
                    "--transport",
                    "websocket",
                    "--port",
                    "9004",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            # Give server time to start
            await asyncio.sleep(2)

            try:
                # Connect to websocket
                async with websockets.connect("ws://localhost:9004") as websocket:
                    # Send initialize request
                    init_request = {
                        "jsonrpc": "2.0",
                        "method": "initialize",
                        "params": {
                            "protocolVersion": "2024-11-05",
                            "capabilities": {},
                            "clientInfo": {"name": "test_client", "version": "1.0.0"},
                        },
                        "id": 1,
                    }

                    await websocket.send(json.dumps(init_request))
                    response = json.loads(await websocket.recv())

                    assert response["jsonrpc"] == "2.0"
                    assert response["id"] == 1
                    assert "result" in response
                    assert response["result"]["protocolVersion"] == "2024-11-05"
                    assert "serverInfo" in response["result"]
                    assert (
                        response["result"]["serverInfo"]["name"] == "FilesysMCPServer"
                    )

                    # Send list tools request
                    tools_request = {
                        "jsonrpc": "2.0",
                        "method": "tools/list",
                        "params": {},
                        "id": 2,
                    }

                    await websocket.send(json.dumps(tools_request))
                    response = json.loads(await websocket.recv())

                    assert response["jsonrpc"] == "2.0"
                    assert response["id"] == 2
                    assert "result" in response
                    assert "tools" in response["result"]

                    # Verify some expected tools exist
                    tool_names = [tool["name"] for tool in response["result"]["tools"]]
                    assert "read_from_file" in tool_names
                    assert "write_to_file" in tool_names
                    assert "list_dir" in tool_names
                    assert "create_dirs" in tool_names
                    assert "delete_paths" in tool_names

            finally:
                proc.terminate()
                proc.wait(timeout=5)

    @pytest.mark.asyncio
    async def test_filesys_file_operations(self):
        """Test Filesys MCP server file operations."""
        # Create a temp directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Start the server
            server_script = (
                Path(__file__).parent.parent.parent / "scripts" / "run_filesys.py"
            )
            proc = subprocess.Popen(
                [sys.executable, str(server_script), "--root-dir", temp_dir],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            try:
                # Send initialize request
                init_request = {
                    "jsonrpc": "2.0",
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "test_client", "version": "1.0.0"},
                    },
                    "id": 1,
                }

                proc.stdin.write(json.dumps(init_request) + "\n")
                proc.stdin.flush()

                # Read response
                response_line = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None, proc.stdout.readline
                    ),
                    timeout=5.0,
                )
                response = json.loads(response_line)
                assert response["id"] == 1
                assert "result" in response

                # Test write_to_file tool
                write_request = {
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "write_to_file",
                        "arguments": {
                            "path": "test.txt",
                            "content": "Hello from MCP test!",
                        },
                    },
                    "id": 2,
                }

                proc.stdin.write(json.dumps(write_request) + "\n")
                proc.stdin.flush()

                response_line = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None, proc.stdout.readline
                    ),
                    timeout=5.0,
                )
                response = json.loads(response_line)
                assert response["id"] == 2
                assert "result" in response

                # Test read_from_file tool
                read_request = {
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "read_from_file",
                        "arguments": {"path": "test.txt"},
                    },
                    "id": 3,
                }

                proc.stdin.write(json.dumps(read_request) + "\n")
                proc.stdin.flush()

                response_line = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None, proc.stdout.readline
                    ),
                    timeout=5.0,
                )
                response = json.loads(response_line)
                assert response["id"] == 3
                assert "result" in response

                # Verify file content
                content = response["result"]["content"]
                assert "Hello from MCP test!" in str(content)

                # Test list_dir tool
                list_request = {
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {"name": "list_dir", "arguments": {"path": "."}},
                    "id": 4,
                }

                proc.stdin.write(json.dumps(list_request) + "\n")
                proc.stdin.flush()

                response_line = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None, proc.stdout.readline
                    ),
                    timeout=5.0,
                )
                response = json.loads(response_line)
                assert response["id"] == 4
                assert "result" in response

                # Verify test.txt is in the listing
                assert "test.txt" in str(response["result"])

            finally:
                proc.terminate()
                proc.wait(timeout=5)

    @pytest.mark.asyncio
    async def test_filesys_directory_operations(self):
        """Test Filesys MCP server directory operations."""
        # Create a temp directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Start the server
            server_script = (
                Path(__file__).parent.parent.parent / "scripts" / "run_filesys.py"
            )
            proc = subprocess.Popen(
                [sys.executable, str(server_script), "--root-dir", temp_dir],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            try:
                # Send initialize request
                init_request = {
                    "jsonrpc": "2.0",
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "test_client", "version": "1.0.0"},
                    },
                    "id": 1,
                }

                proc.stdin.write(json.dumps(init_request) + "\n")
                proc.stdin.flush()

                # Read response
                response_line = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None, proc.stdout.readline
                    ),
                    timeout=5.0,
                )
                response = json.loads(response_line)
                assert response["id"] == 1
                assert "result" in response

                # Test create_dirs tool
                mkdir_request = {
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "create_dirs",
                        "arguments": {"path": "test_dir"},
                    },
                    "id": 2,
                }

                proc.stdin.write(json.dumps(mkdir_request) + "\n")
                proc.stdin.flush()

                response_line = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None, proc.stdout.readline
                    ),
                    timeout=5.0,
                )
                response = json.loads(response_line)
                assert response["id"] == 2
                assert "result" in response

                # Write a file in the directory
                write_request = {
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "write_to_file",
                        "arguments": {
                            "path": "test_dir/nested_file.txt",
                            "content": "Nested file content",
                        },
                    },
                    "id": 3,
                }

                proc.stdin.write(json.dumps(write_request) + "\n")
                proc.stdin.flush()

                response_line = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None, proc.stdout.readline
                    ),
                    timeout=5.0,
                )
                response = json.loads(response_line)
                assert response["id"] == 3
                assert "result" in response

                # List the directory contents
                list_request = {
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "list_dir",
                        "arguments": {"path": "test_dir"},
                    },
                    "id": 4,
                }

                proc.stdin.write(json.dumps(list_request) + "\n")
                proc.stdin.flush()

                response_line = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None, proc.stdout.readline
                    ),
                    timeout=5.0,
                )
                response = json.loads(response_line)
                assert response["id"] == 4
                assert "result" in response
                assert "nested_file.txt" in str(response["result"])

            finally:
                proc.terminate()
                proc.wait(timeout=5)
