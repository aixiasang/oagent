#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
命令行执行工具模块
提供命令行执行功能 可能支持执行不安全指令
支持同步和异步执行、超时控制、输出捕获等
"""
import subprocess
import os
import psutil
import sys
import time
from typing import Dict, Any, List, Union, Optional
from .register import register_tool

# 全局字典存储后台进程
_background_processes = {}

@register_tool
def cmd_run(cmd: Union[str, List[str]], 
           timeout: int = 60, 
           cwd: Optional[str] = None,
           env: Optional[Dict[str, str]] = None,
           shell: bool = False) -> Dict[str, Any]:
    """
    {
        "func": "执行命令",
        "params": {
            "cmd": "命令字符串或参数列表(统一转换为list)",
            "timeout": "超时时间(秒)",
            "cwd": "工作目录",
            "env": "环境变量字典",
            "shell": "是否使用shell执行"
        }
    }
    """
    p = None
    try:
        # 统一转换为list格式并处理Windows命令
        if isinstance(cmd, str):
            if sys.platform == 'win32':
                cmd_args = ['cmd', '/c', cmd]
                use_shell = True
            else:
                cmd_args = ['sh', '-c', cmd]
                use_shell = True
        else:
            cmd_args = list(cmd)  # 确保是list格式
            # 对于Windows系统的列表命令，需要通过cmd执行
            if sys.platform == 'win32':
                # 将列表命令转换为字符串，通过cmd执行
                cmd_str = ' '.join(f'"{arg}"' if ' ' in str(arg) else str(arg) for arg in cmd_args)
                cmd_args = ['cmd', '/c', cmd_str]
                use_shell = True
            else:
                use_shell = shell
            
        p = subprocess.Popen(
            cmd_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace',
            cwd=cwd,
            env=env,
            shell=use_shell if sys.platform == 'win32' else shell
        )
        out, err = p.communicate(timeout=timeout)
        code = p.returncode
    except subprocess.TimeoutExpired:
        if p and psutil.pid_exists(p.pid):
            try:
                parent = psutil.Process(p.pid)
                for child in parent.children(recursive=True):
                    child.kill()
                parent.kill()
            except psutil.NoSuchProcess:
                pass 
        out = ""
        err = f"Command '{cmd}' timed out after {timeout} seconds."
        code = -1
    except Exception as e:
        out = ""
        err = str(e)
        code = -1

    return {'code': code, 'out': out, 'err': err}


@register_tool
def cmd_run_async(cmd: Union[str, List[str]], 
                 process_id: str,
                 cwd: Optional[str] = None,
                 env: Optional[Dict[str, str]] = None,
                 new_shell: bool = True) -> Dict[str, Any]:
    """
    {
        "func": "异步后台执行命令",
        "params": {
            "cmd": "命令字符串或参数列表",
            "process_id": "进程标识符",
            "cwd": "工作目录",
            "env": "环境变量字典",
            "new_shell": "是否开启新shell窗口"
        }
    }
    """
    try:
        # 统一转换为list格式
        if isinstance(cmd, str):
            if sys.platform == 'win32':
                if new_shell:
                    cmd_args = ['start', 'cmd', '/k', cmd]
                else:
                    cmd_args = ['cmd', '/c', cmd]
            else:
                if new_shell:
                    cmd_args = ['gnome-terminal', '--', 'sh', '-c', cmd]
                else:
                    cmd_args = ['sh', '-c', cmd]
        else:
            if sys.platform == 'win32':
                cmd_str = ' '.join(f'"{arg}"' if ' ' in str(arg) else str(arg) for arg in cmd)
                if new_shell:
                    cmd_args = ['start', 'cmd', '/k', cmd_str]
                else:
                    cmd_args = ['cmd', '/c', cmd_str]
            else:
                cmd_args = list(cmd)
                if new_shell:
                    cmd_args = ['gnome-terminal', '--'] + cmd_args
                
        p = subprocess.Popen(
            cmd_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace',
            cwd=cwd,
            env=env,
            shell=True if sys.platform == 'win32' else False
        )
        
        # 存储进程信息
        _background_processes[process_id] = {
            'process': p,
            'start_time': time.time(),
            'cmd': cmd
        }
        
        return {
            'code': 0,
            'out': f'Process started with ID: {process_id}, PID: {p.pid}',
            'err': '',
            'process_id': process_id,
            'pid': p.pid
        }
    except Exception as e:
        return {
            'code': -1,
            'out': '',
            'err': str(e),
            'process_id': process_id,
            'pid': None
        }


@register_tool
def cmd_check_async(process_id: str) -> Dict[str, Any]:
    """
    {
        "func": "检查异步进程状态",
        "params": {
            "process_id": "进程标识符"
        }
    }
    """
    if process_id not in _background_processes:
        return {
            'code': -1,
            'out': '',
            'err': f'Process ID {process_id} not found',
            'status': 'not_found'
        }
    
    proc_info = _background_processes[process_id]
    p = proc_info['process']
    
    try:
        if p.poll() is None:
            # 进程仍在运行
            return {
                'code': 0,
                'out': '',
                'err': '',
                'status': 'running',
                'pid': p.pid,
                'runtime': time.time() - proc_info['start_time']
            }
        else:
            # 进程已结束
            out, err = p.communicate()
            del _background_processes[process_id]
            return {
                'code': p.returncode,
                'out': out,
                'err': err,
                'status': 'finished',
                'pid': p.pid,
                'runtime': time.time() - proc_info['start_time']
            }
    except Exception as e:
        return {
            'code': -1,
            'out': '',
            'err': str(e),
            'status': 'error'
        }


@register_tool
def python_run_code(code: str, 
                   file_path: str, 
                   timeout: int = 60,
                   cwd: Optional[str] = None) -> Dict[str, Any]:
    """
    {
        "func": "运行Python代码",
        "params": {
            "code": "要执行的Python代码字符串",
            "file_path": "代码保存的文件路径",
            "timeout": "超时时间(秒)",
            "cwd": "工作目录"
        }
    }
    """
    if not code:
        return {'code': -1, 'out': '', 'err': '必须提供code参数'}
    
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # 保存代码到指定文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(code)
        
        # 执行文件
        cmd = [sys.executable, file_path]
        result = cmd_run(cmd, timeout=timeout, cwd=cwd)
        
        return result
    except Exception as e:
        return {'code': -1, 'out': '', 'err': str(e)}


@register_tool
def python_run_file(file_path: str, 
                   timeout: int = 60,
                   cwd: Optional[str] = None,
                   args: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    {
        "func": "运行Python文件",
        "params": {
            "file_path": "要执行的Python文件路径",
            "timeout": "超时时间(秒)",
            "cwd": "工作目录",
            "args": "传递给脚本的参数列表"
        }
    }
    """
    if not file_path:
        return {'code': -1, 'out': '', 'err': '必须提供file_path参数'}
    
    if not os.path.exists(file_path):
        return {'code': -1, 'out': '', 'err': f'文件不存在: {file_path}'}
    
    try:
        cmd = [sys.executable, file_path]
        if args:
            cmd.extend(args)
            
        result = cmd_run(cmd, timeout=timeout, cwd=cwd)
        return result
    except Exception as e:
        return {'code': -1, 'out': '', 'err': str(e)}


if __name__ == "__main__":
    # 测试1: 同步命令执行
    print("=== 测试1: 同步命令执行 ===")
    result = cmd_run(["echo", "Hello World"], timeout=5)
    print(f"结果: {result}\n")

    # 测试2: 异步命令执行
    print("=== 测试2: 异步命令执行 ===")
    result = cmd_run_async(["ping", "127.0.0.1", "-n", "3"], "test_ping")
    print(f"启动结果: {result}")
    
    # 检查异步进程状态
    time.sleep(2)
    status = cmd_check_async("test_ping")
    print(f"进程状态: {status}\n")

    # 测试3: Python代码执行
    print("=== 测试3: Python代码执行 ===")
    py_code = '''
print("Python代码测试")
for i in range(3):
    print(f"计数: {i}")
    '''
    result = python_run_code(py_code, "../temp/test_code.py")
    print(f"结果: {result}\n")

    # 测试4: Python文件执行
    print("=== 测试4: Python文件执行 ===")
    if os.path.exists("../temp/test_code.py"):
        result = python_run_file("../temp/test_code.py")
        print(f"结果: {result}")
    else:
        print("测试文件不存在")
