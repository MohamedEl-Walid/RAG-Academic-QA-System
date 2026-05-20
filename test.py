from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage
import os
import getpass
import os

if not os.getenv("OPENROUTER_API_KEY"):
    os.environ["OPENROUTER_API_KEY"] = getpass.getpass("Enter your OpenRouter API key")

os.environ["LANGSMITH_API_KEY"] = getpass.getpass("Enter your LangSmith API key: ")
os.environ["LANGSMITH_TRACING"] = "true"

llm = ChatOpenAI(
    model="openai/gpt-4o-mini",
    temperature=0.7
)

response = llm.invoke([HumanMessage(content="hi")])

print(response.content)