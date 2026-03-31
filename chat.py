from langchain_ollama import ChatOllama
from langchain.tools import tool
from langchain.agents import create_agent
from langchain_core.messages import SystemMessage
from ddgs import DDGS
import os
import json

model = ChatOllama(model="llama3.2:3b")

# --- Define Tools ---
@tool
def calculate(expression: str) -> str:
    """Useful for math calculations. Input should be a math expression like 2+2"""
    try:
        return str(eval(expression))
    except:
        return "Invalid calculation"

@tool
def web_search(query: str) -> str:
    """Search the web for current information. Input should be a search query."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
            if not results:
                return "No results found"
            output = ""
            for r in results:
                output += f"Title: {r['title']}\n"
                output += f"Summary: {r['body']}\n\n"
            return output
    except Exception as e:
        return f"Search failed: {str(e)}"

@tool
def read_file(filepath: str) -> str:
    """Reads and returns the content of a file. Input should be a full file path."""
    try:
        with open(filepath, "r") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"

@tool
def write_file(input: str) -> str:
    """Writes content to a file. Input should be in format: filepath|content"""
    try:
        filepath, content = input.split("|", 1)
        with open(filepath.strip(), "w") as f:
            f.write(content.strip())
        return f"Successfully wrote to {filepath}"
    except Exception as e:
        return f"Error writing file: {str(e)}"

@tool
def list_files(folder: str) -> str:
    """Lists all files in a folder. Input should be a folder path."""
    try:
        files = os.listdir(folder)
        return "\n".join(files) if files else "Folder is empty"
    except Exception as e:
        return f"Error listing files: {str(e)}"

tools = [calculate, web_search, read_file, write_file, list_files]

# --- Create Agent ---
agent = create_agent(model=model, tools=tools)

# --- Memory File ---
MEMORY_FILE = "memory.json"

def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    return []

def save_memory(history):
    # Only save plain dicts (user/assistant messages), skip SystemMessage objects
    saveable = [m for m in history if isinstance(m, dict)]
    with open(MEMORY_FILE, "w") as f:
        json.dump(saveable, f, indent=2)

# --- System Prompt ---
system_prompt = SystemMessage(content="""
You are a helpful assistant named Lila.
Keep your answers SHORT and CONCISE.
Get straight to the point.
No unnecessary explanation unless asked.
""")

# --- Load memory and prepend system prompt ---
conversation_history = [system_prompt] + load_memory()

# --- Interactive Chat Loop ---
print("🤖 Lila is ready! (type 'exit' to quit, 'clear memory' to reset)\n")

while True:
    user_input = input("You: ")

    if user_input.lower() == "exit":
        print("Bye! 👋")
        break

    if user_input.lower() == "clear memory":
        conversation_history = [system_prompt]
        save_memory([])
        print("🧹 Memory cleared!\n")
        continue

    if user_input.strip() == "":
        continue

    # Add user message to history
    conversation_history.append({"role": "user", "content": user_input})

    # Send full history to agent
    response = agent.invoke({"messages": conversation_history})

    ai_reply = response["messages"][-1].content

    # Add AI reply to history
    conversation_history.append({"role": "assistant", "content": ai_reply})

    # Save only plain dict messages to file
    save_memory(conversation_history)

    print(f"\nLila: {ai_reply}\n")