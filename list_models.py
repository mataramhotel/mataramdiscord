"""Cetak daftar model yang tersedia di endpoint Nous, untuk memastikan ID model yang benar."""

import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.environ["NOUS_API_KEY"],
    base_url=os.getenv("NOUS_BASE_URL", "https://inference-api.nousresearch.com/v1"),
)

for m in client.models.list().data:
    print(m.id)
