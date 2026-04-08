"""Example script demonstrating command line arguments in google3."""

from collections.abc import Sequence

from absl import app
from absl import flags
from absl import logging
import json
import os
import pprint
import sys
import subprocess
import tempfile
from typing import List, Dict, Any
from pathlib import Path
from absl import app
from absl import flags
from absl import logging
from google3.pyglib import gfile
from google3.experimental.users.nadig.evals.mcp import extract_tool_call
import pydash

# Define flags
_GOLDEN_PROMPT_RESPONSES = flags.DEFINE_string(name="golden_prompts_responses", default=None, help="Path to a Golden Prompts-Responses JSONL file.")
_LOCAL_MCP_JSON  = flags.DEFINE_multi_string(name="localmcpjson", default=[], help="JSON Config for local MCP server")
_REMOTE_MCP_JSON = flags.DEFINE_multi_string(name="remotemcpjson", default=[], help="JSON Config for remote MCP server")
_PROMPT_PREPEND  = flags.DEFINE_string(name="prompt_prepend", default="", help="Prepend each prompt with this string")
_MAIN_CONTEXT    = flags.DEFINE_string(name="context", default="", help="Context string that will be written to GEMINI.md")
_GOOGLE_ACCOUNT = flags.DEFINE_bool(name="google_account", default=False, help="Use Google Account for authentication instead of Gemini API key.")

import subprocess

def run_ls(directory):
    try:
        # capture_output=True grabs the output instead of printing it immediately
        # text=True decodes the raw bytes into a standard Python string
        # check=True raises an error if the command fails (e.g., directory doesn't exist)
        result = subprocess.run(['/bin/ls', '-latr', directory], 
                                capture_output=True, 
                                text=True, 
                                check=True)
        
        # Print the captured output
        print(result.stdout)
        
    except subprocess.CalledProcessError as e:
        print(f"Command failed with error code {e.returncode}")
        print(f"Error message: {e.stderr}")


def load_jsonl_data(file_path: str) -> tuple[List[Dict[str, Any]], bool]:
  """Loads prompt-response pairs from a JSONL file."""
  data = []

  # If the path might be relative, it's often best to resolve it
  # against the directory where blaze run was invoked.
  original_wd = get_working_directory()
  if original_wd and not os.path.isabs(file_path):
    file_path = os.path.join(original_wd, file_path)
    print("Updating path to read JSON file...")
    print(f"Original WD: {original_wd}")
    print(f"File path: {file_path}")
    print("-------------------------------")
    
  print(f'Attempting to read file: {file_path}')

  if check_file_exists(file_path):
    print(f"JSONL File exists: {file_path}")
  else:
    print(f"JSONL File does not exist: {file_path}")
    return data, False

  if can_read_file(file_path):
    print(f"Have permissiosn to read JSONL file: {file_path}")
  else:
    print(f"Error - DO NOT Have permission to read JSONL file: {file_path}")
    run_ls("/tmp/")    
    return data, False

  with open(file_path, "r") as f:
    # Use a context manager (with) to ensure the file is always safely closed
    # Explicitly define utf-8 encoding to prevent cross-OS bugs (e.g., Windows defaults)
    try:
      print(f'Successfully opened file for reading: {file_path}')
      data = json.load(f)
      print(f'Successfully parsed JSON in : {file_path}')
      return data, True
    except json.JSONDecodeError as e:
      # Catching the error explicitly makes debugging much easier later
      raise ValueError(f"Failed to parse JSON syntax in {file_path}: {e}")

  return data, True

def can_write_file(filepath):
    try:
        # Use 'a' (append) instead of 'w' (write). 
        # 'w' will immediately truncate (empty) an existing file!
        with open(filepath, 'a') as f:
            pass 
        return True
    except (OSError, IOError):
        # Catches PermissionError, FileNotFoundError (if dir doesn't exist), etc.
        return False


def can_read_file(filepath):
    try:
        # Use 'a' (append) instead of 'w' (write). 
        # 'w' will immediately truncate (empty) an existing file!
        with open(filepath, 'r') as f:
            pass
        return True
    except (OSError, IOError):
        # Catches PermissionError, FileNotFoundError (if dir doesn't exist), etc.
        return False

