import openai
import os
from textwrap import dedent
from dotenv import load_dotenv

load_dotenv()

from count_tokens import num_tokens_from_messages

MODEL = "gpt-3.5-turbo"

SYSTEM_PROMPT = {
    "role": "system",
    "content": "You are a large language model. Answer as concisely as possible, conform to the parameters given in prompts as tightly as possible.",
}


def prompt(content):
    return {
        "role": "user",
        "content": content,
    }


messages = [
    SYSTEM_PROMPT,
]


def setup():
    openai.api_key = os.getenv("OPENAI_API_KEY")


def send_messages(messages):
    prefixed_messages = [SYSTEM_PROMPT, *messages]
    total_tokens = num_tokens_from_messages(prefixed_messages)

    if total_tokens > 3500:
        # TODO: truncate the message list
        print("Getting close to the token limit, bailing")
        exit()

    response = openai.ChatCompletion.create(
        model=MODEL, messages=prefixed_messages, temperature=0.1, max_tokens=500
    )

    # TODO: handle cases or more information
    return response["choices"][0]["message"]["content"]


def main():
    setup()

    messages = []

    function_purpose = input(
        "Describe the purpose of your function, for example, 'Takes a list of numbers and finds their average.'...\n"
    )
    print("Entering phase 1: Establish input space.")

    phase_1_complete = False
    initial_prompt = dedent(
        f"""\
        You are going to write a Python function. It's purpose has been described as:
        "{function_purpose}"
        Your first task is understand the test space, you are to ask questions to get a comprehensive description of the possible inputs. Ask your first question.
        """
    )

    messages.append(prompt(initial_prompt))

    while not phase_1_complete:
        # TODO: print the current set of constraints for the input space

        question = send_messages(messages)

        # TODO: print the question and ask for a response, or an indication that the user is happy
        response = input(f"{question}:\n")

        # TODO: give the model the user's response, ask it if it needs further clarification, otherwise ask another question.

        exit()

    # TODO: phase 2, establish test cases with the model

    # TODO: phase 3, get the model to generate code, and repeatedly run it and feed the results back into the model until it passes all test cases


if __name__ == "__main__":
    main()
