from autogen_core.models import UserMessage
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
from dotenv import load_dotenv
from typing import List, Sequence
import asyncio
import os


# Note: This example uses mock tools instead of real APIs for demonstration purposes
import glob
import ast
import aiofiles
async def search_blueprint_tool(query: str) -> str:
    input_dir = os.path.join(os.getcwd(), "input_files")
    file_paths = [f for f in glob.glob(f"{input_dir}/**/*.txt", recursive=True)]
    if not file_paths:
        return "No blueprint files found."

    prompt = f"""
You are a system blueprint search agent.
Given the following query:
---
{query}
---
Here is a list of available blueprint files:
{chr(10).join(file_paths)}
Which files are most relevant to answering the query? Return a comma separated list of file paths.
"""
    print(prompt)
    from autogen_core.models import UserMessage
    response = await model_client.create(messages=[UserMessage(role="user", content=prompt, source="user")])
    # Extract content and clean up code block and raw string prefixes
    print(response.content)    # Remove code block markers
    content = response.content.split(",")
    print("Chose files:")
    print("\n".join(content))
    contents = []
    for path in content:
        path = path.strip().strip("`").strip('"').strip("'")
        file_content = None
        encodings = ["utf-8", "utf-16", "utf-8-sig", "latin-1"]
        for encoding in encodings:
            try:
                async with aiofiles.open(path, "r", encoding=encoding) as f:
                    file_content = await f.read()
                break
            except Exception as e:
                print("ERROR: " + str(e))
                file_content = None
        # Try ascii with errors ignored as last resort
        if file_content is None:
            try:
                async with aiofiles.open(path, "r", encoding="ascii", errors="ignore") as f:
                    file_content = await f.read()
            except Exception as e:
                print("ERROR: " + str(e))
                file_content = None
        # Try binary read and decode as utf-8 ignoring errors
        if file_content is None:
            try:
                async with aiofiles.open(path, "rb") as f:
                    raw_bytes = await f.read()
                file_content = raw_bytes.decode("utf-8", errors="ignore")
            except Exception as e:
                file_content = None
                print("ERROR: " + str(e))
        if file_content is not None:
            contents.append(f"--- {os.path.basename(path)} ---\n{file_content}")
        else:
            contents.append(f"--- {os.path.basename(path)} ---\n[Error reading file: Could not decode with utf-16, utf-8-sig, utf-8, latin-1, ascii, or binary utf-8: {file_content}]")
    return "\n\n".join(contents)

load_dotenv()
api_key = os.getenv("API_KEY")
azure_endpoint = os.getenv("AZURE_ENDPOINT")
azure_deployment = os.getenv("AZURE_DEPLOYMENT")
model_client = AzureOpenAIChatCompletionClient(
    azure_deployment=azure_deployment,
    model="gpt-5",
    api_version="2024-12-01-preview",
    azure_endpoint=azure_endpoint,
    api_key=api_key,
)

planning_agent = AssistantAgent(
    "PlanningAgent",
    description="An agent for planning tasks, this agent should be the first to engage when given a new task.",
    model_client=model_client,
    system_message="""
    You are a planning agent.
    Your job is to break down complex tasks into smaller, manageable subtasks.
    Your team members are:
        SearchBlueprintAgent: Searches for information in the design of the system
        DataAnalystAgent: Performs calculations

    You only plan and delegate tasks - you do not execute them yourself.

    When assigning tasks, use this format:
    1. <agent> : <task>

    After all tasks are complete, summarize the findings, giving references to the files that demonstrate compliance, and end with "TERMINATE".
    """,
)

web_search_agent = AssistantAgent(
    "SearchBlueprintAgent",
    description="An agent for retrieving information about the system under analysis.",
    tools=[search_blueprint_tool],
    model_client=model_client,
    system_message="""
    You are a document search agent.
    Your only tool is search_tool - use it to find information.
    You make only one search call at a time.
    Once you have the results, you never do calculations based on them.
    """,
)

data_analyst_agent = AssistantAgent(
    "DataAnalystAgent",
    description="An agent for performing calculations.",
    model_client=model_client,
    tools=[],
    system_message="""
    You are a data analyst.
    Given the tasks you have been assigned, you should analyze the data and provide results using the tools provided.
    If you have not seen the data, ask for it.
    """,
)

text_mention_termination = TextMentionTermination("TERMINATE")
max_messages_termination = MaxMessageTermination(max_messages=25)
termination = text_mention_termination | max_messages_termination

selector_prompt = """Select an agent to perform task.

{roles}

Current conversation context:
{history}

Read the above conversation, then select an agent from {participants} to perform the next task.
Make sure the planner agent has assigned tasks before other agents start working.
Only select one agent.
"""

team = SelectorGroupChat(
    [planning_agent, web_search_agent, data_analyst_agent],
    model_client=model_client,
    termination_condition=termination,
    selector_prompt=selector_prompt,
    allow_repeated_speaker=True,  # Allow an agent to speak multiple turns in a row.
    max_turns=10,
)

guideline_description = "User accounts are not configured with password never expires or password not required."
task = f"Determine if this criteria has been satisfied with the current blueprint design: '{guideline_description}'"

load_dotenv()

# Use asyncio.run(...) if you are running this in a script.
asyncio.run(Console(team.run_stream(task=task)))

def selector_func(messages):
	"""
	custom logic to select next speaker.
	returns agent name or none to use model selection
	"""
	if len(messages) > 0 and messages[-1].source != "Manager":
		#always return to the manager afer other agents speak
		return "Manager"
	return None
