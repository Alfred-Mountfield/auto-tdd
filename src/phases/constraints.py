import json
import re
from textwrap import dedent
from pprint import pprint
from src.utils.message import (
    send_messages as send_messages_general,
    wrap_system_message,
    wrap_assistant_message,
    wrap_user_message,
)


def extract_object_from_string(input_string):
    # Regular expression to match the JSON object
    pattern = r'{\s*"type"\s*:\s*"(INTRO|FOLLOW_UP|CONSTRAINT_SUMMARY|FINISHED)"\s*,\s*"contents"\s*:\s*"(?:[^"\\]|\\.)*"\s*}'
    # Search for the pattern in the input string
    match = re.search(pattern, input_string)

    if match:
        # Extract the matched JSON object
        output_json = match.group(0)
        return output_json
    else:
        # No matching JSON object found
        raise ValueError("No JSON object found in the input string")


JSON_FORMAT_DISCLAIMER = "IMPORTANT: It is essential that your entire response contains ONLY a single JSON object exactly matching the format given above, the entire message should be parseable as JSON."

MESSAGE_FORMAT = dedent(
    f"""\
    Anything you output must be wrapped within a JSON object. The JSON object must contain a "type" field, and a "contents" field. The "contents" field should be your output in plain english. The "type" field must be one of the following strings:

    - "INTRO" should be used for the initial question about a specific constraint on the input.
    - "FOLLOW_UP" should be used for a response to a user question, or a follow-up question if you do not understand the specific constraint yet.
    - "CONSTRAINT_SUMMARY" should be used for a summary of _new information_ of the constraint on the input you have discovered. This should be returned when you understand the specific constraint and you're ready to ask the next one, there is no need to repeat previous information.
    - "FINISHED" should be used to indicate that you are finished collecting constraints.

    An example of a valid message is:

    {{ "type": "INTRO", "contents": "Can the input be empty?" }}

    {JSON_FORMAT_DISCLAIMER}
    """
)

RESPONSE_INSTRUCTIONS = dedent(
    """\
    Engage in a conversation with the user, try and focus on discovering one constraint on the input at a time, starting with an "INTRO". Respond with "FOLLOW_UP"s until you understand that one constraint. Then send a "CONSTRAINT_SUMMARY".
    You will be asked when it is time to provide a new question, do not add questions about new constraints to the end of another message.
    When you have figured out all of the constraints, send a "FINISHED" message.
    """
)


def get_initial_prompt(function_purpose):
    return dedent(
        f"""\
        You are a large language model. Answer only in JSON objects which conform to the format described below.
        You are tasked with discovering the constraints of the inputs of a Python function whose purpose is described as:
        \"""
        {function_purpose}
        \"""

        You are to ask questions *in a machine-parseable manner* to get a comprehensive description of the possible inputs. 

        {MESSAGE_FORMAT}

        {RESPONSE_INSTRUCTIONS}
        """
    )


def get_interim_prompt(function_purpose, constraints):
    constraints_str = "- " + "\n- ".join(
        [
            json.dumps({"type": "CONSTRAINT_SUMMARY", "contents": constraint})
            for constraint in constraints
        ]
    )

    return dedent(
        f"""\
        You are a large language model. Answer only in JSON objects which conform to the format described below.

        You are tasked with discovering the constraints of the inputs of a Python function whose purpose is described as:
        \"""
        {function_purpose}
        \"""

        You have already acquired the following constraints:
        {constraints_str}
        
        {MESSAGE_FORMAT}

        If you have no more questions, send a "FINISHED" message.

        IMPORTANT: When you send a "CONSTRAINT_SUMMARY", only output new information that is not already expressed in previous constraints.
        For example, if you already have a constraint "The input is expected to be a list of floats", and you ask the user if there is a maximum length to that list and they say yes, you should not say "The input is expected to be a list of floats, with a maximum length of 5". Instead, you should say "The maximum length of the list is 5", as the information about it being a list of floats is already captured.
        
        You may now ask a question about a NEW constraint, or send a "FINISHED" message if you are done.
        """
    )


UNKNOWN_FORMAT_MESSAGE = dedent(
    """\
    Your response was not deserializable. Did you add text outside of the JSON object? Try again, ONLY outputting a JSON object.
    """
)


def send_messages(messages):
    prefixed_messages = [*messages]
    return send_messages_general(prefixed_messages)


def run_constraints_phase(function_purpose):
    messages = []

    print("Entering phase 1: Establish input space.")

    phase_1_complete = False

    messages.append(wrap_system_message(get_initial_prompt(function_purpose)))
    messages.append(wrap_user_message("Ask your first question"))

    constraints = []
    incorrect_format_attempt = 0

    while not phase_1_complete:
        if incorrect_format_attempt > 2:
            print("Exceeded max attempts, exiting")
            print("Message log:")
            pprint(messages)
            exit()

        incorrect_format_attempt += 1

        assistant_response = send_messages(messages)
        messages.append(wrap_assistant_message(assistant_response))

        try:
            obj = extract_object_from_string(assistant_response)
            parsed_message = json.loads(obj.strip())
            # we only want to parse the first level as a dict
            parsed_message = {
                key: value if not isinstance(value, dict) else json.dumps(value)
                for key, value in parsed_message.items()
            }
        # pylint: disable=bare-except
        except:
            # print("Could not parse JSON object from response")
            # print("Response:")
            # print(assistant_response)
            messages.append(wrap_user_message(UNKNOWN_FORMAT_MESSAGE))
            continue

        # TODO: handle control flow, make sure only one active INTRO
        match parsed_message:
            case {"type": "INTRO", "contents": contents}:
                if len(constraints) > 0:
                    print("Current constraints")
                    for idx, constraint in enumerate(constraints):
                        print(f"Constraint {idx + 1}: {constraint}")

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

            case {"type": "CONSTRAINT_SUMMARY", "contents": contents}:
                print("Constraint captured:")
                print(contents)
                user_response = input(
                    "Is this correct? Write exactly 'yes' if it is, otherwise describe what you want improved.\n"
                )

                if user_response != "yes":
                    messages.append(
                        wrap_user_message(
                            f"Constraint needs modification: {user_response}.\n Remember to respond in the given JSON format."
                        )
                    )
                    incorrect_format_attempt = 0
                    continue

                constraints.append(contents)
                messages = [
                    wrap_system_message(
                        get_interim_prompt(function_purpose, constraints)
                    ),
                    wrap_user_message(
                        "Ask your next question, remember to respond in the given JSON format."
                    ),
                ]

                incorrect_format_attempt = 0
                continue

            case {"type": "FINISHED", "contents": contents}:
                print("Finished collecting constraints")
                for idx, constraint in enumerate(constraints):
                    print(f"Constraint {idx + 1}: {constraint}")
                # TODO continue to next phase
                exit(0)

        # TODO handle this better
        messages.append(wrap_user_message(UNKNOWN_FORMAT_MESSAGE))
        continue
