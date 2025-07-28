# -*- coding: utf-8 -*-
"""
Local System Tools Module
Provides basic operating system related operations
Including file operations, path queries, time operations, etc.
"""

import os
import sys
import datetime
import shutil
import glob
import platform
from typing import  Dict, Any
from .base_tools import register_tool

def get_os_info():
    os_version=platform.platform()
    workspace_path=os.getcwd()
    powshell_path=None
    if sys.platform == "win32":
        ps_paths = [
            os.path.join(os.environ["SystemRoot"], "System32", "WindowsPowerShell", "v1.0", "powershell.exe"),
            os.path.join(os.environ["SystemRoot"], "SysWOW64", "WindowsPowerShell", "v1.0", "powershell.exe")
        ]
        for path in ps_paths:
            if os.path.exists(path):
                powshell_path = path
                break
        else: 
            powshell_path = "Unknown"
    return f"The user's OS version is {os_version}. The absolute path of the user's workspace is {workspace_path}. The user's shell is {powshell_path}."

# ==================== File Operation Tools ====================

@register_tool()
def create_file(file_path: str, content: str = "", encoding: str = "utf-8") -> Dict[str, Any]:
    """
    {
        "fn": "Create File",
        "args": {
            "file_path": "File Path",
            "content": "File Content, Empty by Default",
            "encoding": "File Encoding, UTF-8 by Default"
        }
    }
    """
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w', encoding=encoding) as f:
            f.write(content)
        
        return {
            "success": True,
            "message": f"File created successfully: {file_path}",
            "file_path": file_path,
            "size": len(content.encode(encoding))
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"File creation failed: {str(e)}",
            "error": str(e)
        }

@register_tool
def delete_file(file_path: str) -> Dict[str, Any]:
    """
    {
        "fn": "Delete File",
        "args": {
            "file_path": "File Path"
        }
    }
    """
    try:
        if not os.path.exists(file_path):
            return {
                "success": False,
                "message": f"File does not exist: {file_path}"
            }
        
        os.remove(file_path)
        return {
            "success": True,
            "message": f"File deleted successfully: {file_path}"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"File deletion failed: {str(e)}",
            "error": str(e)
        }

@register_tool
def read_file(file_path: str, encoding: str = "utf-8") -> Dict[str, Any]:
    """
    {
        "fn": "Read File Content",
        "args": {
            "file_path": "File Path",
            "encoding": "File Encoding, UTF-8 by Default"
        }
    }
    """
    try:
        if not os.path.exists(file_path):
            return {
                "success": False,
                "message": f"File does not exist: {file_path}"
            }
        
        with open(file_path, 'r', encoding=encoding) as f:
            content = f.read()
        
        return {
            "success": True,
            "message": f"File read successfully: {file_path}",
            "content": content,
            "size": len(content.encode(encoding)),
            "lines": len(content.splitlines())
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"File read failed: {str(e)}",
            "error": str(e)
        }

@register_tool
def write_file(file_path: str, content: str, mode: str = "w", encoding: str = "utf-8") -> Dict[str, Any]:
    """
    {
        "fn": "Write File Content",
        "args": {
            "file_path": "File Path",
            "content": "Content to Write",
            "mode": "Write Mode ('w': Overwrite, 'a': Append)",
            "encoding": "File Encoding, UTF-8 by Default"
        }
    }
    """
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, mode, encoding=encoding) as f:
            f.write(content)
        
        return {
            "success": True,
            "message": f"File written successfully: {file_path}",
            "mode": mode,
            "size": len(content.encode(encoding))
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"File write failed: {str(e)}",
            "error": str(e)
        }

