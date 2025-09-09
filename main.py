# # Install AgentChat and OpenAI client from Extensions
# pip install -U "autogen-agentchat" "autogen-ext[openai]" "autogen-ext[azure]" "aiohttp"

from autogen_core.models import UserMessage
from autogen_ext.auth.azure import AzureTokenProvider
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
from azure.identity import DefaultAzureCredential
import asyncio

async def main() -> None:
  # Create the token provider
  token_provider = AzureTokenProvider(
      DefaultAzureCredential(),
      "https://cognitiveservices.azure.com/.default",
  )

  az_model_client = AzureOpenAIChatCompletionClient(
    azure_deployment="jonathan-initial-test-gpt-5-chat-2",
    model="gpt-5",
    api_version="2024-12-01-preview",
    azure_endpoint="<redacted>",
    api_key="<redacted>",
  )

  result = await az_model_client.create([UserMessage(content="What is the capital of France?", source="user")])
  print(result)
  await az_model_client.close()

asyncio.run(main())
