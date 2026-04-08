import json
import os
from typing import Any, Dict, Optional

def _extract_from_json(data: Any) -> Optional[Dict[str, Any]]:
    if isinstance(data, dict) and data.get('type') == 'tool-calls-update':
        tool_calls = data.get('toolCalls', [])
        if tool_calls:
            tool_call = tool_calls[0]
            request = tool_call.get('request', {})

            name = request.get('name')
            args = request.get('args')
            call_id = request.get('callId')
            status = tool_call.get('status')
            response = tool_call.get('response') or {}
            try:
                result_display = json.loads(response.get('resultDisplay'))
            except TypeError:
                # Handle cases where resultDisplay is None or not a string
                result_display = ''
            except json.JSONDecodeError:
                result_display =  ''
            
            return {
                "name": name,
                "args": args,
                "callId": call_id,
                "status": status,
                "resultDisplay": result_display
            }
    return None

def parse_log(file_path: str) -> Optional[Dict[str, Any]]:
    """
    Parses a gemini-cli log file to extract the first occurrence of a tool call.
    """
    if not os.path.exists(file_path):
        return None

    with open(file_path, 'r') as f:
        # Try parsing the entire file as JSON first (e.g., for pretty.json testcases)
        content = f.read()
        try:
            data = json.loads(content)
            result = _extract_from_json(data)
            if result:
                return result
        except json.JSONDecodeError:
            pass

        # Fallback to parsing line-by-line for gemini-cli logs
        f.seek(0)
        #for line in f:
        for line in reversed(f.readlines()):
            # Look for the characteristic prefix of tool call messages in gemini-cli logs
            if '[MESSAGE_BUS] publish: ' in line:
                # Extract the JSON part after the prefix
                parts = line.split('[MESSAGE_BUS] publish: ', 1)
                if len(parts) >= 2:
                    json_str = parts[1].strip()
                    try:
                        data = json.loads(json_str)
                        result = _extract_from_json(data)
                        if result:
                            # We break on the first valid occurrence
                            return result
                    except json.JSONDecodeError:
                        continue
    return None
