from tools import register_tool
import json
import subprocess
from pathlib import Path
from typing import Any



@register_tool
def bash(command: str = "", restart: bool = False) -> str:
    """
    {
        "fn": "Execute bash commands in a persistent shell session. This tool allows you to run shell commands, navigate directories, install packages, etc.",
        "args": {
            "command": "The bash command to execute. For example: 'ls -la', 'cd /path/to/dir', 'pip install package'",
            "restart": "Restart the bash session. Set to true if you want to start a fresh shell session"
        }
    }
    """
    if restart:
        return "Bash session restarted successfully."
    
    if not command:
        return "Error: No command provided. Please specify a command to execute."
    
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=120
        )
        output = result.stdout if result.stdout else result.stderr
        if len(output) > 1000:
            output = output[:1000] + "\n<output clipped - too long>"
        return output
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 120 seconds"
    except Exception as e:
        return f"Error executing command: {str(e)}"

@register_tool
def edit_file(command: str, path: str, file_text: str = "", insert_line: int = -1, 
              new_str: str = "", old_str: str = "") -> str:
    """
    {
        "fn": "Edit files using various operations such as view, create, insert, and string replace. This tool can manage file content in multiple ways.",
        "args": {
            "command": "The edit operation to perform. Options: 'view', 'create', 'insert', 'str_replace'",
            "path": "Absolute path to the file or directory to operate on",
            "file_text": "Text content for file creation (used with 'create' command)",
            "insert_line": "Line number where to insert new content (used with 'insert' command)",
            "new_str": "New string to insert or replace with (used with 'insert' and 'str_replace' commands)",
            "old_str": "Existing string to be replaced (used with 'str_replace' command)"
        }
    }
    """
    if not path:
        return "Error: No path provided. Please specify an absolute path."
    
    try:
        file_path = Path(path)
        
        # Check if path is absolute
        if not file_path.is_absolute():
            return "Error: Please provide an absolute path."
        
        if command == "view":
            if file_path.is_dir():
                # List directory contents
                try:
                    entries = list(file_path.iterdir())
                    output_lines = [f"Directory contents of {path}:"]
                    for entry in entries:
                        marker = "/" if entry.is_dir() else ""
                        output_lines.append(f"  {entry.name}{marker}")
                    return "\n".join(output_lines)
                except Exception as e:
                    return f"Error listing directory: {str(e)}"
            else:
                # View file contents
                if not file_path.exists():
                    return f"Error: File {path} does not exist."
                try:
                    content = file_path.read_text()
                    lines = content.splitlines()
                    output_lines = [f"File: {path}"]
                    for i, line in enumerate(lines, 1):
                        output_lines.append(f"{i:6}  {line}")
                    output = "\n".join(output_lines)
                    if len(output) > 2000:
                        output = output[:2000] + "\n<output clipped - too long>"
                    return output
                except Exception as e:
                    return f"Error reading file: {str(e)}"
        
        elif command == "create":
            if not file_text:
                return "Error: No file_text provided for create command."
            try:
                # Create parent directories if they don't exist
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(file_text)
                return f"File {path} created successfully."
            except Exception as e:
                return f"Error creating file: {str(e)}"
        
        elif command == "str_replace":
            if not old_str or not new_str:
                return "Error: Both old_str and new_str must be provided for str_replace command."
            if not file_path.exists():
                return f"Error: File {path} does not exist."
            
            try:
                content = file_path.read_text()
                
                # Count occurrences
                count = content.count(old_str)
                if count == 0:
                    return f"Error: String '{old_str}' not found in file."
                if count > 1:
                    return f"Error: Multiple occurrences ({count}) of string '{old_str}' found. Replacement must be unique."
                
                # Replace and write back
                new_content = content.replace(old_str, new_str)
                file_path.write_text(new_content)
                return f"File {path} edited successfully."
            except Exception as e:
                return f"Error editing file: {str(e)}"
        
        elif command == "insert":
            if insert_line < 0 or not new_str:
                return "Error: Valid insert_line and new_str must be provided for insert command."
            if not file_path.exists():
                return f"Error: File {path} does not exist."
            
            try:
                lines = file_path.read_text().splitlines(keepends=True)
                
                if insert_line > len(lines):
                    return f"Error: Line number {insert_line} is beyond the end of file."
                
                lines.insert(insert_line, new_str + "\n")
                file_path.write_text("".join(lines))
                return f"File {path} edited successfully."
            except Exception as e:
                return f"Error editing file: {str(e)}"
        
        else:
            return f"Error: Invalid command '{command}'. Supported commands: view, create, str_replace, insert."
            
    except Exception as e:
        return f"Error processing edit operation: {str(e)}"

