from typing import List
from openai import OpenAI
import openai
from pydantic import BaseModel, ValidationError


class LLMInput(BaseModel):
    message: str


class LLMOutput(BaseModel):
    response: str


client = OpenAI()


def chat_with_llm(system_message, user_message, input_model, output_model):

    input = input_model(message=user_message)

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": input.message}
        ]
    )
    data = response.choices[0].message.content
    output = output_model(response=data)
    return output


# Example usage
if __name__ == "__main__":
    try:
        user_message = "Hello!"
        system_message = "You are a helpful assistant."
        result = chat_with_llm(
            system_message, user_message, LLMInput, LLMOutput)
        print(result.response)
    except ValidationError as e:
        print("Input validation error:", e)
