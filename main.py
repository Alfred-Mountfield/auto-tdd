import openai
import os
from dotenv import load_dotenv

load_dotenv()

from count_tokens import num_tokens_from_messages

MODEL = "gpt-3.5-turbo"

SYSTEM_PROMPT = {
    "role": "system",
    "content": "You are a large language model. Answer as concisely as you can, and conform to the parameters given in prompts as tightly as you can.",
}

OPENING_PROMPT = {
    "role": "user",
    "content": "Write me a haiku about test-driven development.",
}

messages = [
    SYSTEM_PROMPT,
    OPENING_PROMPT,
]


def main():
    openai.api_key = os.getenv("OPENAI_API_KEY")

    print(f"Total tokens: {num_tokens_from_messages(messages)}")

    response = openai.ChatCompletion.create(
        model=MODEL, messages=messages, temperature=0.1, max_tokens=250
    )

    print(response)


if __name__ == "__main__":
    main()