@register_tool
def edit_file_line(file_path: str, line_number: int, new_content: str, encoding: str = "utf-8") -> Dict[str, Any]:
    """
    {
        "fn": "Edit File Specified Line",
        "args": {
            "file_path": "File Path",
            "line_number": "Line Number (Starting from 1)",
            "new_content": "New Line Content",
            "encoding": "File Encoding, UTF-8 by Default"
        }
    }
    """
    try:
        if not os.path.exists(file_path):
            return {
                "success": False,
                "message": f"File does not exist: {file_path}"
            }
        
        # Read all lines
        with open(file_path, 'r', encoding=encoding) as f:
            lines = f.readlines()
        
        # Check line number validity
        if line_number < 1 or line_number > len(lines):
            return {
                "success": False,
                "message": f"Invalid line number: {line_number}, file has {len(lines)} lines"
            }
        
        # Save original content
        old_content = lines[line_number - 1].rstrip('\n\r')
        
        # Modify specified line
        lines[line_number - 1] = new_content + '\n'
        
        # Write back to file
        with open(file_path, 'w', encoding=encoding) as f:
            f.writelines(lines)
        
        return {
            "success": True,
            "message": f"Line {line_number} edited successfully",
            "line_number": line_number,
            "old_content": old_content,
            "new_content": new_content
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Line editing failed: {str(e)}",
            "error": str(e)
        }

@register_tool
def edit_file_lines(file_path: str, start_line: int, end_line: int, new_content: str, encoding: str = "utf-8") -> Dict[str, Any]:
    """
    {
        "fn": "Edit File Multiple Lines",
        "args": {
            "file_path": "File Path",
            "start_line": "Start Line Number (Starting from 1)",
            "end_line": "End Line Number (Inclusive)",
            "new_content": "New Content (Multiple Lines Separated by \\n)",
            "encoding": "File Encoding, UTF-8 by Default"
        }
    }
    """
    try:
        if not os.path.exists(file_path):
            return {
                "success": False,
                "message": f"File does not exist: {file_path}"
            }
        
        # Read all lines
        with open(file_path, 'r', encoding=encoding) as f:
            lines = f.readlines()
        
        # Check line number validity
        if start_line < 1 or end_line > len(lines) or start_line > end_line:
            return {
                "success": False,
                "message": f"Invalid line range: {start_line}-{end_line}, file has {len(lines)} lines"
            }
        
        # Save original content
        old_lines = [line.rstrip('\n\r') for line in lines[start_line-1:end_line]]
        
        # Prepare new content
        new_lines = [line + '\n' for line in new_content.split('\n')]
        
        # Replace specified line range
        lines[start_line-1:end_line] = new_lines
        
        # Write back to file
        with open(file_path, 'w', encoding=encoding) as f:
            f.writelines(lines)
        
        return {
            "success": True,
            "message": f"Lines {start_line}-{end_line} edited successfully",
            "start_line": start_line,
            "end_line": end_line,
            "old_lines": old_lines,
            "new_lines_count": len(new_lines)
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Multi-line editing failed: {str(e)}",
            "error": str(e)
        }

# ==================== Directory Operation Tools ====================

@register_tool
def create_directory(dir_path: str) -> Dict[str, Any]:
    """
    {
        "fn": "Create Directory",
        "args": {
            "dir_path": "Directory Path"
        }
    }
    """
    try:
        os.makedirs(dir_path, exist_ok=True)
        return {
            "success": True,
            "message": f"Directory created successfully: {dir_path}",
            "path": dir_path
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Directory creation failed: {str(e)}",
            "error": str(e)
        }

@register_tool
def delete_directory(dir_path: str, force: bool = False) -> Dict[str, Any]:
    """
    {
        "fn": "Delete Directory",
        "args": {
            "dir_path": "Directory Path",
            "force": "Force Delete (Delete Non-Empty Directory)"
        }
    }
    """
    try:
        if not os.path.exists(dir_path):
            return {
                "success": False,
                "message": f"Directory does not exist: {dir_path}"
            }
        
        if force:
            shutil.rmtree(dir_path)
        else:
            os.rmdir(dir_path)
        
        return {
            "success": True,
            "message": f"Directory deleted successfully: {dir_path}"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Directory deletion failed: {str(e)}",
            "error": str(e)
        }

