import httpx
import json
import asyncio
from typing import AsyncGenerator, Dict, Any, Optional, List

from src.core.settings import load_settings

class OpenAICompatibleClientError(Exception):
    """Custom exception for OpenAICompatibleClient errors."""
    pass

class OpenAICompatibleClient:
    """
    Asynchronous client for interacting with OpenAI-compatible API endpoints,
    specifically for streaming text generation.
    """
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=None)
        self._current_settings = load_settings()

    def _get_api_url(self) -> str:
        """Constructs the API URL from settings."""
        base_url = self._current_settings.get("base_url", "127.0.0.1:5001")
        # Handle URL prefix if not present
        if not base_url.startswith(("http://", "https://")):
            base_url = f"http://{base_url}"
        return f"{base_url}/v1/completions"

    def reload_settings(self):
        """Reloads settings from the config file."""
        self._current_settings = load_settings()
        print("OpenAICompatibleClient settings reloaded.")

    async def generate_stream(
        self,
        prompt: str,
        max_length: Optional[int] = None,
        generation_params: Optional[Dict[str, Any]] = None,
        stop_sequence: Optional[List[str]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Sends a prompt to the OpenAI-compatible streaming API and yields generated tokens.

        Args:
            prompt: The input prompt string.
            max_length: Optional specific max_length for this generation request.
            generation_params: Optional dictionary overriding other default generation parameters.
            stop_sequence: Optional list of strings to use as stop sequences.

        Yields:
            str: Generated text chunks (tokens).

        Raises:
            OpenAICompatibleClientError: If connection fails or API returns an error status.
        """
        api_url = self._get_api_url()
        
        # Convert to OpenAI-compatible parameters
        params_to_send = {
            "temperature": self._current_settings.get("temperature"),
            "min_p": self._current_settings.get("min_p"),
            "top_p": self._current_settings.get("top_p"),
            "top_k": self._current_settings.get("top_k"),
            "repeat_penalty": self._current_settings.get("rep_pen"),
            "stop": stop_sequence if stop_sequence is not None else self._current_settings.get("stop_sequences", []),
        }

        if generation_params:
            gen_params_copy = generation_params.copy()
            gen_params_copy.pop("stop_sequence", None)
            params_to_send.update(gen_params_copy)

        # OpenAI-compatible request format
        payload = {
            "prompt": prompt,
            "stream": True,
            "max_tokens": max_length,
            **params_to_send
        }

        payload = {k: v for k, v in payload.items() if v is not None}

        print(f"Sending request to {api_url} with payload: {json.dumps(payload, indent=2)}")

        try:
            async with self.client.stream("POST", api_url, json=payload) as response:
                if response.status_code != 200:
                    error_content = await response.aread()
                    raise OpenAICompatibleClientError(
                        f"API Error: Status {response.status_code} - {error_content.decode()}"
                    )

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:].strip()
                        if data_str == "[DONE]":
                            print("Stream finished ([DONE] received).")
                            break
                        try:
                            data = json.loads(data_str)
                            token = data["choices"][0]["text"]
                            if token:
                                yield token
                        except json.JSONDecodeError:
                            print(f"Warning: Could not decode JSON data: {data_str}")
                        except Exception as e:
                            print(f"Error processing stream line: {line}, Error: {e}")

        except httpx.ConnectError as e:
            raise OpenAICompatibleClientError(
                f"Connection Error: Could not connect to {api_url}. Is the server running? Details: {e}"
            )
        except httpx.TimeoutException as e:
            raise OpenAICompatibleClientError(
                f"Timeout Error: Request to {api_url} timed out. Details: {e}"
            )
        except httpx.RequestError as e:
            raise OpenAICompatibleClientError(
                f"Request Error: An error occurred during the request to {api_url}. Details: {e}"
            )
        except Exception as e:
            raise OpenAICompatibleClientError(
                f"An unexpected error occurred during streaming: {e}"
            )

    async def close(self):
        """Closes the underlying HTTP client."""
        await self.client.aclose()


# Example Usage (for testing)
async def main():
    client = OpenAICompatibleClient()
    client.reload_settings()

    test_prompt = "Write a short story about a brave knight."
    print(f"\n--- Testing generate_stream with prompt: ---\n{test_prompt}\n------------------------------------------")

    try:
        full_response = ""
        async for token in client.generate_stream(test_prompt):
            print(token, end="", flush=True)
            full_response += token
        print("\n--- Stream finished ---")

    except OpenAICompatibleClientError as e:
        print(f"\n--- Error during generation: {e} ---")
    finally:
        await client.close()
        print("\nClient closed.")

if __name__ == "__main__":
    load_settings()
    asyncio.run(main())
