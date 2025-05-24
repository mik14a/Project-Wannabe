from typing import Protocol, AsyncGenerator, Dict, Any, Optional, List

class LLMClient(Protocol):
    """
    Protocol defining the interface for LLM (Large Language Model) clients.
    This abstract base class ensures consistent implementation across different LLM client types.
    """
    async def generate_stream(
        self,
        prompt: str,
        max_length: Optional[int] = None,
        generation_params: Optional[Dict[str, Any]] = None,
        stop_sequence: Optional[List[str]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Generates text stream from the LLM based on the given prompt.

        Args:
            prompt: The input text prompt to generate from
            max_length: Optional maximum length of generated text
            generation_params: Optional dictionary of generation parameters to override defaults
            stop_sequence: Optional list of strings that will stop generation when encountered

        Returns:
            AsyncGenerator yielding generated text chunks (tokens)
        """
        ...