@register_tool
def json_edit(operation: str, file_path: str, json_path: str = "", value: Any = None) -> str:
    """
    {
        "fn": "Edit JSON files using JSONPath expressions. This tool supports viewing, setting, adding, and removing values in JSON files.",
        "args": {
            "operation": "The operation to perform. Options: 'view', 'set', 'add', 'remove'",
            "file_path": "Absolute path to the JSON file to operate on",
            "json_path": "JSONPath expression to locate the value. Examples: '$.users[0].name', '$.config.setting'",
            "value": "The value to set or add. Not required for 'view' and 'remove' operations"
        }
    }
    """
    if not file_path:
        return "Error: file_path is required."
    
    try:
        path = Path(file_path)
        
        if not path.is_absolute():
            return "Error: Please provide an absolute file path."
        
        if not path.exists():
            return f"Error: File {file_path} does not exist."
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            return f"Error: Invalid JSON in file {file_path}: {str(e)}"
        except Exception as e:
            return f"Error reading file {file_path}: {str(e)}"
        
        if operation == "view":
            if not json_path:
                output = json.dumps(data, indent=2, ensure_ascii=False)
                if len(output) > 2000:
                    output = output[:2000] + "\n<output clipped - too long>"
                return output
            else:
                try:
                    from jsonpath_ng import parse as jsonpath_parse
                    jsonpath_expr = jsonpath_parse(json_path)
                    matches = jsonpath_expr.find(data)
                    if not matches:
                        return f"Error: No matches found for JSONPath '{json_path}'"
                    result = matches[0].value if len(matches) == 1 else [match.value for match in matches]
                    return json.dumps(result, indent=2, ensure_ascii=False)
                except Exception as e:
                    return f"Error evaluating JSONPath '{json_path}': {str(e)}"
        
        elif operation == "set":
            if not json_path:
                return "Error: json_path is required for set operation."
            if value is None:
                return "Error: value is required for set operation."
            
            try:
                from jsonpath_ng import parse as jsonpath_parse
                from jsonpath_ng.ext import parse as jsonpath_ext_parse
                
                try:
                    jsonpath_expr = jsonpath_ext_parse(json_path)
                except:
                    jsonpath_expr = jsonpath_parse(json_path)
                    
                matches = jsonpath_expr.find(data)
                if not matches:
                    return f"Error: No matches found for JSONPath '{json_path}'"
                if len(matches) > 1:
                    return f"Error: Multiple matches found for JSONPath '{json_path}'. Only single updates allowed."
                
                matched = matches[0]
                if matched.context is None:
                    data = value
                else:
                    if isinstance(matched.context.value, list):
                        matched.context.value[matched.path.index] = value
                    elif isinstance(matched.context.value, dict):
                        matched.context.value[matched.path.fields[0]] = value
                    
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                return "JSON updated successfully."
                
            except Exception as e:
                return f"Error updating JSON: {str(e)}"
        
        elif operation == "add":
            if not json_path:
                return "Error: json_path is required for add operation."
            if value is None:
                return "Error: value is required for add operation."
            
            try:
                from jsonpath_ng import parse as jsonpath_parse
                jsonpath_expr = jsonpath_parse(json_path)
                matches = jsonpath_expr.find(data)
                
                if not matches:
                    # Special case: adding to root object
                    if json_path == "$":
                        if isinstance(data, dict) and isinstance(value, dict):
                            data.update(value)
                        else:
                            return "Error: Invalid value for root object addition."
                    else:
                        return f"Error: No matches found for JSONPath '{json_path}'"
                elif len(matches) > 1:
                    return f"Error: Multiple matches found for JSONPath '{json_path}'. Only single additions allowed."
                else:
                    matched = matches[0]
                    if isinstance(matched.value, list):
                        matched.value.append(value)
                    elif isinstance(matched.value, dict):
                        # For dict, we would need to know the key, which should be in the path
                        return f"Error: Cannot add to dict with this path format. Use set operation instead."
                    else:
                        return f"Error: Cannot add to non-container type {type(matched.value)}."
                
                # Write back to file
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                return "JSON updated successfully."
                
            except Exception as e:
                return f"Error adding to JSON: {str(e)}"
        
        elif operation == "remove":
            if not json_path:
                return "Error: json_path is required for remove operation."
            
            try:
                from jsonpath_ng import parse as jsonpath_parse
                jsonpath_expr = jsonpath_parse(json_path)
                matches = jsonpath_expr.find(data)
                
                if not matches:
                    return f"Error: No matches found for JSONPath '{json_path}'"
                if len(matches) > 1:
                    return f"Error: Multiple matches found for JSONPath '{json_path}'. Only single removal allowed."
                
                matched = matches[0]
                if matched.context is None:
                    return "Error: Cannot remove root element."
                else:
                    if isinstance(matched.context.value, list):
                        del matched.context.value[matched.path.index]
                    elif isinstance(matched.context.value, dict):
                        del matched.context.value[matched.path.fields[0]]
                
                # Write back to file
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                return "JSON updated successfully."
                
            except Exception as e:
                return f"Error removing from JSON: {str(e)}"
        
        else:
            return f"Error: Invalid operation '{operation}'. Supported operations: view, set, add, remove."
            
    except Exception as e:
        return f"Error processing JSON edit operation: {str(e)}"