@register_tool
def list_directory(dir_path: str, show_hidden: bool = False, recursive: bool = False) -> Dict[str, Any]:
    """
    {
        "fn": "List Directory Contents",
        "args": {
            "dir_path": "Directory Path",
            "show_hidden": "Show Hidden Files",
            "recursive": "Recursively List Subdirectories"
        }
    }
    """
    try:
        if not os.path.exists(dir_path):
            return {
                "success": False,
                "message": f"Directory does not exist: {dir_path}"
            }
        
        if not os.path.isdir(dir_path):
            return {
                "success": False,
                "message": f"Path is not a directory: {dir_path}"
            }
        
        items = []
        
        if recursive:
            for root, dirs, files in os.walk(dir_path):
                # Process directories
                for d in dirs:
                    if show_hidden or not d.startswith('.'):
                        full_path = os.path.join(root, d)
                        rel_path = os.path.relpath(full_path, dir_path)
                        items.append({
                            "name": d,
                            "type": "directory",
                            "path": full_path,
                            "relative_path": rel_path
                        })
                
                # Process files
                for f in files:
                    if show_hidden or not f.startswith('.'):
                        full_path = os.path.join(root, f)
                        rel_path = os.path.relpath(full_path, dir_path)
                        stat = os.stat(full_path)
                        items.append({
                            "name": f,
                            "type": "file",
                            "path": full_path,
                            "relative_path": rel_path,
                            "size": stat.st_size,
                            "modified": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat()
                        })
        else:
            for item in os.listdir(dir_path):
                if show_hidden or not item.startswith('.'):
                    full_path = os.path.join(dir_path, item)
                    if os.path.isdir(full_path):
                        items.append({
                            "name": item,
                            "type": "directory",
                            "path": full_path
                        })
                    else:
                        stat = os.stat(full_path)
                        items.append({
                            "name": item,
                            "type": "file",
                            "path": full_path,
                            "size": stat.st_size,
                            "modified": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat()
                        })
        
        return {
            "success": True,
            "message": f"Directory list obtained successfully: {dir_path}",
            "path": dir_path,
            "items": items,
            "count": len(items)
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Directory listing failed: {str(e)}",
            "error": str(e)
        }

# ==================== Path Operation Tools ====================

@register_tool
def get_current_directory() -> Dict[str, Any]:
    """
    {
        "fn": "Get Current Working Directory",
        "args": {}
    }
    """
    try:
        current_dir = os.getcwd()
        return {
            "success": True,
            "message": "Current directory obtained successfully",
            "current_directory": current_dir,
            "absolute_path": os.path.abspath(current_dir)
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to get current directory: {str(e)}",
            "error": str(e)
        }

@register_tool
def change_directory(dir_path: str) -> Dict[str, Any]:
    """
    {
        "fn": "Change Current Working Directory",
        "args": {
            "dir_path": "Target Directory Path"
        }
    }
    """
    try:
        if not os.path.exists(dir_path):
            return {
                "success": False,
                "message": f"Directory does not exist: {dir_path}"
            }
        
        if not os.path.isdir(dir_path):
            return {
                "success": False,
                "message": f"Path is not a directory: {dir_path}"
            }
        
        old_dir = os.getcwd()
        os.chdir(dir_path)
        new_dir = os.getcwd()
        
        return {
            "success": True,
            "message": f"Directory changed successfully: {new_dir}",
            "old_directory": old_dir,
            "new_directory": new_dir
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Directory change failed: {str(e)}",
            "error": str(e)
        }

@register_tool
def get_absolute_path(path: str) -> Dict[str, Any]:
    """
    {
        "fn": "Get Absolute Path",
        "args": {
            "path": "Relative or Absolute Path"
        }
    }
    """
    try:
        abs_path = os.path.abspath(path)
        return {
            "success": True,
            "message": "Absolute path obtained successfully",
            "input_path": path,
            "absolute_path": abs_path,
            "exists": os.path.exists(abs_path),
            "is_file": os.path.isfile(abs_path),
            "is_directory": os.path.isdir(abs_path)
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to get absolute path: {str(e)}",
            "error": str(e)
        }

