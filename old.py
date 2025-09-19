import json
import re
import subprocess
import os
import logging
import uuid
import requests
from datetime import datetime, timezone
from pymongo import MongoClient
from langchain_ollama import ChatOllama

# Setup logging with UTF-8 encoding
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('llm_agent.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# MongoDB setup
try:
    mongo_client = MongoClient("mongodb://localhost:27017", serverSelectionTimeoutMS=5000)
    mongo_client.admin.command('ping')
    logger.info("MongoDB connection established")
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {e}")
db = mongo_client["trello_mcp"]
sessions_collection = db["sessions"]

# Session globals
session_id = str(uuid.uuid4())
session_doc_id = sessions_collection.insert_one({
    "session_id": session_id,
    "started_at": datetime.now(timezone.utc),
    "interactions": [],
    "cache": []
}).inserted_id
logger.info(f"Started session with ID: {session_id}")

# Start of get the list of boards and lists in the trello and then parse them and save in the data base
def parse_boards_output(output: str) -> str:
    logger.debug(f"Parsing boards output: {output[:500]}...")
    if not output.strip():
        logger.warning("Empty boards output received")
        return json.dumps({"result": []})

    lines = output.splitlines()
    json_lines = []
    brace_count = 0
    in_result = False
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if '[INFO] Result:' in line and '{' in line:
            in_result = True
            json_start = line.find('{')
            json_lines.append(line[json_start:])
            brace_count += line[json_start:].count('{') + line[json_start:].count('[')
        elif in_result:
            json_lines.append(line)
            brace_count += line.count('{') + line.count('[')
            brace_count -= line.count('}') + line.count(']')
            if brace_count <= 0:
                in_result = False
    cleaned_output = '\n'.join(json_lines).strip()

    if not cleaned_output:
        logger.warning("No valid JSON found in boards output")
        return json.dumps({"result": []})

    try:
        parsed = json.loads(cleaned_output)
        boards = parsed["result"] if isinstance(parsed, dict) and "result" in parsed else parsed
        boards_cache = [
            {"id": board["id"], "name": board["name"]}
            for board in boards
            if isinstance(board, dict) and "id" in board and "name" in board
        ]
        logger.info(f"Parsed {len(boards_cache)} boards")
        return json.dumps({"result": boards_cache})
    except json.JSONDecodeError:
        match = re.search(r'"result"\s*:\s*(\[(?:[^][{}]+|\{(?:[^{}]+|\{[^{}]*\})*\}|\[(?:[^][{}]+|\{[^{}]*\}|\[[^][{}]*\])*\])*?\])', output, re.DOTALL)
        if match:
            try:
                boards = json.loads(match.group(1))
                boards_cache = [
                    {"id": board["id"], "name": board["name"]}
                    for board in boards
                    if isinstance(board, dict) and "id" in board and "name" in board
                ]
                logger.info(f"Parsed {len(boards_cache)} boards via regex fallback")
                return json.dumps({"result": boards_cache})
            except json.JSONDecodeError:
                logger.error("Regex fallback failed to parse boards output")
        logger.error("Failed to parse boards output")
        return json.dumps({"result": []})

def run_get_boards() -> str:
    server_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'trello-mcp-server'))
    logger.info(f"Running get_boards in directory: {server_dir}")
    if not os.path.isdir(server_dir):
        logger.error(f"Directory {server_dir} does not exist")
        return f"Error: Directory {server_dir} does not exist or is not a directory."
    try:
        result = subprocess.run(
            'npm run start:client get_boards {}',
            cwd=server_dir,
            shell=True,
            capture_output=True,
            text=True,
            check=True
        )
        logger.info(f"get_boards executed successfully")
        return result.stdout + "\n" + result.stderr
    except subprocess.CalledProcessError as e:
        logger.error(f"Error executing get_boards: {e.stderr}")
        return f"Error executing get_boards: {e.stderr}"
    except FileNotFoundError:
        logger.error("npm not installed or command not found")
        return "Error: npm not installed or command not found"

