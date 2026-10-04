"""SSE adapter for the integrator's StreamingResponse; no gateway edits required."""
import asyncio
import threading

from labforge.agent.errors import redacted_json, safe_error
from labforge.agent.planner import run_turn


class Disconnected(Exception):
    pass


async def stream_turn(history: list[dict]):
    """Yield SSE frames. Model calls run off the ASGI event loop.

    Gateway use: StreamingResponse(stream_turn(req.messages), media_type='text/event-stream').
    On disconnect, further model/tool calls stop at the next event boundary; an already
    running API call may still complete. A consumer must preserve result.history.
    """
    loop = asyncio.get_running_loop()
    queue = asyncio.Queue()
    stopped = threading.Event()

    def put(event):
        if stopped.is_set():
            raise Disconnected()
        loop.call_soon_threadsafe(queue.put_nowait, event)

    def worker():
        try:
            result = run_turn(history, on_event=put, stream_text=True)
            put({'type': 'result', 'status': result.get('status'),
                 'message': result.get('message'), 'output': result})
        except Disconnected:
            pass
        except Exception as exc:
            if not stopped.is_set():
                put({'type': 'error', 'message': safe_error(exc)})
        finally:
            if not stopped.is_set():
                loop.call_soon_threadsafe(queue.put_nowait, None)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    try:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=15)
            except asyncio.TimeoutError:
                yield ': keepalive\n\n'
                continue
            if event is None:
                break
            yield 'data: ' + redacted_json(event) + '\n\n'
    finally:
        stopped.set()