@register_tool
def find_files(pattern: str, search_path: str = ".", recursive: bool = True) -> Dict[str, Any]:
    """
    {
        "fn": "Find Files",
        "args": {
            "pattern": "File Name Pattern (Supports Wildcards)",
            "search_path": "Search Path, Current Directory by Default",
            "recursive": "Recursively Search Subdirectories"
        }
    }
    """
    try:
        if not os.path.exists(search_path):
            return {
                "success": False,
                "message": f"Search path does not exist: {search_path}"
            }
        
        found_files = []
        
        if recursive:
            # Recursive search
            search_pattern = os.path.join(search_path, "**", pattern)
            found_files = glob.glob(search_pattern, recursive=True)
        else:
            # Search only current directory
            search_pattern = os.path.join(search_path, pattern)
            found_files = glob.glob(search_pattern)
        
        # Filter out files (exclude directories)
        files_info = []
        for file_path in found_files:
            if os.path.isfile(file_path):
                stat = os.stat(file_path)
                files_info.append({
                    "path": file_path,
                    "name": os.path.basename(file_path),
                    "size": stat.st_size,
                    "modified": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
        
        return {
            "success": True,
            "message": f"File search completed, found {len(files_info)} files",
            "pattern": pattern,
            "search_path": search_path,
            "recursive": recursive,
            "files": files_info,
            "count": len(files_info)
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"File search failed: {str(e)}",
            "error": str(e)
        }

# ==================== Time Operation Tools ====================

@register_tool
def get_current_time(format_str: str = "%Y-%m-%d %H:%M:%S") -> Dict[str, Any]:
    """
    {
        "fn": "Get Current Time",
        "args": {
            "format_str": "Time Format String Default %Y-%m-%d %H:%M:%S Can Remain Unchanged"
        }
    }
    """
    try:
        now = datetime.datetime.now()
        return {
            "success": True,
            "message": "Current time obtained successfully",
            "current_time": now.strftime(format_str),
            "timestamp": now.timestamp(),
            "iso_format": now.isoformat(),
            "year": now.year,
            "month": now.month,
            "day": now.day,
            "hour": now.hour,
            "minute": now.minute,
            "second": now.second
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to get time: {str(e)}",
            "error": str(e)
        }

@register_tool
def get_file_times(file_path: str) -> Dict[str, Any]:
    """
    {
        "fn": "Get File Time Information",
        "args": {
            "file_path": "File Path"
        }
    }
    """
    try:
        if not os.path.exists(file_path):
            return {
                "success": False,
                "message": f"File does not exist: {file_path}"
            }
        
        stat = os.stat(file_path)
        
        return {
            "success": True,
            "message": f"File time information obtained successfully: {file_path}",
            "file_path": file_path,
            "created_time": datetime.datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified_time": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "accessed_time": datetime.datetime.fromtimestamp(stat.st_atime).isoformat(),
            "created_timestamp": stat.st_ctime,
            "modified_timestamp": stat.st_mtime,
            "accessed_timestamp": stat.st_atime
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to get file time information: {str(e)}",
            "error": str(e)
        }

# ==================== System Information Tools ====================

@register_tool
def get_system_info() -> Dict[str, Any]:
    """
    {
        "fn": "Get System Information",
        "args": {}
    }
    """
    try:
        return {
            "success": True,
            "message": "System information obtained successfully",
            "platform": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "current_directory": os.getcwd(),
            "home_directory": os.path.expanduser("~"),
            # "environment_variables": dict(os.environ) # Environment variable parameter acquisition prohibited may leak privacy information
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to get system information: {str(e)}",
            "error": str(e)
        }

@register_tool
def get_disk_usage(path: str = ".") -> Dict[str, Any]:
    """
    {
        "fn": "Get Disk Usage",
        "args": {
            "path": "Path to Check, Current Directory by Default"
        }
    }
    """
    try:
        if not os.path.exists(path):
            return {
                "success": False,
                "message": f"Path does not exist: {path}"
            }
        
        usage = shutil.disk_usage(path)
        
        def format_bytes(bytes_value):
            """Format bytes to readable format"""
            for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                if bytes_value < 1024.0:
                    return f"{bytes_value:.2f} {unit}"
                bytes_value /= 1024.0
            return f"{bytes_value:.2f} PB"
        
        return {
            "success": True,
            "message": f"Disk usage obtained successfully: {path}",
            "path": path,
            "total_bytes": usage.total,
            "used_bytes": usage.used,
            "free_bytes": usage.free,
            "total_formatted": format_bytes(usage.total),
            "used_formatted": format_bytes(usage.used),
            "free_formatted": format_bytes(usage.free),
            "usage_percentage": round((usage.used / usage.total) * 100, 2)
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to get disk usage: {str(e)}",
            "error": str(e)
        }

# ==================== File Copy and Move Tools ====================

@register_tool
def copy_file(src_path: str, dst_path: str) -> Dict[str, Any]:
    """
    {
        "fn": "Copy File",
        "args": {
            "src_path": "Source File Path",
            "dst_path": "Destination File Path"
        }
    }
    """
    try:
        if not os.path.exists(src_path):
            return {
                "success": False,
                "message": f"Source file does not exist: {src_path}"
            }
        
        if not os.path.isfile(src_path):
            return {
                "success": False,
                "message": f"Source path is not a file: {src_path}"
            }
        
        # Ensure destination directory exists
        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
        
        shutil.copy2(src_path, dst_path)
        
        return {
            "success": True,
            "message": f"File copied successfully: {src_path} -> {dst_path}",
            "source": src_path,
            "destination": dst_path
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"File copy failed: {str(e)}",
            "error": str(e)
        }

@register_tool
def move_file(src_path: str, dst_path: str) -> Dict[str, Any]:
    """
    {
        "fn": "Move File",
        "args": {
            "src_path": "Source File Path",
            "dst_path": "Destination File Path"
        }
    }
    """
    try:
        if not os.path.exists(src_path):
            return {
                "success": False,
                "message": f"Source file does not exist: {src_path}"
            }
        
        # Ensure destination directory exists
        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
        
        shutil.move(src_path, dst_path)
        
        return {
            "success": True,
            "message": f"File moved successfully: {src_path} -> {dst_path}",
            "source": src_path,
            "destination": dst_path
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"File move failed: {str(e)}",
            "error": str(e)
        }

# ==================== Test Functions ====================

def test_os_tools():
    """
    Test all operating system tool functions
    """
    print("=== Operating System Tools Test ===")
    
    # Test file operations
    print("\n1. Testing file operations")
    test_file = "test_file.txt"
    test_content = "This is a test file\nSecond line content"
    
    # Create file
    result = create_file(test_file, test_content)
    print(f"Create file: {result}")
    
    # Read file
    result = read_file(test_file)
    print(f"Read file: {result}")
    
    # Edit single line
    result = edit_file_line(test_file, 1, "Modified first line")
    print(f"Edit single line: {result}")
    
    # Test directory operations
    print("\n2. Testing directory operations")
    test_dir = "test_directory"
    
    # Create directory
    result = create_directory(test_dir)
    print(f"Create directory: {result}")
    
    # List directory
    result = list_directory(".")
    print(f"List directory: {result}")
    
    # Test time operations
    print("\n3. Testing time operations")
    result = get_current_time()
    print(f"Current time: {result}")
    
    # Test system information
    print("\n4. Testing system information")
    result = get_system_info()
    print(f"System information: {result}")
    
    # Clean up test files
    delete_file(test_file)
    delete_directory(test_dir)
    
    print("\n=== Test Completed ===")

if __name__ == "__main__":
    test_os_tools()
   