def run_get_board_lists(board_id: str) -> str:
    server_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'trello-mcp-server'))
    logger.info(f"Running get_board_lists for board {board_id} in directory: {server_dir}")
    if not os.path.isdir(server_dir):
        logger.error(f"Directory {server_dir} does not exist")
        return f"Error: Directory {server_dir} does not exist or is not a directory."
    args = {"boardId": board_id}
    args_json = json.dumps(args).replace('"', '\\"')
    cmd = f'npm run start:client get_board_lists "{args_json}"'
    try:
        result = subprocess.run(
            cmd,
            cwd=server_dir,
            shell=True,
            capture_output=True,
            text=True,
            check=True
        )
        logger.info(f"get_board_lists executed successfully for board {board_id}")
        return result.stdout + "\n" + result.stderr
    except subprocess.CalledProcessError as e:
        logger.error(f"Error executing get_board_lists for board {board_id}: {e.stderr}")
        return f"Error executing get_board_lists: {e.stderr}"
    except FileNotFoundError:
        logger.error("npm not installed or command not found")
        return "Error: npm not installed or command not found"

def parse_board_lists_output(output: str) -> str:
    logger.debug(f"Parsing board lists output: {output[:500]}...")
    if not output.strip():
        logger.warning("Empty board lists output received")
        return json.dumps({"result": []})
    lines = output.splitlines()
    json_lines = []
    brace_count = 0
    in_result = False
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if '[INFO] Result:' in line and '{' in line:
            in_result = True
            json_start = line.find('{')
            json_lines.append(line[json_start:])
            brace_count += line[json_start:].count('{') + line[json_start:].count('[')
        elif in_result:
            json_lines.append(line)
            brace_count += line.count('{') + line.count('[')
            brace_count -= line.count('}') + line.count(']')
            if brace_count <= 0:
                in_result = False
    cleaned_output = '\n'.join(json_lines).strip()
    if not cleaned_output:
        logger.warning("No valid JSON found in board lists output")
        return json.dumps({"result": []})
    try:
        parsed = json.loads(cleaned_output)
        lists = parsed["result"] if isinstance(parsed, dict) and "result" in parsed else parsed
        lists_cache = [
            {"id": lst["id"], "name": lst["name"]}
            for lst in lists
            if isinstance(lst, dict) and "id" in lst and "name" in lst
        ]
        logger.info(f"Parsed {len(lists_cache)} lists")
        return json.dumps({"result": lists_cache})
    except json.JSONDecodeError:
        match = re.search(r'"result"\s*:\s*(\[(?:[^][{}]+|\{(?:[^{}]+|\{[^{}]*\})*\}|\[(?:[^][{}]+|\{[^{}]*\}|\[[^][{}]*\])*\])*?\])', output, re.DOTALL)
        if match:
            try:
                lists = json.loads(match.group(1))
                lists_cache = [
                    {"id": lst["id"], "name": lst["name"]}
                    for lst in lists
                    if isinstance(lst, dict) and "id" in lst and "name" in lst
                ]
                logger.info(f"Parsed {len(lists_cache)} lists via regex fallback")
                return json.dumps({"result": lists_cache})
            except json.JSONDecodeError:
                logger.error("Regex fallback failed to parse board lists output")
        logger.error("Failed to parse board lists output")
        return json.dumps({"result": []})

