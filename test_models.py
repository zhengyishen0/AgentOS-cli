#!/usr/bin/env python3
import asyncio
import llm_provider

async def test_openai_models():
    """Test fetching available OpenAI models"""
    try:
        models = await llm_provider.get_available_models("openai")
        print("Available OpenAI models:")
        for model in sorted(models):
            print(f"  - {model}")
    except Exception as e:
        print(f"Error fetching models: {e}")

if __name__ == "__main__":
    asyncio.run(test_openai_models())