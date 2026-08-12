"""Bot Discord yang menjawab lewat model Hermes (Nous Research).

Cara pakai: tag @bot di channel mana pun, bot membalas di thread percakapan yang sama.
"""

import asyncio
import logging
import os
from collections import defaultdict, deque

import discord
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
NOUS_API_KEY = os.environ["NOUS_API_KEY"]
NOUS_BASE_URL = os.getenv("NOUS_BASE_URL", "https://inference-api.nousresearch.com/v1")
MODEL = os.getenv("HERMES_MODEL", "Hermes-4-70B")

SYSTEM_PROMPT = os.getenv(
    "SYSTEM_PROMPT",
    "Kamu adalah asisten di sebuah server Discord. Jawab ringkas, ramah, "
    "dan pakai bahasa yang sama dengan penanya. Hindari jawaban bertele-tele.",
)

HISTORY_TURNS = int(os.getenv("HISTORY_TURNS", "8"))
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "800"))
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.7"))
DISCORD_LIMIT = 2000

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("hermes-bot")

llm = AsyncOpenAI(api_key=NOUS_API_KEY, base_url=NOUS_BASE_URL)

intents = discord.Intents.default()
intents.message_content = True  # privileged — aktifkan di Developer Portal > Bot
client = discord.Client(intents=intents)

# Riwayat percakapan per channel, dibatasi agar prompt tidak membengkak.
history: dict[int, deque] = defaultdict(lambda: deque(maxlen=HISTORY_TURNS * 2))
locks: dict[int, asyncio.Lock] = defaultdict(asyncio.Lock)


def chunk(text: str, size: int = DISCORD_LIMIT) -> list[str]:
    """Pecah teks agar tiap bagian muat di satu pesan Discord."""
    if len(text) <= size:
        return [text]
    parts, buf = [], ""
    for line in text.splitlines(keepends=True):
        while len(line) > size:
            if buf:
                parts.append(buf)
                buf = ""
            parts.append(line[:size])
            line = line[size:]
        if len(buf) + len(line) > size:
            parts.append(buf)
            buf = line
        else:
            buf += line
    if buf:
        parts.append(buf)
    return parts


async def ask_hermes(channel_id: int, prompt: str) -> str:
    convo = history[channel_id]
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, *convo, {"role": "user", "content": prompt}]

    resp = await llm.chat.completions.create(
        model=MODEL,
        messages=messages,
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
    )
    answer = (resp.choices[0].message.content or "").strip()

    convo.append({"role": "user", "content": prompt})
    convo.append({"role": "assistant", "content": answer})
    return answer or "(model tidak mengembalikan apa-apa)"


@client.event
async def on_ready():
    log.info("Login sebagai %s (id %s), model %s", client.user, client.user.id, MODEL)


@client.event
async def on_message(message: discord.Message):
    if message.author.bot or client.user not in message.mentions:
        return

    prompt = message.content.replace(f"<@{client.user.id}>", "").replace(f"<@!{client.user.id}>", "").strip()

    if prompt.lower() in {"reset", "clear", "lupakan"}:
        history.pop(message.channel.id, None)
        await message.reply("Riwayat percakapan di channel ini dihapus.", mention_author=False)
        return

    if not prompt:
        await message.reply("Ada yang bisa dibantu? Tag aku dengan pertanyaanmu.", mention_author=False)
        return

    async with locks[message.channel.id]:
        async with message.channel.typing():
            try:
                answer = await ask_hermes(message.channel.id, prompt)
            except Exception:
                log.exception("Gagal memanggil Hermes")
                await message.reply("Maaf, gagal menghubungi model. Coba lagi sebentar lagi.", mention_author=False)
                return

    target = message
    for part in chunk(answer):
        target = await target.reply(part, mention_author=False)


if __name__ == "__main__":
    client.run(DISCORD_TOKEN)
