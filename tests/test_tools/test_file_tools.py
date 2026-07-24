"""rapier-ai — tests for file tools."""

import pytest
from pathlib import Path
from rapier.tools.read_file import ReadFileTool
from rapier.tools.write_file import WriteFileTool
from rapier.tools.edit_file import EditFileTool


@pytest.fixture
def tmp_file(tmp_path):
    """Create a temporary test file."""
    file = tmp_path / "test.py"
    file.write_text("def hello():\n    return 'world'\n")
    return file


@pytest.mark.asyncio
async def test_read_file(tmp_file):
    tool = ReadFileTool()
    result = await tool.execute({"path": str(tmp_file)})
    assert "def hello():" in result
    assert "return 'world'" in result


@pytest.mark.asyncio
async def test_read_file_not_found():
    tool = ReadFileTool()
    result = await tool.execute({"path": "/nonexistent/file.py"})
    assert "Error" in result
    assert "not found" in result.lower()


@pytest.mark.asyncio
async def test_write_file(tmp_path):
    tool = WriteFileTool()
    path = tmp_path / "new.py"
    result = await tool.execute({"path": str(path), "content": "print('hello')"})
    assert "OK" in result
    assert path.read_text() == "print('hello')"


@pytest.mark.asyncio
async def test_edit_file(tmp_file):
    tool = EditFileTool()
    result = await tool.execute(
        {
            "path": str(tmp_file),
            "old_string": "return 'world'",
            "new_string": "return 'rapier'",
        }
    )
    assert "OK" in result
    assert "rapier" in tmp_file.read_text()


@pytest.mark.asyncio
async def test_edit_file_not_found():
    tool = EditFileTool()
    result = await tool.execute(
        {
            "path": "/nonexistent/file.py",
            "old_string": "a",
            "new_string": "b",
        }
    )
    assert "Error" in result