def fetch_and_store_boards() -> list:
    logger.info("Starting fetch_and_store_boards")
    raw_boards_output = run_get_boards()
    if "Error" in raw_boards_output:
        logger.error(f"Failed to fetch boards: {raw_boards_output}")
        return []
    boards_result = parse_boards_output(raw_boards_output)
    try:
        boards = json.loads(boards_result)["result"]
        logger.info(f"Fetched {len(boards)} boards")
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse boards result JSON: {e}")
        return []
    output = []
    for board in boards:
        board_data = {"id": board["id"], "name": board["name"], "lists": []}
        raw_lists_output = run_get_board_lists(board["id"])
        if "Error" in raw_lists_output:
            logger.error(f"Failed to fetch lists for board {board['id']}: {raw_lists_output}")
        else:
            lists_result = parse_board_lists_output(raw_lists_output)
            try:
                lists = json.loads(lists_result)["result"]
                logger.info(f"Fetched {len(lists)} lists for board {board['id']}")
                board_data["lists"] = lists
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse lists result JSON for board {board['id']}: {e}")
        output.append(board_data)
    try:
        result = sessions_collection.update_one(
            {"session_id": session_id},
            {"$set": {"cache": output, "cache_updated_at": datetime.now(timezone.utc)}},
            upsert=True
        )
        if result.modified_count > 0 or result.upserted_id:
            logger.info(f"Stored {len(output)} boards with lists in sessions.cache: {json.dumps(output)}")
        else:
            logger.warning(f"No changes made to sessions.cache")
    except Exception as e:
        logger.error(f"Failed to store boards and lists in sessions.cache: {e}")
    try:
        session_doc = sessions_collection.find_one({"session_id": session_id}, {"_id": 0, "cache": 1, "cache_updated_at": 1})
        if session_doc and "cache" in session_doc:
            logger.info(f"Verified cache: {json.dumps(session_doc['cache'], default=str)}")
        else:
            logger.warning(f"No cache found in sessions")
    except Exception as e:
        logger.error(f"Failed to verify sessions.cache: {e}")
    logger.info(f"Completed fetch_and_store_boards with {len(output)} boards")
    return output

# End of get the list of boards and lists in the trello and then parse them and save in the data base
# Start function to get the id from the name (Trello boards and lists ...)
def resolve_names_to_ids(args: dict, session_id: str) -> dict:
    """
    Resolve board and list names to IDs using sessions.cache.
    Args:
        args (dict): Arguments containing boardId and/or listId (names or IDs).
        session_id (str): Current session ID to query sessions.cache.
    Returns:
        dict:
            - {"status": "success", "args": {...}} if resolved
            - {"status": "disambiguate", "type": "board" or "list", "name": "...", "options": [...], "args": {...}} if multiple matches
            - {"status": "error", "message": "..."} if not found
    """
    logger.info(f"Resolving names to IDs for args: {args}")
    resolved_args = args.copy()
    board_name = args.get("boardId")
    list_name = args.get("listId")
    try:
        session_doc = sessions_collection.find_one({"session_id": session_id}, {"_id": 0, "cache": 1})
        if not session_doc or "cache" not in session_doc:
            logger.error(f"No cache found for session_id: {session_id}")
            return {"status": "error", "message": "No board/list cache available."}
        cache = session_doc["cache"]
    except Exception as e:
        logger.error(f"Failed to fetch sessions.cache: {e}")
        return {"status": "error", "message": "Failed to access board/list cache."}
    if board_name and not re.match(r'^[0-9a-f]{24}$', board_name):  # Assume non-ID is a name
        matching_boards = [board for board in cache if board.get("name").lower() == board_name.lower()]
        if not matching_boards:
            logger.warning(f"No boards found with name: {board_name}")
            return {"status": "error", "message": f"No board found with name '{board_name}'."}
        elif len(matching_boards) > 1:
            logger.info(f"Multiple boards found with name: {board_name}")
            return {
                "status": "disambiguate",
                "type": "board",
                "name": board_name,
                "options": [{"id": board["id"], "name": board["name"]} for board in matching_boards],
                "args": args
            }
        else:
            resolved_args["boardId"] = matching_boards[0]["id"]
            logger.info(f"Resolved board '{board_name}' to ID: {resolved_args['boardId']}")
    if list_name and not re.match(r'^[0-9a-f]{24}$', list_name) and "boardId" in resolved_args:
        board_id = resolved_args["boardId"]
        matching_board = next((board for board in cache if board["id"] == board_id), None)
        if not matching_board:
            logger.error(f"Board ID {board_id} not found in cache")
            return {"status": "error", "message": f"Board ID {board_id} not found in cache."}
        matching_lists = [lst for lst in matching_board.get("lists", []) if lst.get("name").lower() == list_name.lower()]
        if not matching_lists:
            logger.warning(f"No lists found with name: {list_name} in board: {board_id}")
            return {"status": "error", "message": f"No list found with name '{list_name}' in board."}
        elif len(matching_lists) > 1:
            logger.info(f"Multiple lists found with name: {list_name} in board: {board_id}")
            return {
                "status": "disambiguate",
                "type": "list",
                "name": list_name,
                "options": [{"id": lst["id"], "name": lst["name"]} for lst in matching_lists],
                "args": args
            }
        else:
            resolved_args["listId"] = matching_lists[0]["id"]
            logger.info(f"Resolved list '{list_name}' to ID: {resolved_args['listId']} in board: {board_id}")
    return {"status": "success", "args": resolved_args}

