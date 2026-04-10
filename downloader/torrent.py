import asyncio
import os
import time
from typing import Callable, Awaitable

try:
    import libtorrent as lt
except ImportError:
    lt = None  # Allows module to load in test environments without libtorrent installed


async def download_torrent(
    torrent_url: str,
    save_path: str,
    progress_callback: Callable[[float, str], Awaitable[None]] | None = None,
) -> str:
    """Download a torrent from URL to save_path.

    Returns the absolute path of the largest file in the torrent (the video file).
    Calls progress_callback(percent, speed_str) approximately every 2 seconds.
    """
    loop = asyncio.get_event_loop()
    callback_queue: asyncio.Queue = asyncio.Queue()

    def sync_download() -> str:
        if lt is None:
            raise RuntimeError("libtorrent is not installed. Run: brew install libtorrent-rasterbar && pip install libtorrent")

        ses = lt.session({"listen_interfaces": "0.0.0.0:6881"})
        params = lt.add_torrent_params()
        params.url = torrent_url
        params.save_path = save_path
        h = ses.add_torrent(params)

        while not h.is_seed():
            s = h.status()
            pct = s.progress * 100
            speed = f"{s.download_rate / 1024:.1f} KB/s"
            loop.call_soon_threadsafe(callback_queue.put_nowait, (pct, speed))
            time.sleep(2)

        loop.call_soon_threadsafe(callback_queue.put_nowait, None)  # sentinel

        info = h.get_torrent_info()
        files = info.files()
        largest_idx = max(range(files.num_files()), key=lambda i: files.file_size(i))
        return os.path.join(save_path, files.file_path(largest_idx))

    future = loop.run_in_executor(None, sync_download)

    while True:
        try:
            item = callback_queue.get_nowait()
        except asyncio.QueueEmpty:
            if future.done():
                break
            await asyncio.sleep(0.5)
            continue

        if item is None:
            break
        if progress_callback:
            pct, speed = item
            await progress_callback(pct, speed)

    return await future
