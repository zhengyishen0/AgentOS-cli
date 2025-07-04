#!/usr/bin/env python3
"""
Example of using agent configurations with the LLM provider
"""

import asyncio
from modules.agent_config import load_agent_config
from modules.llm_provider import complete

async def use_agent(agent_name: str, user_message: str):
    """Use a specific agent to respond to a user message"""
    
    # Load the agent configuration
    config = load_agent_config(agent_name)
    if not config:
        print(f"Agent '{agent_name}' not found!")
        return
    

    
    # Prepare the conversation
    messages = [
        {"role": "user", "content": user_message}
    ]
    
    try:
        # Get response from the agent
        response = await complete(
            provider=config['provider'],
            model=config['model'],
            messages=messages,
            system=config['system_prompt']
        )
        
        print(f"Agent response: {response['content']}")
        print(f"Tokens used: {response['usage']['total_tokens']}")
        
    except Exception as e:
        print(f"Error: {e}")

async def main():
    """Main function to demonstrate agent usage"""
    
    # Example conversations with different agents
    conversations = [
        ("assistant", "Hello! How can you help me today?"),
        ("coder", "Write a Python function to calculate fibonacci numbers"),
        ("analyst", "What are the key trends in AI development in 2024?")
    ]
    
    for agent_name, message in conversations:
        await use_agent(agent_name, message)
        print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    asyncio.run(main()) 