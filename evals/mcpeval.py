"""Example script demonstrating command line arguments in google3."""

from collections.abc import Sequence
from absl import app
from absl import flags
import json
import os
import pprint
import sys
import subprocess
import tempfile
from typing import List, Dict, Any
from pathlib import Path
import pydash

import extract_tool_call

# Define flags
_GOLDEN_PROMPT_RESPONSES = flags.DEFINE_string(name="golden_prompts_responses", default=None, help="Path to a Golden Prompts-Responses JSONL file.")
_CLI_PATH = flags.DEFINE_string(name="gemini_cli_path", default="gemini", help="Path to the Gemini CLI binary.")
_LOCAL_MCP_JSON  = flags.DEFINE_multi_string(name="localmcpjson", default=[], help="JSON Config for local MCP server")
_REMOTE_MCP_JSON = flags.DEFINE_multi_string(name="remotemcpjson", default=[], help="JSON Config for remote MCP server")
_PROMPT_PREPEND  = flags.DEFINE_string(name="prompt_prepend", default="", help="Prepend each prompt with this string")
_MAIN_CONTEXT    = flags.DEFINE_string(name="context", default="", help="Context string that will be written to GEMINI.md")
_GOOGLE_ACCOUNT = flags.DEFINE_bool(name="google_account", default=False, help="Use Google Account for authentication instead of Gemini API key.")

def run_ls(directory):
    try:
        result = subprocess.run(['/bin/ls', '-latr', directory], capture_output=True, text=True, check=True)
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Command failed with error code {e.returncode}")
        print(f"Error message: {e.stderr}")

def load_jsonl_data(file_path: str) -> tuple[List[Dict[str, Any]], bool]:
    data = []
    original_wd = get_working_directory()
    if original_wd and not os.path.isabs(file_path):
        file_path = os.path.join(original_wd, file_path)
        
    print(f'Attempting to read file: {file_path}')

    if check_file_exists(file_path):
        print(f"JSON File exists: {file_path}")
    else:
        print(f"JSON File does not exist: {file_path}")
        return data, False

    if can_read_file(file_path):
        print(f"Have permissions to read JSON file: {file_path}")
    else:
        print(f"Error - DO NOT Have permission to read JSON file: {file_path}")
        return data, False

    with open(file_path, "r") as f:
        try:
            print(f'Successfully opened file for reading: {file_path}')
            data = json.load(f)
            print(f'Successfully parsed JSON in : {file_path}')
            return data, True
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON syntax in {file_path}: {e}")

    return data, True

def can_write_file(filepath):
    try:
        with open(filepath, 'a') as f:
            pass 
        return True
    except (OSError, IOError):
        return False

def can_read_file(filepath):
    try:
        with open(filepath, 'r') as f:
            pass
        return True
    except (OSError, IOError):
        return False

def check_file_exists(filepath) -> bool:
    file_path = Path(filepath)
    if file_path.is_file():
        return True
    else:    
        return False

def write_context_to_file(file_path: str) -> None:
    if _MAIN_CONTEXT.value:
        if can_write_file(file_path):
            with open(file_path, "w") as f:
                print(f"Success! Wrote context to {file_path}.")
                f.write(_MAIN_CONTEXT.value)
    else:
        print("write_context_to_file.FFFF No context to write.")

def create_dot_gemini_dir_write_settings_file() -> bool:
    original_wd = get_working_directory()
    if not original_wd:
        return False

    relative_new_dirs = ".gemini"
    full_path = os.path.join(original_wd, relative_new_dirs)

    try:
        os.makedirs(full_path, exist_ok=True)
        print(f"Successfully created directory structure: {full_path}")

        test_file_path = os.path.join(full_path, "settings.json")
        
        with open(test_file_path, 'w') as f:
            f.write("{ \n"
                    "  \"mcpServers\": { \n")
            
            mcp_servers_entries = []
            for json_text in _LOCAL_MCP_JSON.value:
                mcp_servers_entries.append(json_text)
            for json_text in _REMOTE_MCP_JSON.value:
                mcp_servers_entries.append(json_text)
            
            f.write(",\n".join(mcp_servers_entries))
            f.write("\n   } \n} \n")

        print(f"Created test file: {test_file_path}")
    except OSError as e:
        print(f"Error creating directory structure {full_path}: {e}", file=sys.stderr)
        return False

    return True

def create_local_files_and_dirs_needed() -> bool:
    gemini_md = os.path.join(get_working_directory(), "GEMINI.md")
    write_context_to_file(gemini_md)

    if not create_dot_gemini_dir_write_settings_file():
        return False
    return True

