import openai
from src.utils.count_tokens import num_tokens_from_messages

MODEL = "gpt-3.5-turbo"


def wrap_system_message(content):
    return {
        "role": "system",
        "content": content,
    }


def wrap_assistant_message(content):
    return {
        "role": "assistant",
        "content": content,
    }


def wrap_user_message(content):
    return {
        "role": "user",
        "content": content,
    }


def send_messages(messages):
    total_tokens = num_tokens_from_messages(messages)

    if total_tokens > 3500:
        # TODO: truncate the message list
        print("Getting close to the token limit, bailing")
        exit()

    response = openai.ChatCompletion.create(
        model=MODEL, messages=messages, temperature=0.1, max_tokens=500
    )

    # TODO: handle cases or more information
    return response["choices"][0]["message"]["content"]
