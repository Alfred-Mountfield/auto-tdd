import os
import openai
from dotenv import load_dotenv

from src.phases.constraints import run_constraints_phase


def setup():
    load_dotenv()
    openai.api_key = os.getenv("OPENAI_API_KEY")


def main():
    setup()

    function_purpose = input(
        "Describe the purpose of your function, for example, 'Takes a list of numbers and finds their average.'...\n"
    )

    run_constraints_phase(function_purpose)
    # TODO: provide options to return to previous phases if needs be

    # TODO: phase 2, establish test cases with the model

    # TODO: phase 3, get the model to generate code, and repeatedly run it and feed the results back into the model until it passes all test cases


if __name__ == "__main__":
    main()