# End of function to get the id from the name (Trello boards and lists ...)
# Start load tools (Trello + Calendar) mazel mail
def load_all_tools() -> list[dict]:
    tools = []
    trello_tools_json_path = os.path.join(os.path.dirname(__file__), '..', 'tools.json')
    try:
        with open(trello_tools_json_path, 'r', encoding='utf-8') as f:
            trello_tools = json.load(f)
            for tool in trello_tools:
                tool['source'] = 'trello'
            tools.extend(trello_tools)
        logger.info("Successfully loaded Trello tools")
    except Exception as e:
        logger.error(f"Error loading Trello tools.json: {e}")
    calendar_tools_json_path = os.path.join(os.path.dirname(__file__), '..', 'calendar-tools.json')
    try:
        with open(calendar_tools_json_path, 'r', encoding='utf-8') as f:
            calendar_tools = json.load(f)
            tools.extend(calendar_tools)
        logger.info("Successfully loaded Calendar tools")
    except Exception as e:
        logger.error(f"Error loading calendar-tools.json: {e}")
    return 

# End of load tools (Trello + Calendar) mazel mail
#start Check for the tool if its related to the llm usage
def is_task_management_related_llm(user_prompt: str) -> bool:
    llm = ChatOllama(model="llama3", base_url="http://localhost:11434", temperature=0)
    relevance_prompt = f"""
You are a helpful assistant.
Is the following user query related to Trello task, board, list, or member management, or Calendar event management?
Answer ONLY with "YES" or "NO".
User query: "{user_prompt}"
"""
    response = llm.invoke(relevance_prompt)
    reply = response.content.strip().upper() if hasattr(response, "content") else str(response).strip().upper()
    logger.info(f"Task management relevance check for '{user_prompt}': {reply}")
    return "YES" in reply

#End of Check for the tool if its related to the llm usage

# Start check if the prompt is trello related or calendar related
def classify_prompt_category(user_prompt: str) -> str:
    llm = ChatOllama(model="llama3", base_url="http://localhost:11434", temperature=0)
    classify_prompt = f"""
You are a classification assistant for a task management system.
Determine whether the following user query is related to Trello (task, board, list, or member management) or Calendar (event scheduling and management).
Respond ONLY with "trello" or "calendar". If unsure, respond with "calendar".
User query: "{user_prompt}"
"""
    response = llm.invoke(classify_prompt)
    short_response = response.content.strip().lower() if hasattr(response, "content") else str(response).strip().lower()
    logger.info(f"Prompt category for '{user_prompt}': {short_response}")
    return short_response if short_response in ["trello", "calendar"] else "calendar"

