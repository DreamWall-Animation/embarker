import os
import threading
from functools import lru_cache

from PySide6 import QtCore
import numpy as np

from dwramplayer.decoder import VideoContainer, ImageSequenceContainer


VIDEO_EXTENSIONS = 'mp4', 'mov', 'avi', 'mkv'
IMAGE_EXTENSIONS = 'exr',
EXTENSIONS = VIDEO_EXTENSIONS + IMAGE_EXTENSIONS


class Playlist(QtCore.QObject):
    def __init__(
            self,
            video_paths=None,
            buffer_pre_size=20,
            buffer_post_size=60):

        self.buffer_pre_size = buffer_pre_size
        self.buffer_post_size = buffer_post_size

        self.frame = 0
        self.playback_start: int|None = None
        self.playback_end: int|None = None
        self.playback_loop: bool = True
        self.frames_count = 0
        self.first_frames: dict[str, int] = dict()

        # by frame dicts
        self.frames_paths: dict[int, str] = dict()
        self.frames_frames: dict[int, int] = dict()  # global idx to video idx
        self.frames_times: dict[int, float] = dict()
        self.frames_containers: dict[int, VideoContainer] = dict()
        self.frames_images: dict[int, object] = dict()
        # Dict to replace image for some frames:
        self.frames_images_overrides: dict[int, np.array] = dict()
        self.frames_fps: dict[int, float] = dict()
        self.frames_hasalpha: dict[int, bool] = dict()

        self.buffer_updater = UpdateBufferThread(self)

        # startup
        if video_paths:
            self.load_videos(video_paths)

    def load_videos(self, video_paths, container_ids=None):
        self.first_frames.clear()
        self.frames_paths.clear()
        self.frames_images.clear()
        self.frames_hasalpha.clear()
        self.frames_count = 0
        previous_time = 0
        paths_durations = dict()
        container_ids = container_ids or [None] * len(video_paths)
        for video_path, container_id in zip(video_paths, container_ids):
            if video_path.endswith(VIDEO_EXTENSIONS):
                try:
                    container = VideoContainer(
                        video_path=video_path, container_id=container_id)
                except RuntimeError:
                    print(f'Could not open {video_path}')
                    continue
            else:
                try:
                    container = ImageSequenceContainer(
                        video_path=video_path, container_id=container_id)
                except IndexError:
                    print(f'Could not open {video_path}')
                    continue
            self.first_frames[container.id] = self.frames_count
            length = container.length
            # read first frame to get shape
            fps = container.fps
            duration = length / fps
            paths_durations[video_path] = duration
            print(
                f'    Loading {os.path.basename(video_path)}, '
                f'{length} frames @ {fps}fps')
            framerange = range(self.frames_count, self.frames_count + length)
            for video_frame, playlist_frame in enumerate(framerange):
                self.frames_times[playlist_frame] = (
                    previous_time + video_frame / fps)
                self.frames_frames[playlist_frame] = video_frame
                self.frames_paths[playlist_frame] = video_path
                self.frames_containers[playlist_frame] = container
                self.frames_fps[playlist_frame] = fps
                self.frames_hasalpha[playlist_frame] = container.has_alpha
            previous_time += duration  # for more accuracy
            self.frames_count += length

        self.get_and_cache_frame(0)  # fire up cache loader
        return self.frames_count, paths_durations

    def get_and_cache_frame(self, frame: int):
        try:
            return self.frames_images[frame]
        except KeyError:
            pass
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

    @property
    def containers(self):
        return [self.frames_containers[f] for f in self.first_frames.values()]


class UpdateBufferThread:
    def __init__(self, playlist):
        self.playlist: Playlist = playlist
        self.running = False
        self.abort = False

    def start(self):
        self.thread = threading.Thread(target=self.run)
        self.thread.start()

    def run(self):
        self.running = True
        for frame in self.playlist.get_frames_to_cache():
            if self.abort:
                self.running = False
                return
            if frame in self.playlist.frames_images:
                continue
            container = self.playlist.frames_containers[frame]
            try:
                self.playlist.frames_images[frame] = container.decode_frame(
                    frame)
            except ValueError:
                # next(self.decoder) => ValueError: generator already executing
                break
        self.playlist.clear_extra_cache()
        self.running = False


@lru_cache()
def get_frames_to_cache(center, before, after, max_value, min_value=0):
    count = before + after  # if we cannot buffer before, we buffer more after
    first = max(min_value, center - before)
    last = min(max_value, first + count - 1)
    if last == max_value:
        first = last - count
    return list(range(first, last + 1))


if __name__ == '__main__':
    from os.path import expandvars
    pl = Playlist([
        expandvars('$SAMPLES/ep311_sq0060_sh0880_spline_v003.mov'),
        expandvars('$SAMPLES/ep311_sq0060_sh0880_spline_v003.mov')])
