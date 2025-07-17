"""Streaming support for AI summary generation."""

from typing import Any, AsyncIterator

from src.pr_agents.pr_processing.analysis_models import PersonaSummary


class StreamingResponse:
    """Represents a streaming response from an LLM."""

    def __init__(self, persona: str, stream: AsyncIterator[str]):
        """Initialize streaming response.

        Args:
            persona: The persona this response is for
            stream: Async iterator of text chunks
        """
        self.persona = persona
        self.stream = stream
        self.accumulated_text = ""
        self.token_count = 0

    async def __aiter__(self):
        """Iterate over streaming chunks."""
        async for chunk in self.stream:
            self.accumulated_text += chunk
            self.token_count += len(chunk.split())  # Rough token estimate
            yield chunk

    def to_summary(self, confidence: float = 0.95) -> PersonaSummary:
        """Convert accumulated text to PersonaSummary.

        Args:
            confidence: Confidence score for the summary

        Returns:
            PersonaSummary instance
        """
        return PersonaSummary(
            persona=self.persona,
            summary=self.accumulated_text.strip(),
            confidence=confidence,
        )


class StreamingHandler:
    """Handles streaming responses from multiple personas."""

    def __init__(self):
        """Initialize streaming handler."""
        self.responses: dict[str, StreamingResponse] = {}

    def add_response(self, persona: str, stream: AsyncIterator[str]) -> None:
        """Add a streaming response for a persona.

        Args:
            persona: The persona type
            stream: Async iterator of text chunks
        """
        self.responses[persona] = StreamingResponse(persona, stream)

    async def stream_all(self) -> AsyncIterator[tuple[str, str]]:
        """Stream all responses concurrently.

        Yields:
            Tuples of (persona, chunk) for each text chunk
        """
        import asyncio

        # Create tasks for each stream
        async def stream_persona(persona: str, response: StreamingResponse):
            async for chunk in response:
                yield persona, chunk

        # Merge all streams
        streams = [
            stream_persona(persona, response)
            for persona, response in self.responses.items()
        ]

        # Use asyncio to merge streams
        async for persona, chunk in self._merge_streams(streams):
            yield persona, chunk

    async def _merge_streams(
        self, streams: list[AsyncIterator[tuple[str, str]]]
    ) -> AsyncIterator[tuple[str, str]]:
        """Merge multiple async iterators.

        Args:
            streams: List of async iterators

        Yields:
            Items from all streams as they become available
        """
        import asyncio

        # Create queues for each stream
        queues = [asyncio.Queue() for _ in streams]
        finished = [False] * len(streams)

        async def fill_queue(stream_idx: int, stream: AsyncIterator, queue: asyncio.Queue):
            try:
                async for item in stream:
                    await queue.put(item)
            finally:
                finished[stream_idx] = True
                await queue.put(None)  # Sentinel

        # Start tasks to fill queues
        tasks = [
            asyncio.create_task(fill_queue(i, stream, queue))
            for i, (stream, queue) in enumerate(zip(streams, queues, strict=False))
        ]

        # Read from queues
        while not all(finished):
            for i, queue in enumerate(queues):
                if not finished[i] and not queue.empty():
                    item = await queue.get()
                    if item is not None:
                        yield item
            await asyncio.sleep(0.01)  # Small delay to prevent busy waiting

        # Wait for all tasks to complete
        await asyncio.gather(*tasks)

    def get_summaries(self) -> dict[str, PersonaSummary]:
        """Get completed summaries from all responses.

        Returns:
            Dictionary mapping persona to PersonaSummary
        """
        return {
            persona: response.to_summary()
            for persona, response in self.responses.items()
        }