# End of check if the prompt is trello related or calendar related
# Start gessing the tools that the llm will be using
def guess_tool_from_prompt(user_prompt: str, tools: list[dict], session_id: str) -> list[dict]:
    category = classify_prompt_category(user_prompt)
    tool_descriptions = "\n\n".join([
        f"Tool name: {tool['name']}\nSource: {tool['source']}\nDescription: {tool['description']}\nInput Schema:\n{json.dumps(tool.get('inputSchema') or tool.get('parameters'), indent=2)}"
        for tool in tools
    ])
    prompt = f"""
You are a tool selection assistant for a task management system that supports Trello (task, board, list, member, card, checklist, label management), Calendar (event scheduling and management), and potentially other services. Your job is to select the BEST matching tool(s) for a user request from the provided list of tools, based on the query's intent, tool names, descriptions, and schemas.

Respond with a JSON array of objects, where each object has:
{{
  "tool": "tool_name",
  "source": "trello or calendar",
  "args": {{ ... }}
}}
- If multiple tools are needed, include all in the array.
- If only one tool is needed, return a single-item array.
- If no tool matches exactly, return an empty array.
- For Trello tools requiring boardId or listId, resolve names to IDs using the provided cache. If a name matches multiple boards/lists, return a disambiguation object:
  {{
    "tool": "tool_name",
    "source": "trello",
    "args": {{ ... }},
    "status": "disambiguate",
    "type": "board" or "list",
    "name": "...",
    "options": [{{"id": "...", "name": "..."}}, ...]
  }}
- If a board/list name is not found, return a disambiguation object with an error message:
  {{
    "tool": "tool_name",
    "source": "trello",
    "args": {{ ... }},
    "status": "error",
    "message": "..."
  }}
- For Trello create_card, include a default name "Untitled Card" if not specified.

**Instructions**:
- Match exact tool names from the available tools list. Do not invent tool names.
- Use descriptions and schemas to match the user’s intent.
- Handle synonyms: 'add'/'create'/'make' for creation tools, 'get'/'show'/'list' for retrieval tools, 'edit'/'update' for update tools, 'delete'/'remove' for deletion tools.
- For Trello queries, resolve board/list names to IDs using the cache. If ambiguous, include disambiguation data.
- For Calendar tools, use default "userId": "current_user" if not specified.
- Ensure args match the tool’s input schema.

🛠️ Available tools:
{tool_descriptions}

🧠 Example 1:
User: get information about my account
Output: [{{
  "tool": "get_me",
  "source": "trello",
  "args": {{}}
}}]

🧠 Example 2:
User: add a new card inside the board test-mcp in the list test
Cache: [{{"id": "686b7c8622f3834294acc4eb", "name": "test-mcp", "lists": [{{"id": "687653ce3121f631bd931d85", "name": "test"}}]}}]
Output: [{{
  "tool": "create_card",
  "source": "trello",
  "args": {{ "boardId": "686b7c8622f3834294acc4eb", "listId": "687653ce3121f631bd931d85", "name": "Untitled Card" }}
}}]

🧠 Example 3:
User: add a new card inside the board test-mcp in the list hello
Cache: [{{"id": "686b7c8622f3834294acc4eb", "name": "test-mcp", "lists": [
  {{"id": "687653cc69e8c963d9eef70e", "name": "hello"}},
  {{"id": "687a5448d31d683f84a57856", "name": "hello"}}
]}}]
Output: [{{
  "tool": "create_card",
  "source": "trello",
  "args": {{ "boardId": "686b7c8622f3834294acc4eb", "listId": "hello", "name": "Untitled Card" }},
  "status": "disambiguate",
  "type": "list",
  "name": "hello",
  "options": [
    {{"id": "687653cc69e8c963d9eef70e", "name": "hello"}},
    {{"id": "687a5448d31d683f84a57856", "name": "hello"}}
  ]
}}]

User: {user_prompt}
ONLY respond with a valid JSON array. No explanations.
"""
    llm = ChatOllama(model="llama3", base_url="http://localhost:11434", temperature=0)
    response = llm.invoke(prompt)
    try:
        raw = response.content if hasattr(response, "content") else str(response)
        match = re.search(r'\[.*\]', raw, re.DOTALL)
        if not match:
            logger.error("No JSON array found in LLM response")
            raise ValueError("No JSON array found in response.")
        json_str = match.group(0)
        tool_choices = json.loads(json_str)
        if not isinstance(tool_choices, list):
            logger.error("LLM response is not a JSON array")
            raise ValueError("Response is not a JSON array.")
        
        # Resolve board/list names to IDs
        resolved_choices = []
        for choice in tool_choices:
            if choice.get("source") != "trello" or choice.get("status") in ["disambiguate", "error"]:
                resolved_choices.append(choice)
                continue
            args = choice.get("args", {})
            # Add default name for create_card if missing
            if choice.get("tool") == "create_card" and "name" not in args:
                args["name"] = "Untitled Card"
            resolution = resolve_names_to_ids(args, session_id)
            if resolution["status"] == "success":
                resolved_choices.append({
                    "tool": choice["tool"],
                    "source": choice["source"],
                    "args": resolution["args"]
                })
            else:
                resolved_choices.append({
                    "tool": choice["tool"],
                    "source": choice["source"],
                    "args": args,
                    "status": resolution["status"],
                    "type": resolution.get("type"),
                    "name": resolution.get("name"),
                    "options": resolution.get("options")
                })
        logger.info(f"Selected tools for prompt '{user_prompt}': {json.dumps(resolved_choices)}")
        return resolved_choices
    except Exception as e:
        logger.error(f"Failed to parse LLM response: {e}")
        logger.error(f"Raw LLM output: {raw}")
        return [{"tool": None, "source": None, "args": {}}]