def get_working_directory() -> str:
    if is_in_docker():
        return "./"  
    elif os.getenv('BUILD_WORKING_DIRECTORY'):
        return str(os.getenv('BUILD_WORKING_DIRECTORY'))
    else:
        return str(os.getcwd())

def is_in_docker() -> bool:
    return os.path.exists('/.dockerenv')

def compare_test_results(full_testrun_data: Dict[str, Any], expected_subset_data: Dict[str, Any]) -> bool:
    return pydash.is_match(full_testrun_data, expected_subset_data)

def run_one_testcase(one_testcase: Any) -> float:
    prompt = one_testcase["prompt"]
    print(f"Prompt: {prompt}")
    temp_dir = tempfile.mkdtemp()
    
    log_file_stdout = os.path.join(temp_dir, "gemini_cli.log.stdout")
    log_file_stderr = os.path.join(temp_dir, "gemini_cli.log.stderr")

    # Use the local binary path passed in from the flag
    gemini_cli_path = _CLI_PATH.value
    command = f'{gemini_cli_path} --debug -p "{prompt}" 1> {log_file_stdout} 2> {log_file_stderr}'

    print(f'Command: {command}')

    return_score = 0.0
    try:
        print("Running subprocess.run")
        subprocess.run(command, shell=True, check=False, cwd=get_working_directory())

        if not check_file_exists(log_file_stderr):
            print("ERROR: Stderr log file was not generated.")
            return 0.0

        if one_testcase.get("response", {}).get("name"):
            parsed_results_dict = extract_tool_call.parse_log(log_file_stderr)
            if parsed_results_dict:
                print("Tool call extracted:")
                pprint.pprint(parsed_results_dict)
                
                return_score = 0.0
                
                # Check Result Display
                if compare_test_results(parsed_results_dict.get("resultDisplay"),   one_testcase["response"].get("resultDisplay")):
                    return_score += 0.5
                    print("ResultDisplay match")
                else:
                    print("ResultDisplay NO match")
                
                # Check Status
                if parsed_results_dict.get("status") == "success":
                    return_score += 0.2
                    print("Status success")
                else:
                    print("Status NO match (not success)")
                
                # Check Name
                if parsed_results_dict.get("name") == one_testcase["response"].get("name"):
                    return_score += 0.15
                    print("Name match")
                else:
                    print("Name NO match")
                                
                # Check Args
                if parsed_results_dict.get("args") == one_testcase["response"].get("args"):
                    return_score += 0.15
                    print("Arguments match")
                else:
                    print("Arguments NO match")
                
                return return_score
            else:
                print("\n" + "="*50)
                print("🚨 CRITICAL FAILURE: No tool call found in log file.")
                print("="*50)
                print("--- RAW AI RESPONSE (STDOUT) ---")
                try:
                    with open(log_file_stdout, "r") as f:
                        print(f.read())
                except Exception as e:
                    print(f"Could not read stdout: {e}")
                
                print("\n--- RAW CLI LOGS (STDERR) ---")
                try:
                    with open(log_file_stderr, "r") as f:
                        print(f.read())
                except Exception as e:
                    print(f"Could not read stderr: {e}")
                print("="*50 + "\n")
                return 0.0
        else:
            return 0.0
    except Exception as e:
        print(f"CRITICAL: An unexpected Python error occurred: {e}")
        
    return 0.0
 
def main(argv: Sequence[str]) -> None:
    if len(argv) != 1:
        print("Usage: python mcpeval.py <json file>")
        sys.exit(1)

    if _GOLDEN_PROMPT_RESPONSES.value is None:
        raise app.UsageError('--golden_prompts_responses=<json file> is required')
    
    if not _LOCAL_MCP_JSON.value and not _REMOTE_MCP_JSON.value:
        raise app.UsageError('At least one of --remotemcpjson or --localmcpjson is required')

    if not create_local_files_and_dirs_needed():
        print("Could not create .gemini directory and/or creating GEMINI.md file")
        return

    json_golden_data, success_reading_json = load_jsonl_data(_GOLDEN_PROMPT_RESPONSES.value)

    if not success_reading_json:
        print("Failure reading JSON")
        return
    
    total_score = 0.0
    num_testcases = 0
    for one_test_case in json_golden_data:
        print(f"\nRunning testcase {one_test_case}")
        total_score += run_one_testcase(one_test_case)
        num_testcases += 1
    
    print(f"\nNumber of testcases: {num_testcases}")
    print(f"Total score: {total_score}")
    
    if num_testcases > 0:
        print(f"Average score: {total_score / num_testcases}")
        print(f"Percentage score: {(total_score / num_testcases) * 100}%")
    else:
        print("No test cases evaluated.")

if __name__ == '__main__':
    app.run(main)