import os
from langchain_openai import ChatOpenAI

def get_chat_model(model="gpt-4", temperature=0.7, **kwargs):
    """
    Factory function to get ChatModel instance.
    Supports switching to DeepSeek via USE_DEEPSEEK env var.
    """
    use_deepseek = os.getenv("USE_DEEPSEEK", "").lower() == "true"
    
    if use_deepseek:
        # DeepSeek specific configuration
        # DeepSeek's chat model is usually 'deepseek-chat' or 'deepseek-coder'.
        
        target_model = "deepseek-chat"
        
        # Allow overriding if specific deepseek model is passed in kwargs or model arg
        # If user requested a GPT model, switch to deepseek-chat.
        # If user specifically requested deepseek-coder (unlikely here but possible), keep it.
        if "deepseek" in model:
            target_model = model
        
        # Remove 'openai_api_base' if it exists in kwargs to avoid conflict
        # (though we set it explicitly below)
        kwargs.pop("base_url", None)
        kwargs.pop("openai_api_base", None)
        kwargs.pop("api_key", None)
        kwargs.pop("openai_api_key", None)

        return ChatOpenAI(
            model=target_model,
            temperature=temperature,
            base_url="https://api.deepseek.com",
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            **kwargs
        )
    
    return ChatOpenAI(model=model, temperature=temperature, **kwargs)

# Alias for user requested "ChatDeepSeek" class logic, if they expect a class import.
# But since we are replacing usage, get_chat_model is better.
# If we wanted to be fancy, we could return a class that inherits from ChatOpenAI
# but pre-configures itself. But the factory function is cleaner.

