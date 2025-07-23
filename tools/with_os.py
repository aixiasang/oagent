# -*- coding: utf-8 -*-
"""
本地系统工具模块
提供与操作系统相关的基本操作功能
包括文件操作、路径查询、时间操作等
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

# ==================== 文件操作工具 ====================

@register_tool()
def create_file(file_path: str, content: str = "", encoding: str = "utf-8") -> Dict[str, Any]:
    """
    {
        "fn": "创建文件",
        "args": {
            "file_path": "文件路径",
            "content": "文件内容，默认为空",
            "encoding": "文件编码，默认utf-8"
        }
    }
    """
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w', encoding=encoding) as f:
            f.write(content)
        
        return {
            "success": True,
            "message": f"文件创建成功: {file_path}",
            "file_path": file_path,
            "size": len(content.encode(encoding))
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"文件创建失败: {str(e)}",
            "error": str(e)
        }

@register_tool
def delete_file(file_path: str) -> Dict[str, Any]:
    """
    {
        "fn": "删除文件",
        "args": {
            "file_path": "文件路径"
        }
    }
    """
    try:
        if not os.path.exists(file_path):
            return {
                "success": False,
                "message": f"文件不存在: {file_path}"
            }
        
        os.remove(file_path)
        return {
            "success": True,
            "message": f"文件删除成功: {file_path}"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"文件删除失败: {str(e)}",
            "error": str(e)
        }

@register_tool
def read_file(file_path: str, encoding: str = "utf-8") -> Dict[str, Any]:
    """
    {
        "fn": "读取文件内容",
        "args": {
            "file_path": "文件路径",
            "encoding": "文件编码，默认utf-8"
        }
    }
    """
    try:
        if not os.path.exists(file_path):
            return {
                "success": False,
                "message": f"文件不存在: {file_path}"
            }
        
        with open(file_path, 'r', encoding=encoding) as f:
            content = f.read()
        
        return {
            "success": True,
            "message": f"文件读取成功: {file_path}",
            "content": content,
            "size": len(content.encode(encoding)),
            "lines": len(content.splitlines())
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"文件读取失败: {str(e)}",
            "error": str(e)
        }

@register_tool
def write_file(file_path: str, content: str, mode: str = "w", encoding: str = "utf-8") -> Dict[str, Any]:
    """
    {
        "fn": "写入文件内容",
        "args": {
            "file_path": "文件路径",
            "content": "要写入的内容",
            "mode": "写入模式 ('w': 覆盖, 'a': 追加)",
            "encoding": "文件编码，默认utf-8"
        }
    }
    """
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, mode, encoding=encoding) as f:
            f.write(content)
        
        return {
            "success": True,
            "message": f"文件写入成功: {file_path}",
            "mode": mode,
            "size": len(content.encode(encoding))
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"文件写入失败: {str(e)}",
            "error": str(e)
        }

@register_tool
def edit_file_line(file_path: str, line_number: int, new_content: str, encoding: str = "utf-8") -> Dict[str, Any]:
    """
    {
        "fn": "编辑文件指定行",
        "args": {
            "file_path": "文件路径",
            "line_number": "行号（从1开始）",
            "new_content": "新的行内容",
            "encoding": "文件编码，默认utf-8"
        }
    }
    """
    try:
        if not os.path.exists(file_path):
            return {
                "success": False,
                "message": f"文件不存在: {file_path}"
            }
        
        # 读取所有行
        with open(file_path, 'r', encoding=encoding) as f:
            lines = f.readlines()
        
        # 检查行号有效性
        if line_number < 1 or line_number > len(lines):
            return {
                "success": False,
                "message": f"行号无效: {line_number}，文件共有 {len(lines)} 行"
            }
        
        # 保存原内容
        old_content = lines[line_number - 1].rstrip('\n\r')
        
        # 修改指定行
        lines[line_number - 1] = new_content + '\n'
        
        # 写回文件
        with open(file_path, 'w', encoding=encoding) as f:
            f.writelines(lines)
        
        return {
            "success": True,
            "message": f"第 {line_number} 行编辑成功",
            "line_number": line_number,
            "old_content": old_content,
            "new_content": new_content
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"行编辑失败: {str(e)}",
            "error": str(e)
        }

@register_tool
def edit_file_lines(file_path: str, start_line: int, end_line: int, new_content: str, encoding: str = "utf-8") -> Dict[str, Any]:
    """
    {
        "fn": "编辑文件多行内容",
        "args": {
            "file_path": "文件路径",
            "start_line": "起始行号（从1开始）",
            "end_line": "结束行号（包含）",
            "new_content": "新的内容（多行用\\n分隔）",
            "encoding": "文件编码，默认utf-8"
        }
    }
    """
    try:
        if not os.path.exists(file_path):
            return {
                "success": False,
                "message": f"文件不存在: {file_path}"
            }
        
        # 读取所有行
        with open(file_path, 'r', encoding=encoding) as f:
            lines = f.readlines()
        
        # 检查行号有效性
        if start_line < 1 or end_line > len(lines) or start_line > end_line:
            return {
                "success": False,
                "message": f"行号范围无效: {start_line}-{end_line}，文件共有 {len(lines)} 行"
            }
        
        # 保存原内容
        old_lines = [line.rstrip('\n\r') for line in lines[start_line-1:end_line]]
        
        # 准备新内容
        new_lines = [line + '\n' for line in new_content.split('\n')]
        
        # 替换指定行范围
        lines[start_line-1:end_line] = new_lines
        
        # 写回文件
        with open(file_path, 'w', encoding=encoding) as f:
            f.writelines(lines)
        
        return {
            "success": True,
            "message": f"第 {start_line}-{end_line} 行编辑成功",
            "start_line": start_line,
            "end_line": end_line,
            "old_lines": old_lines,
            "new_lines_count": len(new_lines)
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"多行编辑失败: {str(e)}",
            "error": str(e)
        }

# ==================== 目录操作工具 ====================

@register_tool
def create_directory(dir_path: str) -> Dict[str, Any]:
    """
    {
        "fn": "创建目录",
        "args": {
            "dir_path": "目录路径"
        }
    }
    """
    try:
        os.makedirs(dir_path, exist_ok=True)
        return {
            "success": True,
            "message": f"目录创建成功: {dir_path}",
            "path": dir_path
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"目录创建失败: {str(e)}",
            "error": str(e)
        }

@register_tool
def delete_directory(dir_path: str, force: bool = False) -> Dict[str, Any]:
    """
    {
        "fn": "删除目录",
        "args": {
            "dir_path": "目录路径",
            "force": "是否强制删除（删除非空目录）"
        }
    }
    """
    try:
        if not os.path.exists(dir_path):
            return {
                "success": False,
                "message": f"目录不存在: {dir_path}"
            }
        
        if force:
            shutil.rmtree(dir_path)
        else:
            os.rmdir(dir_path)
        
        return {
            "success": True,
            "message": f"目录删除成功: {dir_path}"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"目录删除失败: {str(e)}",
            "error": str(e)
        }

@register_tool
def list_directory(dir_path: str, show_hidden: bool = False, recursive: bool = False) -> Dict[str, Any]:
    """
    {
        "fn": "列出目录内容",
        "args": {
            "dir_path": "目录路径",
            "show_hidden": "是否显示隐藏文件",
            "recursive": "是否递归列出子目录"
        }
    }
    """
    try:
        if not os.path.exists(dir_path):
            return {
                "success": False,
                "message": f"目录不存在: {dir_path}"
            }
        
        if not os.path.isdir(dir_path):
            return {
                "success": False,
                "message": f"路径不是目录: {dir_path}"
            }
        
        items = []
        
        if recursive:
            for root, dirs, files in os.walk(dir_path):
                # 处理目录
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
                
                # 处理文件
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
            "message": f"目录列表获取成功: {dir_path}",
            "path": dir_path,
            "items": items,
            "count": len(items)
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"目录列表获取失败: {str(e)}",
            "error": str(e)
        }

# ==================== 路径操作工具 ====================

@register_tool
def get_current_directory() -> Dict[str, Any]:
    """
    {
        "fn": "获取当前工作目录",
        "args": {}
    }
    """
    try:
        current_dir = os.getcwd()
        return {
            "success": True,
            "message": "当前目录获取成功",
            "current_directory": current_dir,
            "absolute_path": os.path.abspath(current_dir)
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"当前目录获取失败: {str(e)}",
            "error": str(e)
        }

@register_tool
def change_directory(dir_path: str) -> Dict[str, Any]:
    """
    {
        "fn": "改变当前工作目录",
        "args": {
            "dir_path": "目标目录路径"
        }
    }
    """
    try:
        if not os.path.exists(dir_path):
            return {
                "success": False,
                "message": f"目录不存在: {dir_path}"
            }
        
        if not os.path.isdir(dir_path):
            return {
                "success": False,
                "message": f"路径不是目录: {dir_path}"
            }
        
        old_dir = os.getcwd()
        os.chdir(dir_path)
        new_dir = os.getcwd()
        
        return {
            "success": True,
            "message": f"目录切换成功: {new_dir}",
            "old_directory": old_dir,
            "new_directory": new_dir
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"目录切换失败: {str(e)}",
            "error": str(e)
        }

@register_tool
def get_absolute_path(path: str) -> Dict[str, Any]:
    """
    {
        "fn": "获取绝对路径",
        "args": {
            "path": "相对或绝对路径"
        }
    }
    """
    try:
        abs_path = os.path.abspath(path)
        return {
            "success": True,
            "message": "绝对路径获取成功",
            "input_path": path,
            "absolute_path": abs_path,
            "exists": os.path.exists(abs_path),
            "is_file": os.path.isfile(abs_path),
            "is_directory": os.path.isdir(abs_path)
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"绝对路径获取失败: {str(e)}",
            "error": str(e)
        }

@register_tool
def find_files(pattern: str, search_path: str = ".", recursive: bool = True) -> Dict[str, Any]:
    """
    {
        "fn": "查找文件",
        "args": {
            "pattern": "文件名模式（支持通配符）",
            "search_path": "搜索路径，默认当前目录",
            "recursive": "是否递归搜索子目录"
        }
    }
    """
    try:
        if not os.path.exists(search_path):
            return {
                "success": False,
                "message": f"搜索路径不存在: {search_path}"
            }
        
        found_files = []
        
        if recursive:
            # 递归搜索
            search_pattern = os.path.join(search_path, "**", pattern)
            found_files = glob.glob(search_pattern, recursive=True)
        else:
            # 只搜索当前目录
            search_pattern = os.path.join(search_path, pattern)
            found_files = glob.glob(search_pattern)
        
        # 过滤出文件（排除目录）
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
            "message": f"文件搜索完成，找到 {len(files_info)} 个文件",
            "pattern": pattern,
            "search_path": search_path,
            "recursive": recursive,
            "files": files_info,
            "count": len(files_info)
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"文件搜索失败: {str(e)}",
            "error": str(e)
        }

# ==================== 时间操作工具 ====================

@register_tool
def get_current_time(format_str: str = "%Y-%m-%d %H:%M:%S") -> Dict[str, Any]:
    """
    {
        "fn": "获取当前时间",
        "args": {
            "format_str": "时间格式字符串 默认%Y-%m-%d %H:%M:%S 可以不做修改"
        }
    }
    """
    try:
        now = datetime.datetime.now()
        return {
            "success": True,
            "message": "当前时间获取成功",
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
            "message": f"时间获取失败: {str(e)}",
            "error": str(e)
        }

@register_tool
def get_file_times(file_path: str) -> Dict[str, Any]:
    """
    {
        "fn": "获取文件时间信息",
        "args": {
            "file_path": "文件路径"
        }
    }
    """
    try:
        if not os.path.exists(file_path):
            return {
                "success": False,
                "message": f"文件不存在: {file_path}"
            }
        
        stat = os.stat(file_path)
        
        return {
            "success": True,
            "message": f"文件时间信息获取成功: {file_path}",
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
            "message": f"文件时间信息获取失败: {str(e)}",
            "error": str(e)
        }

# ==================== 系统信息工具 ====================

@register_tool
def get_system_info() -> Dict[str, Any]:
    """
    {
        "fn": "获取系统信息",
        "args": {}
    }
    """
    try:
        return {
            "success": True,
            "message": "系统信息获取成功",
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
            # "environment_variables": dict(os.environ) # 环境变量参数获取 禁止获取 可能会泄露隐私信息
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"系统信息获取失败: {str(e)}",
            "error": str(e)
        }

@register_tool
def get_disk_usage(path: str = ".") -> Dict[str, Any]:
    """
    {
        "fn": "获取磁盘使用情况",
        "args": {
            "path": "要检查的路径，默认当前目录"
        }
    }
    """
    try:
        if not os.path.exists(path):
            return {
                "success": False,
                "message": f"路径不存在: {path}"
            }
        
        usage = shutil.disk_usage(path)
        
        def format_bytes(bytes_value):
            """格式化字节数为可读格式"""
            for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                if bytes_value < 1024.0:
                    return f"{bytes_value:.2f} {unit}"
                bytes_value /= 1024.0
            return f"{bytes_value:.2f} PB"
        
        return {
            "success": True,
            "message": f"磁盘使用情况获取成功: {path}",
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
            "message": f"磁盘使用情况获取失败: {str(e)}",
            "error": str(e)
        }

# ==================== 文件复制移动工具 ====================

@register_tool
def copy_file(src_path: str, dst_path: str) -> Dict[str, Any]:
    """
    {
        "fn": "复制文件",
        "args": {
            "src_path": "源文件路径",
            "dst_path": "目标文件路径"
        }
    }
    """
    try:
        if not os.path.exists(src_path):
            return {
                "success": False,
                "message": f"源文件不存在: {src_path}"
            }
        
        if not os.path.isfile(src_path):
            return {
                "success": False,
                "message": f"源路径不是文件: {src_path}"
            }
        
        # 确保目标目录存在
        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
        
        shutil.copy2(src_path, dst_path)
        
        return {
            "success": True,
            "message": f"文件复制成功: {src_path} -> {dst_path}",
            "source": src_path,
            "destination": dst_path
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"文件复制失败: {str(e)}",
            "error": str(e)
        }

@register_tool
def move_file(src_path: str, dst_path: str) -> Dict[str, Any]:
    """
    {
        "fn": "移动文件",
        "args": {
            "src_path": "源文件路径",
            "dst_path": "目标文件路径"
        }
    }
    """
    try:
        if not os.path.exists(src_path):
            return {
                "success": False,
                "message": f"源文件不存在: {src_path}"
            }
        
        # 确保目标目录存在
        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
        
        shutil.move(src_path, dst_path)
        
        return {
            "success": True,
            "message": f"文件移动成功: {src_path} -> {dst_path}",
            "source": src_path,
            "destination": dst_path
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"文件移动失败: {str(e)}",
            "error": str(e)
        }

# ==================== 测试函数 ====================

def test_os_tools():
    """
    测试所有操作系统工具函数
    """
    print("=== 操作系统工具测试 ===")
    
    # 测试文件操作
    print("\n1. 测试文件操作")
    test_file = "test_file.txt"
    test_content = "这是一个测试文件\n第二行内容"
    
    # 创建文件
    result = create_file(test_file, test_content)
    print(f"创建文件: {result}")
    
    # 读取文件
    result = read_file(test_file)
    print(f"读取文件: {result}")
    
    # 编辑单行
    result = edit_file_line(test_file, 1, "修改后的第一行")
    print(f"编辑单行: {result}")
    
    # 测试目录操作
    print("\n2. 测试目录操作")
    test_dir = "test_directory"
    
    # 创建目录
    result = create_directory(test_dir)
    print(f"创建目录: {result}")
    
    # 列出目录
    result = list_directory(".")
    print(f"列出目录: {result}")
    
    # 测试时间操作
    print("\n3. 测试时间操作")
    result = get_current_time()
    print(f"当前时间: {result}")
    
    # 测试系统信息
    print("\n4. 测试系统信息")
    result = get_system_info()
    print(f"系统信息: {result}")
    
    # 清理测试文件
    delete_file(test_file)
    delete_directory(test_dir)
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    test_os_tools()
   