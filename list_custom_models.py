import os

import openai

base_url = os.environ.get("LITELLM_BASE_URL") or os.environ.get("OPENAI_BASE_URL")
api_key = os.environ.get("LITELLM_API_KEY") or os.environ.get("OPENAI_API_KEY")

if not base_url or not api_key:
    print("Missing base_url or api_key in environment.")
    exit(1)

client = openai.OpenAI(api_key=api_key, base_url=base_url)

try:
    models = client.models.list()
    print("Available models at", base_url)
    for m in models.data:
        print("-", m.id)
except Exception as e:
    print("Error listing models:", e)
    exit(2)
