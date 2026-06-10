"""Langfuse client + @observe_anthropic decorator."""
import os
from functools import wraps
from langfuse import Langfuse

_client: Langfuse | None = None


def get_langfuse() -> Langfuse:
    global _client
    if _client is None:
        _client = Langfuse(
            public_key=os.environ.get("LANGFUSE_PUBLIC_KEY"),
            secret_key=os.environ.get("LANGFUSE_SECRET_KEY"),
            host=os.environ.get("LANGFUSE_HOST", "http://localhost:3001"),
        )
    return _client


def observe_anthropic(name: str = "claude_call"):
    """Decorate a function that calls anthropic.messages.create.

    Records model, latency, and (if available) token usage to Langfuse.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            client = get_langfuse()
            trace = client.trace(name=name)
            generation = trace.generation(
                name=func.__name__,
                model=kwargs.get("model", "unknown"),
                input=kwargs.get("messages", kwargs.get("prompt")),
            )
            try:
                result = func(*args, **kwargs)
                # Try to pull token usage if it's an Anthropic Message object
                try:
                    generation.end(
                        output=getattr(result, "content", str(result)),
                        usage={
                            "input": getattr(result.usage, "input_tokens", None),
                            "output": getattr(result.usage, "output_tokens", None),
                        },
                    )
                except AttributeError:
                    generation.end(output=str(result))
                return result
            except Exception as e:
                generation.end(level="ERROR", status_message=str(e))
                raise
        return wrapper
    return decorator
