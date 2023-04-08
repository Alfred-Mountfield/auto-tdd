import json
from textwrap import dedent
from pprint import pprint
from src.utils.message import (
    send_messages as send_messages_general,
    wrap_system_message,
    wrap_assistant_message,
    wrap_user_message,
)


MESSAGE_FORMAT = dedent(
    """\
    Anything you output must be a JSON object which matches the following schema, which wraps your message contents within a JSON object so that it is machine parseable:
    {
        "type": "object",
        "properties": {
            "type": {
                "enum": ["INTRO", "FOLLOW_UP", "CONSTRAINT_SUMMARY", "FINISHED"]
            },
            "contents": {
                "type": "string"
            }
        },
        "required": ["type", "contents"]
    }

    - "INTRO" should be used for the initial question about a specific constraint on the input.
    - "FOLLOW_UP" should be used for a response to a user question, or a follow-up question if you do not understand the specific constraint yet.
    - "CONSTRAINT_SUMMARY" should be used for a summary of the constraint on the input you have discovered. This should be returned when you understand the specific constraint and you're ready to ask the next one. It should NOT repeat information captured in previous constraint.
    - "FINISHED" should be used to indicate that you are finished collecting constraints.

    An example of a valid message is:
    { "type": "INTRO", "contents": "Can the input be empty?" }

    Do not return any other text outside of the JSON object.
    """
)

RESPONSE_INSTRUCTIONS = dedent(
    """\
    Engage in a conversation with the user, try and focus on discovering one constraint on the input at a time, starting with an "INTRO". Respond with "FOLLOW_UP"s until you understand that one constraint. Then send a "CONSTRAINT_SUMMARY".
    Do NOT ask another question until asked to.
    When you have figured out all of the constraints, send a "FINISHED" message.
    """
)


def get_initial_prompt(function_purpose):
    return dedent(
        f"""\
        You are a large language model. Answer only in JSON objects which conform to the format described below.
        You are tasked with discovering the constraints of the inputs of a Python function whose purpose is described as:
        "{function_purpose}"

        You are to ask questions *in a machine-parseable manner* to get a comprehensive description of the possible inputs. 

        {MESSAGE_FORMAT}

        {RESPONSE_INSTRUCTIONS}

        It is essential that your entire response contains ONLY a single JSON object matching the format given above. Do not write any other text. A machine is parsing your response.
        """
    )


def get_interim_prompt(function_purpose, constraints):
    constraints_str = "\n".join(constraints)

    return dedent(
        f"""\
        You are a large language model. Answer only in JSON objects which conform to the format described below.
        You are tasked with discovering the constraints of the inputs of a Python function whose purpose is described as:
        "{function_purpose}"

        You have already acquired the following constraints:
        {constraints_str}

        {MESSAGE_FORMAT}

        Ask a question about a different constraint if there are more unclear aspects, or send a "FINISHED" message if you are done. Do not repeat existing constraints, they have been stored.
        It is essential that your entire response contains ONLY a single JSON object matching the format given above. Do not write any other text. A machine is parsing your response.
        """
    )


UNKNOWN_FORMAT_MESSAGE = dedent(
    f"""\
    Your response was in an incorrect format. 

    {MESSAGE_FORMAT}

    It is essential that your entire response contains ONLY a single JSON object matching the format given above. Do not write any other text. A machine is parsing your response.
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
        if incorrect_format_attempt > 3:
            print("Exceeded max attempts, exiting")
            print("Message log:")
            pprint(messages)
            exit()

        incorrect_format_attempt += 1

        assistant_response = send_messages(messages)
        messages.append(wrap_assistant_message(assistant_response))

        try:
            parsed_message = json.loads(assistant_response.strip())
        except json.JSONDecodeError:
            messages.append(wrap_user_message(UNKNOWN_FORMAT_MESSAGE))
            continue

        # TODO: handle control flow, make sure only one active INTRO
        # TODO: reset message list when a new constraint is started and pass a concise list of current constraints to save token limit

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
                            f"Constraint needs modification: {user_response}"
                        )
                    )
                    incorrect_format_attempt = 0
                    continue

                constraints.append(contents)
                messages = [
                    wrap_system_message(
                        get_interim_prompt(function_purpose, constraints)
                    ),
                    wrap_user_message("Ask your next question"),
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