def check_file_exists(filepath) -> bool:
  file_path = Path(filepath)

  if file_path.is_file():
    return True
  else:    
    return False

def write_context_to_file(file_path: str) -> None:
  """Writes the main context string to the specified file."""
  print("write_context_to_file.0000 Current Dir: "+ str(os.getcwd()))
  print(f"write_context_to_file.AAAA Writing context to file: {file_path}")
  if _MAIN_CONTEXT.value:
    print(f"write_context_to_file.BBBB Writing context to file: {file_path}")
    if can_write_file(file_path):
      print(f"write_context_to_file.CCCC can write to file")
    else:
      print(f"write_context_to_file.CCCC can NOT write to file")
    
    with open(file_path, "w") as f:
      print(f"Success! Wrote context to {file_path}.")
      f.write(_MAIN_CONTEXT.value)
      
    #except PermissionError:
    #  print(f"Error: You do not have permission to write to '{file_path}'.")
    # except IOError as e:
    #  print(f"Error: A system I/O error occurred: {e}")
    #else:
    #  # This acts as your 'else' block for the write operation.
    #  # It only runs if the file was successfully opened, written to, and closed.
  else:
    print("write_context_to_file.FFFF No context to write.")

async def run_flow(json_golden_data: List[Dict[str, Any]]) -> List[int]:
  print("Inside run_flow")
  results: List[int] = [0, 0, 0]

  try:
    print(f"Iterating over {len(json_golden_data)} prompts from input file...")
    for request in json_golden_data:
      print(f"\nEvaluating Request: {request}")
      prompt = request["prompt"]
      print(f"\n\tPrompt: {prompt} ")

  except Exception as e:
      print(f"An error occurred: {e}")

  finally:
    # Clean up the subprocess gracefully
    print("\nShutting down MCP server...")
    #if mcp_server_process.returncode is None:
    #  mcp_server_process.terminate()
    #  await mcp_server_process.wait()
    #  print("Done.")
    return results

def create_dot_gemini_dir_write_settings_file() -> bool:

  # Get the directory where blaze run was launched
  original_wd = get_working_directory()

  if not original_wd:
    print("Warning: Cannot determine the original working directory.", file=sys.stderr)
    return False

  # The relative path for the new directory structure from user input
  relative_new_dirs = ".gemini"

  # Construct the full absolute path
  full_path = os.path.join(original_wd, relative_new_dirs)

  print(" Current Dir: "+ str(os.getcwd()))
  print(f"Attempting to create directory structure: {full_path}")

  try:
    # Create the directory structure.
    # exist_ok=True means it won't raise an error if the directory already exists.
    os.makedirs(full_path, exist_ok=True)
    print(f"Successfully created directory structure: {full_path}")

    # Example: Create a file in the new directory
    test_file_path = os.path.join(full_path, "settings.json")
    auth_type = "google-credentials" if _GOOGLE_ACCOUNT.value else "gemini-api-key"
    with open(test_file_path, 'w') as f:
      #f.write("Hello from blaze run script!\n")
      f.write("{ \n"
              "  \"security\": { \n"
              "      \"auth\": { \n"
              f"          \"selectedType\": \"{auth_type}\" \n"
              "        } \n"
              "   }, \n"
              "  \"mcpServers\": { \n")
      mcp_servers_entries = []
      for json_text in _LOCAL_MCP_JSON.value:
        mcp_servers_entries.append(json_text)
      for json_text in _REMOTE_MCP_JSON.value:
        mcp_servers_entries.append(json_text)
      f.write(",\n".join(mcp_servers_entries))
      f.write("\n   } \n")
      f.write("} \n")

    print(f"Created test file: {test_file_path}")

  except OSError as e:
    print(f"Error creating directory structure {full_path}: {e}", file=sys.stderr)
    return False

  return True

