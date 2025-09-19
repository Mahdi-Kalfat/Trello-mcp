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
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Setup logging with minimal logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('llm_agent.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# MongoDB setup
mongo_client = MongoClient("mongodb://localhost:27017", serverSelectionTimeoutMS=5000)
db = mongo_client["trello_mcp"]
sessions_collection = db["sessions"]

def select_or_create_session():
    print("\n--- Session Selection ---")
    recent_sessions = list(sessions_collection.find({}, {"session_id": 1, "started_at": 1}).sort("started_at", -1).limit(5))
    if recent_sessions:
        print("Recent sessions:")
        for i, sess in enumerate(recent_sessions, 1):
            started = sess.get("started_at")
            started_str = started.strftime('%Y-%m-%d %H:%M:%S') if started else "Unknown"
            print(f"{i}. ID: {sess['session_id']} (Started: {started_str})")
        print("Enter a session ID to resume, or press Enter to start a new session.")
        chosen_id = input("Session ID: ").strip()
        if chosen_id:
            session_doc = sessions_collection.find_one({"session_id": chosen_id})
            if session_doc:
                print(f"Resuming session {chosen_id}.")
                return session_doc["session_id"], session_doc["_id"]
            else:
                print("Session ID not found. Starting a new session.")
    # Create new session
    new_id = str(uuid.uuid4())
    doc_id = sessions_collection.insert_one({
        "session_id": new_id,
        "started_at": datetime.now(timezone.utc),
        "interactions": [],
        "cache": []
    }).inserted_id
    print(f"Started new session: {new_id}")
    return new_id, doc_id


# Session globals
session_id = None
session_doc_id = None

# Start of board and list parsing and caching
def parse_boards_output(output: str) -> str:
    if not output.strip():
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
        return json.dumps({"result": []})
    try:
        parsed = json.loads(cleaned_output)
        boards = parsed["result"] if isinstance(parsed, dict) and "result" in parsed else parsed
        boards_cache = [
            {"id": board["id"], "name": board["name"]}
            for board in boards
            if isinstance(board, dict) and "id" in board and "name" in board
        ]
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
                return json.dumps({"result": boards_cache})
            except json.JSONDecodeError:
                pass
        return json.dumps({"result": []})

def run_get_boards() -> str:
    server_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'trello-mcp-server'))
    if not os.path.isdir(server_dir):
        return f"Error: Directory {server_dir} does not exist or is not a directory."
    try:
        cmd = 'npm run start:client -- get_boards'
        logger.info(f"Executing command: {cmd}")
        result = subprocess.run(
            cmd,
            cwd=server_dir,
            shell=True,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout + "\n" + result.stderr
    except subprocess.CalledProcessError as e:
        return f"Error executing get_boards: {e.stderr}"
    except FileNotFoundError:
        return "Error: npm not installed or command not found"

def parse_board_lists_output(output: str) -> str:
    if not output.strip():
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
        return json.dumps({"result": []})
    try:
        parsed = json.loads(cleaned_output)
        lists = parsed["result"] if isinstance(parsed, dict) and "result" in parsed else parsed
        lists_cache = [
            {"id": lst["id"], "name": lst["name"]}
            for lst in lists
            if isinstance(lst, dict) and "id" in lst and "name" in lst
        ]
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
                return json.dumps({"result": lists_cache})
            except json.JSONDecodeError:
                pass
        return json.dumps({"result": []})

def run_get_board_lists(board_id: str) -> str:
    server_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'trello-mcp-server'))
    if not os.path.isdir(server_dir):
        return f"Error: Directory {server_dir} does not exist or is not a directory."
    args = {"boardId": board_id}
    args_json = json.dumps(args)
    cmd = f'npm run start:client -- get_board_lists "{args_json}"'
    logger.info(f"Executing command: {cmd}")
    try:
        result = subprocess.run(
            cmd,
            cwd=server_dir,
            shell=True,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout + "\n" + result.stderr
    except subprocess.CalledProcessError as e:
        return f"Error executing get_board_lists: {e.stderr}"
    except FileNotFoundError:
        return "Error: npm not installed or command not found"

def fetch_and_store_boards() -> list:
    raw_boards_output = run_get_boards()
    if "Error" in raw_boards_output:
        return []
    boards_result = parse_boards_output(raw_boards_output)
    try:
        boards = json.loads(boards_result)["result"]
    except json.JSONDecodeError:
        return []
    output = []
    for board in boards:
        board_data = {"id": board["id"], "name": board["name"], "lists": []}
        raw_lists_output = run_get_board_lists(board["id"])
        if "Error" in raw_lists_output:
            pass
        else:
            lists_result = parse_board_lists_output(raw_lists_output)
            try:
                lists = json.loads(lists_result)["result"]
                board_data["lists"] = lists
            except json.JSONDecodeError:
                pass
        output.append(board_data)
    try:
        sessions_collection.update_one(
            {"session_id": session_id},
            {"$set": {"cache": output, "cache_updated_at": datetime.now(timezone.utc)}},
            upsert=True
        )
        logger.info(f"Parsed and saved {len(output)} boards with lists: {json.dumps(output)}")
    except Exception:
        pass
    return output

# End of board and list parsing and caching
# Start name-to-ID resolution
def resolve_names_to_ids(args: dict, session_id: str) -> dict:
    resolved_args = args.copy()
    board_name = args.get("boardId")
    list_name = args.get("listId")
    try:
        session_doc = sessions_collection.find_one({"session_id": session_id}, {"_id": 0, "cache": 1})
        if not session_doc or "cache" not in session_doc:
            return {"status": "error", "message": "No board/list cache available."}
        cache = session_doc["cache"]
    except Exception:
        return {"status": "error", "message": "Failed to access board/list cache."}
    if board_name and not re.match(r'^[0-9a-f]{24}$', board_name):
        matching_boards = [board for board in cache if board.get("name").lower() == board_name.lower()]
        if not matching_boards:
            return {"status": "error", "message": f"No board found with name '{board_name}'."}
        elif len(matching_boards) > 1:
            return {
                "status": "disambiguate",
                "type": "board",
                "name": board_name,
                "options": [{"id": board["id"], "name": board["name"]} for board in matching_boards],
                "args": args
            }
        else:
            resolved_args["boardId"] = matching_boards[0]["id"]
    if list_name and not re.match(r'^[0-9a-f]{24}$', list_name) and "boardId" in resolved_args:
        board_id = resolved_args["boardId"]
        matching_board = next((board for board in cache if board["id"] == board_id), None)
        if not matching_board:
            return {"status": "error", "message": f"Board ID {board_id} not found in cache."}
        matching_lists = [lst for lst in matching_board.get("lists", []) if lst.get("name").lower() == list_name.lower()]
        if not matching_lists:
            return {"status": "error", "message": f"No list found with name '{list_name}' in board."}
        elif len(matching_lists) > 1:
            return {
                "status": "disambiguate",
                "type": "list",
                "name": list_name,
                "options": [{"id": lst["id"], "name": lst["name"]} for lst in matching_lists],
                "args": args
            }
        else:
            resolved_args["listId"] = matching_lists[0]["id"]
    return {"status": "success", "args": resolved_args}

# End name-to-ID resolution
# Start load tools
def load_all_tools() -> list[dict]:
    tools = []
    trello_tools_json_path = os.path.join(os.path.dirname(__file__), 'tools.json')
    try:
        with open(trello_tools_json_path, 'r', encoding='utf-8') as f:
            trello_tools = json.load(f)
            for tool in trello_tools:
                tool['source'] = 'trello'
            tools.extend(trello_tools)
    except Exception:
        pass
    calendar_tools_json_path = os.path.join(os.path.dirname(__file__), 'calendar-tools.json')
    try:
        with open(calendar_tools_json_path, 'r', encoding='utf-8') as f:
            calendar_tools = json.load(f)
            for tool in calendar_tools:
                tool['source'] = 'calendar'
            tools.extend(calendar_tools)
    except Exception:
        pass
    return tools

# End load tools
# Start guess tool
def guess_tool_from_prompt(user_prompt: str, tools: list[dict]) -> list[dict]:
    tool_descriptions = "\n\n".join([
        f"Tool name: {tool['name']}\nSource: {tool['source']}\nDescription: {tool['description']}\nInput Schema:\n{json.dumps(tool.get('inputSchema') or tool.get('parameters'), indent=2)}"
        for tool in tools
    ])
    prompt = f"""
You are a tool selection assistant for a task management system that supports Trello (task, board, list, member, card, checklist, label management), Calendar (event scheduling and management), and potentially other services (e.g., Gmail in the future). Your job is to select the BEST matching tool(s) for a user request from the provided list of tools, based on the query's intent, tool names, descriptions, and schemas.

Respond with a JSON array of objects, where each object has one of the following formats:
1. Successful tool selection:
{{
  "tool": "tool_name",
  "source": "trello or calendar",
  "args": {{ ... }}
}}
2. Disambiguation needed (multiple boards/lists with the same name):
{{
  "status": "disambiguate",
  "type": "board or list",
  "name": "name",
  "options": [{{"id": "id1", "name": "name1"}}, ...],
  "tool": "tool_name",
  "source": "trello",
  "args": {{ ... }}
}}
3. Error (e.g., no board/list found):
{{
  "status": "error",
  "message": "error message"
}}

- If only one tool is needed, return a single-item array.
- If no tool matches exactly, return an empty array.
- For Trello tools, if `boardId` or `listId` in `args` is a name (not a 24-character hex ID), resolve it to an ID using the session's cached board/list data:
  - If a unique ID is found, replace the name with the ID in `args`.
  - If multiple IDs are found for the same name, return a disambiguation response with `status: "disambiguate"`.
  - If no ID is found, return an error response with `status: "error"`.

**Instructions**:
- **Match Exact Tool Names**: Use the exact tool names from the available tools list. Do not invent tool names.
- **Use Descriptions and Schemas**: Match the user’s intent to the tool’s description and input schema.
- **Handle Typos and Synonyms**:
  - Map 'add', 'create', or 'make' to tools like `create_card`, `create_list`, `create_board`, or `add_event`.
  - Map 'get', 'show', 'list', or 'information about' to tools like `get_board`, `get_card`, `get_me`, or `list_today_events`.
  - Map 'edit' or 'update' to tools like `update_card`, `update_board`, or `edit_event`.
  - Map 'delete' or 'remove' to tools like `delete_card`, `delete_board`, or `delete_event`.
- **Trello-Specific Guidance**:
  - For queries about creating a card, use `create_card` with `listId` and `name` (and `boardId` if provided).
  - For queries about board information, use `get_board` with `boardId`.
  - For listing lists on a board, use `get_board_lists` with `boardId`.
  - For user information, use `get_me` for the authenticated user or `get_member` for another user.
- **Calendar-Specific Guidance**:
  - For event creation, use `add_event` with `userId`, `title`, `date`, `time`, and optional `description`.
  - For listing events, use `list_today_events` or `list_all_events` based on the time scope.
  - For event updates or deletion, use `edit_event` or `delete_event` with `eventId` and `userId`.
- **Input Validation**: Ensure `args` match the tool’s required input schema. Use default values (e.g., `userId`: "current_user" for Calendar tools) when not specified.

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
User: list my events for today
Output: [{{
  "tool": "list_today_events",
  "source": "calendar",
  "args": {{ "userId": "current_user" }}
}}]

🧠 Example 3:
User: create a card in the board test-mcp under list hello named created from llm
Output: [{{
  "tool": "create_card",
  "source": "trello",
  "args": {{ "boardId": "686b7c8622f3834294acc4eb", "listId": "687653cc69e8c963d9eef70e", "name": "created from llm" }}
}}]
(Note: Assumes unique board/list IDs; if multiple lists named 'hello', return disambiguation)

🧠 Example 4:
User: create a card in the board test-mcp under list hello named created from llm
Output: [{{
  "status": "disambiguate",
  "type": "list",
  "name": "hello",
  "options": [
    {{"id": "687653cc69e8c963d9eef70e", "name": "hello"}},
    {{"id": "687a5448d31d683f84a57856", "name": "hello"}}
  ],
  "tool": "create_card",
  "source": "trello",
  "args": {{ "name": "created from llm" , "listId": "hello",  }}
}}]

🧠 Example 5:
User: create a list in board nonexistent named new list
Output: [{{
  "status": "error",
  "message": "No board found with name 'nonexistent'."
}}]

Now answer the following:
User: {user_prompt}
ONLY respond with a valid JSON array. No explanations.
"""
    llm = ChatOllama(model="llama3", base_url="http://localhost:11434", temperature=0)
    response = llm.invoke(prompt)
    try:
        raw = response.content if hasattr(response, "content") else str(response)
        logger.info(f"Prompt: {user_prompt}, Guessed tool: {raw}")
        match = re.search(r'\[.*\]', raw, re.DOTALL)
        if not match:
            return [{"tool": None, "source": None, "args": {}}]
        json_str = match.group(0)
        tool_choices = json.loads(json_str)
        if not isinstance(tool_choices, list):
            return [{"tool": None, "source": None, "args": {}}]
        # Resolve board/list names to IDs for Trello tools
        resolved_choices = []
        for choice in tool_choices:
            if choice.get("source") == "trello" and choice.get("tool"):
                args = choice.get("args", {})
                # Access session cache
                try:
                    session_doc = sessions_collection.find_one({"session_id": session_id}, {"_id": 0, "cache": 1})
                    if not session_doc or "cache" not in session_doc:
                        resolved_choices.append({
                            "status": "error",
                            "message": "No board/list cache available."
                        })
                        continue
                    cache = session_doc["cache"]
                except Exception:
                    resolved_choices.append({
                        "status": "error",
                        "message": "Failed to access board/list cache."
                    })
                    continue
                # Resolve boardId
                board_name = args.get("boardId")
                if board_name and not re.match(r'^[0-9a-f]{24}$', board_name):
                    matching_boards = [board for board in cache if board.get("name").lower() == board_name.lower()]
                    if not matching_boards:
                        resolved_choices.append({
                            "status": "error",
                            "message": f"No board found with name '{board_name}'."
                        })
                        continue
                    elif len(matching_boards) > 1:
                        resolved_choices.append({
                            "status": "disambiguate",
                            "type": "board",
                            "name": board_name,
                            "options": [{"id": board["id"], "name": board["name"]} for board in matching_boards],
                            "tool": choice["tool"],
                            "source": choice["source"],
                            "args": args
                        })
                        continue
                    else:
                        args["boardId"] = matching_boards[0]["id"]
                # Resolve listId
                list_name = args.get("listId")
                if list_name and not re.match(r'^[0-9a-f]{24}$', list_name) and "boardId" in args:
                    board_id = args["boardId"]
                    matching_board = next((board for board in cache if board["id"] == board_id), None)
                    if not matching_board:
                        resolved_choices.append({
                            "status": "error",
                            "message": f"Board ID {board_id} not found in cache."
                        })
                        continue
                    matching_lists = [lst for lst in matching_board.get("lists", []) if lst.get("name").lower() == list_name.lower()]
                    if not matching_lists:
                        resolved_choices.append({
                            "status": "error",
                            "message": f"No list found with name '{list_name}' in board."
                        })
                        continue
                    elif len(matching_lists) > 1:
                        resolved_choices.append({
                            "status": "disambiguate",
                            "type": "list",
                            "name": list_name,
                            "options": [{"id": lst["id"], "name": lst["name"]} for lst in matching_lists],
                            "tool": choice["tool"],
                            "source": choice["source"],
                            "args": args
                        })
                        continue
                    else:
                        args["listId"] = matching_lists[0]["id"]
                resolved_choices.append({
                    "tool": choice["tool"],
                    "source": choice["source"],
                    "args": args
                })
            else:
                resolved_choices.append(choice)
        return resolved_choices
    except Exception as e:
        logger.info(f"Prompt: {user_prompt}, Error parsing tool: {e}")
        return [{"tool": None, "source": None, "args": {}}]

# End guess tool
# Start tool execution
def extract_result_json(output: str) -> str:
    match = re.search(r'"Result":\s*(\{.*\})', output, re.DOTALL)
    if match:
        try:
            json_data = json.loads(match.group(1))
            return json.dumps(json_data, indent=2)
        except Exception:
            return match.group(1)
    return output

def execute_tool(tool_name: str, source: str, args: dict) -> dict:
    result = {"tool": tool_name, "source": source}
    if source == "trello":
        server_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', "trello-mcp-server"))
        if not os.path.isdir(server_dir):
            result.update({"status": "error", "output": f"Error: Directory {server_dir} does not exist or is not a directory."})
            return result
        # Construct command with proper quoting for PowerShell
        if args:
            args_json = json.dumps(args)
            cmd = f'npm run start:client -- {tool_name} "{args_json}"'
        else:
            cmd = f'npm run start:client -- {tool_name}'
        logger.info(f"Executing command: {cmd}")
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
            result.update({"status": "success", "output": extract_result_json(full_output)})
        except subprocess.CalledProcessError as e:
            result.update({"status": "error", "output": f"Trello Error: {e.stderr}"})
        except FileNotFoundError:
            result.update({"status": "error", "output": "Error: npm not installed or command not found"})
    elif source == "calendar":
        calendar_server_url = "http://localhost:8000/messages"
        tool_call = {"name": tool_name, "arguments": args}
        payload = {"session_id": session_id, "content": {"tool_calls": [tool_call]}}
        try:
            response = requests.post(calendar_server_url, json=payload, timeout=10)
            response.raise_for_status()
            result_data = response.json()
            if result_data.get("results") and len(result_data["results"]) > 0:
                tool_result = result_data["results"][0]
                if "error" in tool_result:
                    result.update({"status": "error", "output": f"Calendar Error: {tool_result['error']}"})
                else:
                    result.update({"status": "success", "output": json.dumps(tool_result.get("result", {}), indent=2)})
            else:
                result.update({"status": "error", "output": "Calendar Error: No valid result returned"})
        except Exception as e:
            result.update({"status": "error", "output": f"Calendar Error: {str(e)}"})
    else:
        result.update({"status": "error", "output": f"Invalid tool source: {source}"})
    return result

# End tool execution
# Start response summarization
def summarize_response(prompt: str, tool_results: list[dict]) -> str:
    combined_output = []
    for result in tool_results:
        output = result["output"]
        try:
            json.loads(output)
        except json.JSONDecodeError:
            output = json.dumps({"result": output})
        combined_output.append(f"Tool result ({result['tool']} - {result['source']}):\n{output}")
    combined_output_str = "\n\n".join(combined_output)
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
    logger.info(f"Prompt: {prompt}, Response: {summary}")
    return summary

# End response summarization
# Start logging
def log_prompt(prompt: str, session_doc_id):
    sessions_collection.update_one(
        {"_id": session_doc_id},
        {
            "$push": {"interactions": {
                "prompt": prompt,
                "prompt_time": datetime.now(timezone.utc),
                "response": None,
                "response_time": None,
                "pending_tool": None,
                "pending_type": None,
                "pending_name": None,
                "pending_options": None
            }},
            "$set": {"cache_updated_at": datetime.now(timezone.utc)}
        }
    )
    logger.info(f"Prompt: {prompt}")

def log_response(response_text: str, session_doc_id, pending_tool: dict = None, pending_type: str = None, pending_name: str = None, pending_options: list = None):
    update_data = {
        "interactions.$.response": response_text,
        "interactions.$.response_time": datetime.now(timezone.utc),
        "interactions.$.pending_tool": pending_tool,
        "interactions.$.pending_type": pending_type,
        "interactions.$.pending_name": pending_name,
        "interactions.$.pending_options": pending_options,
        "cache_updated_at": datetime.now(timezone.utc)
    }
    sessions_collection.update_one(
        {"_id": session_doc_id, "interactions.response": None},
        {"$set": update_data}
    )
    logger.info(f"Response: {response_text}")

# End logging
# End session
def end_session():
    sessions_collection.update_one(
        {"_id": session_doc_id},
        {"$set": {"ended_at": datetime.now(timezone.utc)}}
    )

def process_prompt(user_input: str, session_id, session_doc_id) -> str:
    # Retrieve session chat history
    session_doc = sessions_collection.find_one({"_id": session_doc_id}, {"interactions": 1})
    chat_history = session_doc.get("interactions", []) if session_doc else []
    history_str = "\n".join([
        f"User: {msg['prompt']}\nAssistant: {msg['response']}" for msg in chat_history if msg.get('prompt') and msg.get('response')
    ])
    log_prompt(user_input, session_doc_id)
    # Let LLM decide if the user wants a summary, chat info, or tool action
    llm = ChatOllama(model="llama3", base_url="http://localhost:11434", temperature=0)
    meta_prompt = f"""
You are a smart assistant for a chat-based productivity system. Here is the chat history so far:
{history_str}

The user just sent: "{user_input}"

Decide what the user wants:
- If the user is asking for a summary, recap, or information about the chat, respond with a summary or relevant info directly.
- If the user is asking for a tool action (e.g., Trello, Calendar, etc.), respond with: TOOL_ACTION_NEEDED
Only respond with a summary or TOOL_ACTION_NEEDED. Do not perform any tool actions yet.
"""
    meta_response = llm.invoke(meta_prompt)
    meta_content = meta_response.content.strip() if hasattr(meta_response, "content") else str(meta_response).strip()
    if meta_content != "TOOL_ACTION_NEEDED":
        log_response(meta_content, session_doc_id)
        return meta_content
    # If tool action is needed, proceed as before
    tools = load_all_tools()
    if not tools:
        return "No tools available. Check your tools.json and calendar-tools.json files."
    tool_choices = guess_tool_from_prompt(
        f"Chat history:\n{history_str}\n\nCurrent user prompt: {user_input}",
        tools
    )
    if not tool_choices or all(choice.get("tool") is None for choice in tool_choices):
        log_response("Could not determine which tool(s) to use.", session_doc_id)
        return "Could not determine which tool(s) to use."
    resolved_tool_choices = []
    for choice in tool_choices:
        if choice.get("source") == "trello" and choice.get("tool"):
            args = choice.get("args", {})
            if choice.get("tool") == "create_card" and "name" not in args:
                args["name"] = "Untitled Card"
            resolution = resolve_names_to_ids(args, session_id)
            if resolution["status"] == "success":
                resolved_tool_choices.append({
                    "tool": choice["tool"],
                    "source": choice["source"],
                    "args": resolution["args"]
                })
            elif resolution["status"] == "disambiguate":
                response_text = f"Multiple {resolution['type']}s named '{resolution['name']}' found:\n"
                for i, opt in enumerate(resolution["options"], 1):
                    response_text += f"{i}. ID: {opt['id']}, Name: {opt['name']}\n"
                response_text += "Please enter the ID to use (or number of the option):"
                log_response(response_text, session_doc_id, {
                    "tool": choice["tool"],
                    "source": choice["source"],
                    "args": resolution["args"]
                }, resolution["type"], resolution["name"], resolution["options"])
                return response_text
            else:
                log_response(resolution["message"], session_doc_id)
                return resolution["message"]
        else:
            resolved_tool_choices.append(choice)
    if not resolved_tool_choices:
        return "Could not resolve tool choices."
    tool_results = []
    for choice in resolved_tool_choices:
        if choice.get("tool") and choice.get("source"):
            result = execute_tool(choice["tool"], choice["source"], choice.get("args", {}))
            tool_results.append({
                "tool": choice["tool"],
                "source": choice["source"],
                "output": result["output"],
                "status": result["status"]
            })
        else:
            tool_results.append({
                "tool": None,
                "source": None,
                "output": "Invalid tool or source",
                "status": "error"
            })
    response_text = summarize_response(
        f"Chat history:\n{history_str}\n\nCurrent user prompt: {user_input}",
        tool_results
    )
    log_response(response_text, session_doc_id)
    return response_text

# --- FastAPI setup ---
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/chat")
async def chat(request: Request):
    data = await request.json()
    user_input = data.get("prompt", "")
    incoming_session_id = data.get("session_id")
    session_id = None
    session_doc_id = None
    # If session_id is missing, None, or 'null', create a new session
    if (not incoming_session_id) or incoming_session_id is None or incoming_session_id == 'null':
        session_id = str(uuid.uuid4())
        session_doc_id = sessions_collection.insert_one({
            "session_id": session_id,
            "started_at": datetime.now(timezone.utc),
            "interactions": [],
            "cache": []
        }).inserted_id
    else:
        session_doc = sessions_collection.find_one({"session_id": incoming_session_id})
        if session_doc:
            session_id = session_doc["session_id"]
            session_doc_id = session_doc["_id"]
        else:
            # If session_id not found, create a new session with that ID
            session_id = incoming_session_id
            session_doc_id = sessions_collection.insert_one({
                "session_id": session_id,
                "started_at": datetime.now(timezone.utc),
                "interactions": [],
                "cache": []
            }).inserted_id
    if not user_input:
        return {"response": "No prompt provided.", "session_id": session_id}
    response_text = process_prompt(user_input, session_id, session_doc_id)
    return {"response": response_text, "session_id": session_id}

# Main function
def main():
    fetch_and_store_boards()
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
                pending_type = last_interaction["pending_type"]
                pending_name = last_interaction["pending_name"]
                pending_options = last_interaction["pending_options"]
                valid_ids = [opt["id"] for opt in pending_options]
                selected_id = user_input
                if user_input.isdigit() and 1 <= int(user_input) <= len(pending_options):
                    selected_id = pending_options[int(user_input) - 1]["id"]
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
                        tool_results = [execute_tool(pending_tool["tool"], pending_tool["source"], resolution["args"])]
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
                            "source": pending_tool["source"],
                            "args": resolution["args"]
                        }, resolution["type"], resolution["name"], resolution["options"])
                    else:
                        print("\nResponse:")
                        print(resolution["message"])
                        log_response(resolution["message"])
                    continue
                else:  # pending_type == "list"
                    resolved_args["listId"] = selected_id
                tool_results = [execute_tool(pending_tool["tool"], pending_tool["source"], resolved_args)]
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
        log_prompt(user_input)
        tools = load_all_tools()
        if not tools:
            print("No tools available. Check your tools.json and calendar-tools.json files.")
            continue
        tool_choices = guess_tool_from_prompt(user_input, tools)
        print("\nLLM Suggested Tools and Arguments:")
        print(json.dumps(tool_choices, indent=2))
        if not tool_choices or all(choice.get("tool") is None for choice in tool_choices):
            print("Could not determine which tool(s) to use.")
            log_response("Could not determine which tool(s) to use.")
            continue
        # Resolve board/list names to IDs
        resolved_tool_choices = []
        for choice in tool_choices:
            if choice.get("source") == "trello" and choice.get("tool"):
                args = choice.get("args", {})
                if choice.get("tool") == "create_card" and "name" not in args:
                    args["name"] = "Untitled Card"
                resolution = resolve_names_to_ids(args, session_id)
                if resolution["status"] == "success":
                    resolved_tool_choices.append({
                        "tool": choice["tool"],
                        "source": choice["source"],
                        "args": resolution["args"]
                    })
                elif resolution["status"] == "disambiguate":
                    response_text = f"Multiple {resolution['type']}s named '{resolution['name']}' found:\n"
                    for i, opt in enumerate(resolution["options"], 1):
                        response_text += f"{i}. ID: {opt['id']}, Name: {opt['name']}\n"
                    response_text += "Please enter the ID to use (or number of the option):"
                    print("\nResponse:")
                    print(response_text)
                    log_response(response_text, {
                        "tool": choice["tool"],
                        "source": choice["source"],
                        "args": resolution["args"]
                    }, resolution["type"], resolution["name"], resolution["options"])
                    resolved_tool_choices = []
                    break
                else:
                    print("\nResponse:")
                    print(resolution["message"])
                    log_response(resolution["message"])
                    resolved_tool_choices = []
                    break
            else:
                resolved_tool_choices.append(choice)
        if not resolved_tool_choices:
            continue
        tool_results = []
        for choice in resolved_tool_choices:
            if choice.get("tool") and choice.get("source"):
                result = execute_tool(choice["tool"], choice["source"], choice.get("args", {}))
                tool_results.append({
                    "tool": choice["tool"],
                    "source": choice["source"],
                    "output": result["output"],
                    "status": result["status"]
                })
            else:
                tool_results.append({
                    "tool": None,
                    "source": None,
                    "output": "Invalid tool or source",
                    "status": "error"
                })
        response_text = summarize_response(user_input, tool_results)
        print("\nResponse:")
        print(response_text)
        log_response(response_text)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "serve":
        fetch_and_store_boards()
        # In server mode, do not select/create session; rely on session_id from UI
        uvicorn.run(app, host="0.0.0.0", port=8001)  # Changed port from 8080 to 8001
    else:
        # In CLI mode, prompt for session selection
        session_id, session_doc_id = select_or_create_session()
        main()