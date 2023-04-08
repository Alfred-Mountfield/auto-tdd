import openai
import os
import json
from textwrap import dedent
from dotenv import load_dotenv

load_dotenv()

from count_tokens import num_tokens_from_messages

MODEL = "gpt-3.5-turbo"

SYSTEM_PROMPT = {
    "role": "system",
    "content": "You are a large language model. You will be given message formats to respond in. Follow the shape and constraints exactly. Make message contents as concise as possible.",
}


def wrap_user_message(content):
    return {
        "role": "user",
        "content": content,
    }


def wrap_assistant_message(content):
    return {
        "role": "assistant",
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


messages_format = dedent(
    f"""\
    You should respond with a single JSON object. Your messages MUST be one of these classifications
    
    1. Question Introduction 
    The initial question for a specific requirement.
    Message Format: "{{ "type": "INTRO", "contents" <MESSAGE CONTENTS> }}"

    2. Follow-up
    A response to a user question, or a follow-up question if you do not understand the specific requirement yet.
    Message Format: "{{ "type": "FOLLOW_UP": "contents" <MESSAGE CONTENTS> }}"

    3. Requirement summary 
    A summary of the specific requirement. Should be returned when you understand the specific requirement and you're ready to ask the next one.
    Message Format: "{{ "type": "REQUIREMENT_SUMMARY", "contents": <MESSAGE CONTENTS> }}"

    4. Finished collecting requirements
    A message to indicate that you are finished collecting requirements.
    Message Format: "{{ "type": "FINISHED", "contents": <MESSAGE CONTENTS> }}"
    """
)

unknown_format_message = dedent(
    f"""\
    Your response was in an incorrect format. 

    {messages_format}

    Try again.
    """
)


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

        Your first task is to understand the test space, you are to engage in a conversation with the user and ask questions to get a comprehensive description of the possible inputs. 

        Engage in a conversation with the user, try and focus on one requirement at a time, starting with a Question Introduction. Respond with Follow-Up's until you understand that one requirement. Then send a Requirement Summary.
        Do NOT ask another question until responding with the Requirement Summary. 

        {messages_format}
        """
    )

    messages.append(wrap_user_message(initial_prompt))

    requirements = []
    incorrect_format_attempt = 0

    while not phase_1_complete:
        if incorrect_format_attempt > 5:
            print("Exceeded max attempts, exiting")
            print("Message log:")
            print(messages)
            exit()

        incorrect_format_attempt += 1

        assistant_response = send_messages(messages)
        messages.append(wrap_assistant_message(assistant_response))

        try:
            parsed_message = json.loads(assistant_response.strip())
        except json.JSONDecodeError as e:
            messages.append(wrap_user_message(unknown_format_message))
            continue

        # TODO: handle control flow, make sure only one active INTRO
        # TODO: reset message list when a new requirement is started and pass a concise list of current requirements to save token limit

        match parsed_message:
            case {"type": "INTRO", "contents": contents}:
                if len(requirements) > 0:
                    print("Current requirements")
                    for idx, requirement in enumerate(requirements):
                        print(f"Requirement {idx + 1}: {requirement}")

                # TODO: print the question and programmatically ask for a response, or an indication that the user is happy
                user_response = input(f"{contents}\n")

                messages.append(wrap_user_message(user_response))
                incorrect_format_attempt = 0
                continue

            case {"type": "FOLLOW_UP", "contents": contents}:
                # TODO: print the question and programmatically ask for a response, or an indication that the user is happy
                user_response = input(f"{contents}\n")

                messages.append(wrap_user_message(user_response))
                incorrect_format_attempt = 0
                continue

            case {"type": "REQUIREMENT_SUMMARY", "contents": contents}:
                print("Requirement captured:")
                print(contents)
                user_response = input("Is this correct? Write exactly 'yes' if it is, otherwise describe what you want improved.\n")

                if user_response != "yes":
                    messages.append(wrap_user_message(f"User wasn't completely happy with requirement: {user_response}"))
                    incorrect_format_attempt = 0
                    continue


                requirements.append(contents)
                messages.append(
                    wrap_user_message("Requirement understood, ask your next question")
                )
                incorrect_format_attempt = 0
                continue

            case {"type": "FINISHED", "contents": contents}:
                print("Finished collecting requirements")
                for idx, requirement in enumerate(requirements):
                    print(f"Requirement {idx + 1}: {requirement}")
                # TODO continue to next phase
                exit(0)

        # TODO handle this better
        messages.append(wrap_user_message(unknown_format_message))
        continue

    # TODO: provide options to return to previous phases if needs be

    # TODO: phase 2, establish test cases with the model

    # TODO: phase 3, get the model to generate code, and repeatedly run it and feed the results back into the model until it passes all test cases


if __name__ == "__main__":
    main()