def extract_result_json(output: str) -> str:
    logger.debug(f"Extracting JSON from tool output: {output[:500]}...")
    match = re.search(r'"Result":\s*(\{.*\})', output, re.DOTALL)
    if match:
        try:
            json_data = json.loads(match.group(1))
            logger.info("Successfully extracted JSON from tool output")
            return json.dumps(json_data, indent=2)
        except Exception as e:
            logger.error(f"Failed to parse JSON in tool output: {e}")
            return match.group(1)
    logger.warning("No 'Result' JSON found in tool output")
    return output

# End of gessing the tools that the llm will be using
# Start the execution of the tools fetching the response from the server and summarizing the response to be user freindly
def execute_tool(tool_name: str, source: str, args: dict) -> dict:
    logger.info(f"Executing tool: {tool_name} (source: {source}, args: {args})")
    result = {"tool": tool_name, "source": source}
    if source == "trello":
        if args:
            args_json = json.dumps(args).replace('"', '\\"')
            cmd = f'npm run start:client {tool_name} "{args_json}"'
        else:
            cmd = f'npm run start:client {tool_name}'
        server_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', "trello-mcp-server"))
        logger.info(f"Running command: {cmd} in {server_dir}")
        try:
            process_result = subprocess.run(
                cmd,
                cwd=server_dir,
                shell=True,
                capture_output=True,
                text=True,
                check=True
            )
            full_output = process_result.stdout + "\n" + process_result.stderr
            logger.info(f"Tool {tool_name} executed successfully")
            result.update({"status": "success", "output": extract_result_json(full_output)})
        except subprocess.CalledProcessError as e:
            logger.error(f"Trello tool {tool_name} failed: {e.stderr}")
            result.update({"status": "error", "output": f"Trello Error: {e.stderr}"})
        except FileNotFoundError:
            logger.error("npm not installed or command not found")
            result.update({"status": "error", "output": "Error: npm not installed or command not found"})
    elif source == "calendar":
        calendar_server_url = "http://localhost:8000/messages"
        tool_call = {"name": tool_name, "arguments": args}
        payload = {"session_id": session_id, "content": {"tool_calls": [tool_call]}}
        logger.info(f"Sending calendar tool request: {tool_call}")
        try:
            response = requests.post(calendar_server_url, json=payload, timeout=10)
            response.raise_for_status()
            result_data = response.json()
            if result_data.get("results") and len(result_data["results"]) > 0:
                tool_result = result_data["results"][0]
                if "error" in tool_result:
                    logger.error(f"Calendar tool {tool_name} error: {tool_result['error']}")
                    result.update({"status": "error", "output": f"Calendar Error: {tool_result['error']}"})
                else:
                    logger.info(f"Calendar tool {tool_name} executed successfully")
                    result.update({"status": "success", "output": json.dumps(tool_result.get("result", {}), indent=2)})
            else:
                logger.error(f"Calendar tool {tool_name} returned no valid result")
                result.update({"status": "error", "output": "Calendar Error: No valid result returned"})
        except Exception as e:
            logger.error(f"Calendar tool {tool_name} failed: {str(e)}")
            result.update({"status": "error", "output": f"Calendar Error: {str(e)}"})
    else:
        logger.error(f"Invalid tool source: {source}")
        result.update({"status": "error", "output": f"Invalid tool source: {source}"})
    return result