def create_local_files_and_dirs_needed() -> bool:

  # Create GEMINI.md file
  gemini_md = os.path.join(get_working_directory(), "GEMINI.md")
  write_context_to_file(gemini_md)

  # Create .gemini/settings.json file
  if not create_dot_gemini_dir_write_settings_file():
    print("Could not create .gemini dir")
    return False

  return True

def get_working_directory() -> str:
  """Returns the working directory."""
  if is_in_docker():
    return "./"  
  elif os.getenv('BUILD_WORKING_DIRECTORY'):
    return str(os.getenv('BUILD_WORKING_DIRECTORY'))
  else:
    return "./"

def is_in_docker() -> bool:
    """Checks if the script is running inside a Docker container."""
    return os.path.exists('/.dockerenv')

def compare_test_results(full_testrun_data: Dict[str, Any], expected_subset_data: Dict[str, Any]) -> bool:
    """
    Compares two parsed JSON objects to see if expected_subset_data 
    is a subset of full_testrun_data.
    """
    return pydash.is_match(full_testrun_data, expected_subset_data)

# Returns:
# 1.0 if the following are true: 
#   - resultDisplay is a subset of the actual resultDisplay - i.e its a match (0.5 points)
#   - if tool call succeeded (i.e has status == "success") (0.2 points)
#   - tool call name matches, and  (0.15 points)
#   - if the arguments to the tool call match the golden (0.15 points)
#
# In case  

def run_one_testcase(one_testcase: Any) -> float:
  prompt = one_testcase["prompt"]
  print(f"Prompt: {prompt}")
  temp_dir = tempfile.mkdtemp()
  
  log_file_stdout = os.path.join(temp_dir, "gemini_cli.log.stdout")
  log_file_stderr = log_file_stdout.replace("stdout", "stderr")

  print("run_one_testcase.0000.AAAA Current Dir: "+ str(os.getcwd()))
  print("run_one_testcase.0000.BBBB log_file_stdout: " + log_file_stdout)
  print("run_one_testcase.0000.CCCC log_file_stderr: " + log_file_stderr)
  gemini_cli_path = f'/google/bin/releases/gemini-cli/tools/gemini'
  command = f'{gemini_cli_path} --debug -m models/gemini-pro -p "{prompt}" 1> {log_file_stdout} 2> {log_file_stderr}'

  if check_file_exists(gemini_cli_path):
    print(f'gemini-cli FILE exists : {gemini_cli_path}')
  else:
    print(f'gemini-cli FILE DOES NOT exist : {gemini_cli_path}')
  

  print(f'Command: {command}')

  return_score = 0.0
  try:
    print("Running subprocess.run")
    result = subprocess.run(command, shell=True, check=False, capture_output=True, text=True, cwd=get_working_directory())

    if check_file_exists(log_file_stdout):
      print(f"STDOUT Log FILE exists : {log_file_stdout}")
    else:
      print(f"STDOUT Log FILE DOES NOT exist : {log_file_stdout}")      

    if check_file_exists(log_file_stderr):
      print(f"STDERR Log FILE exists : {log_file_stderr}")
    else:
      print(f"STDERR Log FILE DOES NOT exist : {log_file_stderr}")
      return 0.0

    #print("STDOUT:", result.stdout)
    #print("STDERR:", result.stderr)
    if one_testcase.get("response", {}).get("name"):
      parsed_results_dict = extract_tool_call.parse_log(log_file_stderr)
      if parsed_results_dict:
        print("Tool call extracted:")
        pprint.pprint(parsed_results_dict)
        
        return_score = 0.0
        # Compare resultDisplay match
        
        print("-------------------------------\n")
        print("Gemini CLI output ResultDisplay:")
        pprint.pprint(parsed_results_dict.get("resultDisplay"))
        print("-------------------------------\n")
        print("Type of Gemini CLI output ResultDisplay: " + str(type(parsed_results_dict.get("resultDisplay"))))
        print("-------------------------------\n\n")
        print("Expected ResultDisplay:")
        pprint.pprint(one_testcase["response"].get("resultDisplay"))        
        print("-------------------------------\n")
        print("Type of Expected ResultDisplay: " + str(type(one_testcase["response"].get("resultDisplay"))))
        print("-------------------------------\n")
        if compare_test_results(parsed_results_dict.get("resultDisplay"),   one_testcase["response"].get("resultDisplay")):
          return_score += 0.5
          print("ResultDisplay match")
        else:
          print("ResultDisplay NO match")
        
        # Compare tool call status
        if parsed_results_dict.get("status") == "success":
          return_score += 0.2
          print("Status success")
        else:
          print("Status NO match (not success)")
        
        if parsed_results_dict.get("name") == one_testcase["response"].get("name"):
          return_score += 0.15
          print("Name match")
        else:
          print("Name NO match")
                
        # Compare arguments
        if parsed_results_dict.get("args") == one_testcase["response"].get("args"):
          return_score += 0.15
          print("Arguments match")
        else:
          print("Arguments NO match")
        
        return return_score
      else:
        print("No tool call found in log file.")
        try:
          with open(log_file_stderr, "r") as f:
            print("--- gemini-cli stderr ---")
            print(f.read())
            print("--- end gemini-cli stderr ---")
        except Exception as e:
          print(f"Could not read stderr log file: {e}")
        return 0.0
    else:
      print("Not a tool call testcase - need to use autorater.")
      return 0.0
  except subprocess.CalledProcessError as e:
    print("Error:", e.stderr)
  except Exception as e:
    print(f"CRITICAL: An unexpected Python error occurred: {e}")
    
  return 0.0
  

