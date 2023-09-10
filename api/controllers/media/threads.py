import asyncio
from asyncio import gather
from logging import getLogger
from pathlib import Path
from queue import Queue
from threading import Event, Thread
from typing import List, Tuple

from fastapi import UploadFile

from models.schemas import Media

logger = getLogger(__name__)


class BaseThread(Thread):
    def __init__(
        self,
        queue: Queue,
        stop_event: Event,
        with_event_loop: bool = False,
    ) -> None:
        super().__init__()
        self.stop_event = stop_event
        self.queue = queue
        self.__with_event_loop = with_event_loop

    def func(self) -> None:
        raise NotImplementedError("Must be overwrite method `func`")

    async def async_func(self) -> None:
        raise NotImplementedError("Must be overwrite async method `async_func`")

    async def __run_async(self) -> None:
        while not self.stop_event.is_set():
            await self.async_func()

    def __run_sync(self) -> None:
        while not self.stop_event.is_set():
            self.func()

    def run(self) -> None:
        logger.debug(
            "(%s: %s) Start cycle",
            self.__class__.__name__,
            self.native_id,
        )

        if self.__with_event_loop:
            asyncio.run(self.__run_async())
        else:
            self.__run_sync()

        logger.debug(
            "(%s: %s) Stop cycle",
            self.__class__.__name__,
            self.native_id,
        )

    def stop(self, timeout: float | int = 10) -> None:
        self.queue.put(None)
        self.join(timeout)

        logger.debug(
            "(%s: %s) Stopped",
            self.__class__.__name__,
            self.native_id,
        )


class WriteThread(BaseThread):
    def func(self) -> None:
        item: Tuple[Media, bytes] | None = self.queue.get()

        if item is None:
            self.queue.task_done()
            return

        media, file = item
        media_path = Path(media.file)

        with media_path.open(mode="wb") as write_file:
            write_file.write(file)

        self.queue.task_done()


class ReadThread(BaseThread):
    def __init__(
        self,
        queue: Queue,
        queue_to_write: Queue,
        stop_event: Event,
        with_event_loop: bool = True,
    ) -> None:
        super().__init__(queue, stop_event, with_event_loop)
        self.queue_to_write = queue_to_write

    async def async_func(self) -> None:
        item: Tuple[List[Media], List[UploadFile]] | None = self.queue.get()

        if item is None:
            self.queue.task_done()
            return

        medias, upload_files = item

        tasks = [file.read() for file in upload_files]

        files: List[bytes] = await gather(*tasks)  # noqa

        for media, file in zip(medias, files):
            self.queue_to_write.put((media, file))

        self.queue.task_done()