def summarize_response(prompt: str, tool_results: list[dict]) -> str:
    combined_output = []
    for result in tool_results:
        output = result["output"]
        tool_name = result.get("tool", "unknown")
        source = result.get("source", "unknown")
        try:
            json.loads(output)
        except json.JSONDecodeError:
            logger.warning(f"Tool output is not valid JSON: {output[:500]}...")
            output = json.dumps({"result": output})
        combined_output.append(f"Tool result ({tool_name} - {source}):\n{output}")
    combined_output_str = "\n\n".join(combined_output)
    logger.info(f"Summarizing tool results for prompt '{prompt}': {combined_output_str[:500]}...")
    llm = ChatOllama(model="llama3", base_url="http://localhost:11434", temperature=0)
    summary_prompt = f"""
The user asked: "{prompt}"
The tools returned:
{combined_output_str}
Summarize this in plain English for the user, combining all tool results into a cohesive response. Ensure the summary is balanced, concise, and informative:
- For Calendar events, include key details like the event title, date, time, and description (if provided).
- For Trello tools, include key details specific to the tool's purpose:
  - For 'get_board', include the board name, description (if available), and status.
  - For 'get_me', include the user's username, full name, and email (if available).
  - For 'get_member', include the member's username and full name.
  - For 'create_card', include the card title, list name, and board name (if available).
  - For 'get_board_lists', list the board name and its lists (list names only).
  - For other Trello tools, include 2-3 key details relevant to the tool's output.
- If a tool fails or returns an error, briefly mention the issue without technical jargon.
"""
    response = llm.invoke(summary_prompt)
    summary = response.content.strip() if hasattr(response, "content") else str(response).strip()
    logger.info(f"Generated summary: {summary[:500]}...")
    return summary
# End of the execution of the tools fetching the response from the server and summarizing the response to be user freindly

# Start of Dev related logs (will be removed when deployed)
def log_prompt(prompt: str):
    sessions_collection.update_one(
        {"_id": session_doc_id},
        {"$push": {"interactions": {
            "prompt": prompt,
            "prompt_time": datetime.now(timezone.utc),
            "response": None,
            "response_time": None,
            "pending_tool": None,
            "pending_type": None,
            "pending_name": None,
            "pending_options": None
        }}}
    )
    logger.info(f"Logged prompt: {prompt}")

def log_response(response_text: str, pending_tool: dict = None, pending_type: str = None, pending_name: str = None, pending_options: list = None):
    update_data = {
        "interactions.$.response": response_text,
        "interactions.$.response_time": datetime.now(timezone.utc),
        "interactions.$.pending_tool": pending_tool,
        "interactions.$.pending_type": pending_type,
        "interactions.$.pending_name": pending_name,
        "interactions.$.pending_options": pending_options
    }
    sessions_collection.update_one(
        {"_id": session_doc_id, "interactions.response": None},
        {"$set": update_data}
    )
    logger.info(f"Logged response: {response_text[:500]}...")
    
# End of Dev related logs (will be removed when deployed)
# Kill session when its over prompt to kill is "quit"
def end_session():
    sessions_collection.update_one(
        {"_id": session_doc_id},
        {"$set": {"ended_at": datetime.now(timezone.utc)}}
    )
    logger.info(f"Ended session: {session_id}")

