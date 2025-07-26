import json
from typing import Dict
def format_agent_config(agent_cfg: Dict) -> str:
    lines = []
    for agent_id, info in agent_cfg.items():
        lines.append(f"[Agent ID: {agent_id}]")
        lines.append(f"  Description: {info.get('desc', 'N/A')}")
        lines.append(f"  Interfaces:")
        for interface in info.get("exec_interface", []):
            fn = interface.get("fn", "unknown_fn")
            desc = interface.get("desc", "No description.")
            args = interface.get("args", {})
            args_str = "\n        ".join(f"{k}: {v}" for k, v in args.items())
            lines.append(f"    - Function: {fn}")
            lines.append(f"      Description: {desc}")
            lines.append(f"      Arguments:\n        {args_str}")
        lines.append("") 
    return "\n".join(lines)

def parse_json_resp(resp:str):
    if resp.startswith("{"):
        return json.loads(resp)
    elif resp.startswith("```json") and resp.endswith("```"):
        return json.loads(resp[7:-3])
    else:
        return json.loads(resp)