def main(argv: Sequence[str]) -> None:
  print('Number of command-line arguments: ' + str(len(argv)))

  if len(argv) != 1:
    print("Usage: python mcpeval.py <json file>")
    sys.exit(1)

  if is_in_docker():
    print("Inside docker container")
    os.chdir('/tmp')
  else:
    print("NOT in docker container")  

  if not can_write_file("./GEMINI.md"):
    print("Cannot write to current directory. Exiting!")
    return

  if _GOLDEN_PROMPT_RESPONSES.value is None:
    raise app.UsageError('--golden_prompts_responses=<json file> is required')
  
  print("main.AAAA . _GOLDEN_PROMPT_RESPONSES : " + str(_GOLDEN_PROMPT_RESPONSES.value))

  if not _LOCAL_MCP_JSON.value and not _REMOTE_MCP_JSON.value:
    raise app.UsageError('Atleast one of --remotemcpjson or --localmcpjson is required')

  print("main.BBBB")
  
  if _LOCAL_MCP_JSON.value:
    print("main.CCCC --localmcpjson")
    for v in _LOCAL_MCP_JSON.value:
      print("main.DDDD")
      print("\t" + v)
  else:
    print("main.EEEE No local MCP JSON")

  print("main.FFFF")

  if _REMOTE_MCP_JSON.value:
    print("main.GGGG --localmcpjson")
    for v in _LOCAL_MCP_JSON.value:
      print("main.HHHH")
      print("\t" + v)
  else:
    print("main.IIII No remote MCP JSON")

  print("main.JJJJ")
  print(" Current Dir: "+ str(os.getcwd()))
  if not create_local_files_and_dirs_needed():
    print("main.KKKK")
    print("Could not create .gemini directory and/or creating GEMINI.md file")
    return

  print("main.LLLL")
  # Load JSON data
  json_golden_data, success_reading_json = load_jsonl_data(_GOLDEN_PROMPT_RESPONSES.value)

  if not success_reading_json:
    print("Failure reading JSON")
    return
  
  print("Success reading JSON")
  print("main.MMMM")
  print("Running run_flow")

  total_score = 0.0
  num_testcases = 0
  for one_test_case in json_golden_data:
    print(f"Running testcase {one_test_case}")
    total_score += run_one_testcase(one_test_case)
    num_testcases += 1
  
  print(f"Number of testcases: {num_testcases}")
  print(f"Total score: {total_score}")

  print(f"Average score: {total_score / num_testcases}")
  print(f"Percentage score: {(total_score / num_testcases) * 100}")
  print("main.NNNN - DONE")


if __name__ == '__main__':
  # app.run will parse the flags and call main
  app.run(main)
  #asyncio.run(app.run(main))