def main():
    logger.info("Fetching and storing Trello boards at startup")
    boards = fetch_and_store_boards()
    if boards:
        logger.info(f"Successfully fetched and stored {len(boards)} boards")
    else:
        logger.warning("No boards fetched at startup")
    while True:
        pending_interaction = sessions_collection.find_one(
            {"_id": session_doc_id, "interactions.response": {"$regex": "Please enter the.*ID to use.*"}},
            {"interactions.$": 1}
        )
        if pending_interaction and "interactions" in pending_interaction and pending_interaction["interactions"]:
            last_interaction = pending_interaction["interactions"][0]
            pending_tool = last_interaction.get("pending_tool")
            if isinstance(pending_tool, dict) and pending_tool.get("tool") and last_interaction.get("pending_type") and last_interaction.get("pending_options"):
                user_input = input("Enter the ID to use (or number of the option, or 'quit' to exit): ")
                if user_input.lower() == "quit":
                    end_session()
                    print("Session ended.")
                    break
                logger.info(f"User selected ID: {user_input}")
                pending_type = last_interaction["pending_type"]
                pending_name = last_interaction["pending_name"]
                pending_options = last_interaction["pending_options"]
                valid_ids = [opt["id"] for opt in pending_options]
                selected_id = user_input
                if user_input.isdigit() and 1 <= int(user_input) <= len(pending_options):
                    selected_id = pending_options[int(user_input) - 1]["id"]
                    logger.info(f"Converted option number {user_input} to ID: {selected_id}")
                if selected_id not in valid_ids:
                    response_text = f"Invalid ID '{user_input}'. Please choose one of the listed IDs: {', '.join(valid_ids)}."
                    print("\nResponse:")
                    print(response_text)
                    log_response(response_text, pending_tool, pending_type, pending_name, pending_options)
                    continue
                resolved_args = pending_tool["args"].copy()
                if pending_type == "board":
                    resolved_args["boardId"] = selected_id
                    resolution = resolve_names_to_ids(resolved_args, session_id)
                    if resolution["status"] == "success":
                        tool_results = [execute_tool(pending_tool["tool"], "trello", resolution["args"])]
                        response_text = summarize_response(last_interaction["prompt"], tool_results)
                        print("\nResponse:")
                        print(response_text)
                        log_response(response_text)
                    elif resolution["status"] == "disambiguate":
                        response_text = f"Multiple {resolution['type']}s named '{resolution['name']}' found:\n"
                        for i, opt in enumerate(resolution["options"], 1):
                            response_text += f"{i}. ID: {opt['id']}, Name: {opt['name']}\n"
                        response_text += "Please enter the ID to use (or number of the option):"
                        print("\nResponse:")
                        print(response_text)
                        log_response(response_text, {
                            "tool": pending_tool["tool"],
                            "source": "trello",
                            "args": resolution["args"]
                        }, resolution["type"], resolution["name"], resolution["options"])
                    else:
                        print("\nResponse:")
                        print(resolution["message"])
                        log_response(resolution["message"])
                    continue
                else:  # pending_type == "list"
                    resolved_args["listId"] = selected_id
                tool_results = [execute_tool(pending_tool["tool"], "trello", resolved_args)]
                response_text = summarize_response(last_interaction["prompt"], tool_results)
                print("\nResponse:")
                print(response_text)
                log_response(response_text)
                continue
        user_input = input("Enter your query (or type 'quit' to exit): ")
        if user_input.lower() == "quit":
            end_session()
            print("Session ended.")
            break
        logger.info(f"User prompt: {user_input}")
        if not is_task_management_related_llm(user_input):
            response_text = "I am an AI dedicated to Trello or Calendar management. Please ask about Trello or Calendar-related actions."
            print("\nResponse:")
            print(response_text)
            log_prompt(user_input)
            log_response(response_text)
            continue
        log_prompt(user_input)
        tools = load_all_tools()
        if not tools:
            print("No tools available. Check your tools.json and calendar-tools.json files.")
            continue
        tool_choices = guess_tool_from_prompt(user_input, tools, session_id)
        print("\nLLM Suggested Tools and Arguments:")
        print(json.dumps(tool_choices, indent=2))
        if not tool_choices or all(choice.get("tool") is None for choice in tool_choices):
            print("Could not determine which tool(s) to use.")
            log_response("Could not determine which tool(s) to use.")
            continue
        tool_results = []
        for choice in tool_choices:
            if choice.get("status") == "disambiguate":
                response_text = f"Multiple {choice['type']}s named '{choice['name']}' found:\n"
                for i, opt in enumerate(choice["options"], 1):
                    response_text += f"{i}. ID: {opt['id']}, Name: {opt['name']}\n"
                response_text += "Please enter the ID to use (or number of the option):"
                print("\nResponse:")
                print(response_text)
                log_response(response_text, {
                    "tool": choice["tool"],
                    "source": choice["source"],
                    "args": choice["args"]
                }, choice["type"], choice["name"], choice["options"])
                break
            elif choice.get("status") == "error":
                print("\nResponse:")
                print(choice["message"])
                log_response(choice["message"])
                break
            elif choice.get("tool") and choice.get("source"):
                tool_results.append(execute_tool(choice["tool"], choice["source"], choice["args"]))
        if tool_results:
            response_text = summarize_response(user_input, tool_results)
            print("\nResponse:")
            print(response_text)
            log_response(response_text)
        
if __name__ == "__main__":
    main()