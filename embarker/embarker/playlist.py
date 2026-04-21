from functools import lru_cache

from PySide6 import QtCore
import numpy as np

from embarker.decoder import VideoContainer, get_container


class Playlist(QtCore.QObject):
    playlist_modified = QtCore.Signal()

    def __init__(
            self,
            video_paths=None,
            buffer_pre_size=20,
            buffer_post_size=60):

        super().__init__()

        self._audio_volume = 1.0  # maximum 1.0
        self.buffer_pre_size = buffer_pre_size
        self.buffer_post_size = buffer_post_size


        self.frame = 0
        self.playback_start: int | None = None
        self.playback_end: int | None = None
        self.playback_loop: bool = True
        self.mute_annotations: bool = False
        self.frames_count = 0
        self._containers: list[VideoContainer] = []
        self.first_frames: dict[str, int] = dict()

        # by frame dicts
        self.frames_paths: dict[int, str] = dict()
        self.frames_frames: dict[int, int] = dict()  # global index to video index
        self.frames_times: dict[int, float] = dict()
        self.frames_containers: dict[int, VideoContainer] = dict()
        self.frames_images: dict[int, object] = dict()

        # Dict to replace image for some frames:
        self.frames_images_overrides: dict[int, np.array] = dict()
        self.frames_fps: dict[int, float] = dict()
        self.frames_hasalpha: dict[int, bool] = dict()

        self.audio_samples: np.array = np.array([])

        # startup
        if video_paths:
            self.load_videos(video_paths)

    def load_videos(self, video_paths, metadatas=None, container_ids=None):
        self._containers.clear()
        metadatas = metadatas or [None] * len(video_paths)
        container_ids = container_ids or [None] * len(video_paths)
        iterator = zip(video_paths, metadatas, container_ids)
        for video_path, metadata, container_id in iterator:
            container = get_container(video_path, metadata, container_id)
            if not container:
                continue
            self._containers.append(container)

        return self.build_playlist()

    def build_playlist(self):
        self.first_frames.clear()
        self.frames_paths.clear()
        self.frames_images.clear()
        self.frames_hasalpha.clear()
        self.frames_times.clear()
        self.frames_images_overrides.clear()
        self.frames_count = 0
        previous_time = 0
        paths_durations = dict()

        for container in self._containers:
            self.first_frames[container.id] = self.frames_count
            # read first frame to get shape
            duration = container.length / container.fps
            paths_durations[container.path] = duration
            framerange = range(
                self.frames_count, self.frames_count + container.length)
            for video_frame, playlist_frame in enumerate(framerange):
                self.frames_times[playlist_frame] = (
                    previous_time + video_frame / container.fps)
                self.frames_frames[playlist_frame] = video_frame
                self.frames_paths[playlist_frame] = container.path
                self.frames_containers[playlist_frame] = container
                self.frames_fps[playlist_frame] = container.fps
                self.frames_hasalpha[playlist_frame] = container.has_alpha
            previous_time += duration  # for more accuracy
            self.frames_count += container.length

        # Decode current frame
        if self.frame > self.frames_count - 1:
            self.frame = self.frames_count - 1
        self.get_and_cache_frame(self.frame)
        # Concatenate audio
        self._build_audio()

        self.playlist_modified.emit()

        return self.frames_count, paths_durations

    def _build_audio(self):
        """concatenate containers audio arrays"""
        if not self.containers:
            self.audio_samples = np.array([])
            return self.playlist_modified.emit()
        self.audio_samples = np.concatenate(
            [c.audio_samples for c in self._containers], axis=0)
        if self._audio_volume != 1:
            gain = volume_to_gain(self._audio_volume)
            self.audio_samples *= gain

    def set_volume(self, value):
        self._audio_volume = value
        self._build_audio()

    def mute(self):
        self.audio_samples = np.zeros(
            self.audio_samples.shape, dtype=np.float32)

    def unmute(self):
        self._build_audio()

    def get_container_index(self, frame=None):
        frame = self.frame if frame is None else frame
        container_to_find = self.frames_containers[frame]
        for i, container in enumerate(self._containers):
            if container.id == container_to_find.id:
                return i

    def clear(self):
        self._containers = []
        self.build_playlist()

    def remove_video(self, index=None):
        index = self.get_container_index() if index is None else index
        self._containers.pop(index)
        self.build_playlist()

    def replace_video(
            self, video_path, container_id, metadata=None, index=None,
            keep_id=True):
        container = get_container(video_path, metadata, container_id)
        if not container:
            return
        index = self.get_container_index() if index is None else index
        if keep_id:
            container.id = self._containers[index].id
        self._containers[index] = container
        self.build_playlist()

    def add_video(
            self, video_path, metadata=None, container_id=None, index=-1,
            build=True):
        index = len(self._containers) if index == -1 else index
        container = get_container(video_path, metadata, container_id)
        if not container:
            return
        index = self.get_container_index() if index is None else index
        self._containers.insert(index, container)
        if build:
            self.build_playlist()

    def get_and_cache_frame(self, frame: int):
        try:
            return self.frames_images[frame]
        except KeyError:
            pass
        if not self.containers:
            return None
        container = self.frames_containers[frame]
        video_frame = self.frames_frames[frame]
        image = container.decode_frame(video_frame)
        self.frames_images[frame] = image
        return image

    def get_frames_to_cache(self):
        return get_frames_to_cache(
            self.frame,
            self.buffer_pre_size, self.buffer_post_size,
            self.frames_count)

    def clear_extra_cache(self):
        """
        Clear caches frame outside of asked cache range
        """
        to_keep = self.get_frames_to_cache() + list(self.first_frames.values())
        count = len(to_keep)
        if len(self.frames_images) < count:
            return
        for frame in list(self.frames_images):
            if frame not in to_keep:
                del self.frames_images[frame]
                if len(self.frames_images) < count:
                    return

    def get_playback_range(self):
        return (
            self.playback_start or 0,
            self.playback_end or self.frames_count - 1)

    def set_containters(self, containers):
        self._containers = containers
        self.build_playlist()

    @property
    def containers(self):
        return [self.frames_containers[f] for f in self.first_frames.values()]


@lru_cache()
def get_frames_to_cache(center, before, after, max_value, min_value=0):
    count = before + after  # if we cannot buffer before, we buffer more after
    first = max(min_value, center - before)
    last = min(max_value, first + count - 1)
    if last == max_value:
        first = last - count
    return list(range(first, last + 1))


def volume_to_gain(value, db_range=60):
    value = min(value, 1)
    return 10 ** ((value - 1) * db_range / 20)
