import os
import glob
import uuid
from concurrent.futures import ThreadPoolExecutor

import av
import numpy as np
import OpenImageIO as oiio
from PySide6 import QtCore, QtGui

from embarker.audio import create_silence_samples, extract_audio_samples


VIDEO_EXTENSIONS = 'mp4', 'mov', 'avi', 'mkv'
IMAGE_EXTENSIONS = 'exr', 'png', 'jpg', 'jpeg', 'tif', 'tiff', 'webp'
EXTENSIONS = VIDEO_EXTENSIONS + IMAGE_EXTENSIONS


class VideoContainer:
    def __init__(
            self, video_path, metadata=None,
            container_id=None, no_sound=False):
        self.id = container_id or str(uuid.uuid4())
        self.path = os.path.expandvars(video_path)
        self.has_alpha = False
        self.container = av.open(self.path)
        self.stream = self.container.streams.video[0]
        self.stream.thread_type = 'AUTO'  # Important for performance
        self._metadata = metadata or {}

        self.duration = float(self.stream.duration * self.stream.time_base)
        self.length = self.stream.frames
        self.fps = float(
            self.stream.frames / self.stream.duration / self.stream.time_base)

        self.audio_samples = None
        self._no_sound = no_sound
        self.load_audio()

        self._reset_decoder()
        self._thumbnails = {}

    def activate_sound(self):
        if self._no_sound:
            self._no_sound = False
            self.load_audio()

    def serialize(self):
        return {
            'type': 'video',
            'kwargs': {
                'video_path': self.path,
                'metadata': self._metadata or None,
                'no_sound': self._no_sound,
                'container_id': self.id}}

    def _reset_decoder(self):
        self.video_frame = None
        self.container.seek(0)
        self.stream = self.container.streams.video[0]
        self.decoder = self.container.decode(self.stream)

    def load_audio(self):
        if self._no_sound:
            self.audio_samples = create_silence_samples(self.duration)
            return
        self.audio_samples = extract_audio_samples(self.path, self.duration)

    def thumbnail(self, height, frame=0) -> tuple[QtGui.QPixmap, int]:
        thumbnail = self._thumbnails.get(frame, {}).get(height)
        if thumbnail:
            return thumbnail

        thumbnails = self._thumbnails.setdefault(frame, {})

        decoded_image = self.decode_frame(frame)
        pixmap = numpy_to_qpixmap(decoded_image)
        ratio = pixmap.width() / pixmap.height()
        width = height * ratio
        thumbnails[height] = pixmap.scaled(width, height), width
        return thumbnails[height]

    @property
    def metadata(self):
        metadata = {}
        metadata.update(self._metadata)
        metadata.update(self.container.metadata)
        return metadata

    def set_metadata(self, key, value):
        self._metadata[key] = value

    def delete_metadata(self, key):
        if key in self._metadata:
            del self._metadata[key]

    @property
    def next_frame(self):
        if self.video_frame is None:
            return 0
        return int(round(self.video_frame.time * self.fps)) + 1

    def decode_next_frame(self) -> QtGui.QPixmap:
        self.video_frame = next(self.decoder)
        return self.video_frame.to_ndarray(format='rgb24')

    def _seek(self, frame):
        """Ensure decode_next_frame() outputs `frame` arg"""
        while self.next_frame != frame:
            self.video_frame = next(self.decoder)

    def _seek_to_keyframe(self, frame):
        if frame == 0:
            return self._reset_decoder()
        timestamp = int((frame - 1) / self.fps / self.stream.time_base)
        self.container.seek(timestamp, stream=self.stream)
        self.stream = self.container.streams.video[0]
        self.decoder = self.container.decode(self.stream)
        self.video_frame = None

    def decode_frame(self, frame):
        if frame < self.next_frame or frame - self.next_frame > self.fps:
            self._seek_to_keyframe(frame)
        self._seek(frame)
        return self.decode_next_frame()

    def __repr__(self):
        message = ''
        for stream in self.container.streams:
            codec = stream.codec_context.name if stream.codec_context else ''
            message += (
                f'Stream {stream.index} - Type: {stream.type}\n'
                f'Codec: {codec}\n')
        return message


class ImageSequenceContainer:
    def __init__(
            self, path_pattern, fps=25.0, metadata=None, container_id=None):
        self.id = container_id or str(uuid.uuid4())
        self.path: str = path_pattern
        self.paths = glob.glob(self.path)
        _, self.ext = os.path.splitext(self.path)
        self.has_alpha = self.ext in ('.exr', '.png')
        self.length: int = len(self.paths)
        self.fps: float = fps
        self.duration: float = self.length / self.fps
        self.metadata = metadata or {}
        self._thumbnails = {}

        self.audio_samples = None
        self.load_audio()

    def serialize(self):
        return {
            'type': 'image',
            'kwargs': {
                'path_pattern': self.path,
                'fps': self.fps,
                'metadata': self.metadata or None,
                'container_id': self.id}}

    def load_audio(self):
        self.audio_samples = create_silence_samples(self.duration)

    def decode_frame(self, frame):
        path = self.paths[frame]

        if path.lower().endswith('.webp'):
            # QImage is threadsafe, not QPixmap:
            img = QtGui.QImage(path).convertToFormat(
                QtGui.QImage.Format.Format_RGBA8888)
            w, h = img.width(), img.height()
            arr = np.frombuffer(img.bits(), dtype=np.uint8).reshape((h, w, 4))
            return arr.copy()

        image_input = oiio.ImageInput.open(path)
        image = image_input.read_image(format='uint8')
        spec = image_input.spec()
        image_input.close()

        # We dont want bbox size but instead whole image size:
        cropped = np.array(image).reshape(
            spec.height, spec.width, spec.nchannels)
        full = np.zeros(
            (spec.full_height, spec.full_width, spec.nchannels),
            dtype=np.uint8)
        x, y = spec.x, spec.y
        full[y:y+spec.height, x:x+spec.width, :] = cropped
        return full

    def thumbnail(self, height, frame=0):
        # TODO: maybe need to clear it if it gets too large
        if height in self._thumbnails:
            return self._thumbnails[height]

        decoded_image = self.decode_frame(frame)
        pixmap = numpy_to_qpixmap(decoded_image)
        ratio = pixmap.width() / pixmap.height()
        width = height * ratio
        self._thumbnails[height] = pixmap.scaled(width, height), width
        return self._thumbnails[height]

    def set_metadata(self, key, value):
        self.metadata[key] = value

    def delete_metadata(self, key):
        if key in self.metadata:
            del self.metadata[key]


class MultiContainer:
    def __init__(
            self, containers,
            layout='horizontal',
            container_id=None,
            max_pixels=2_073_600):
        self.id = container_id or str(uuid.uuid4())
        self.layout = layout  # "horizontal" | "vertical" | "grid" | "thumbnail"
        self.max_pixels = max_pixels  # default 2_073_600 = 1920×1080
        self.thumbnail_height_proportion = 0.3
        self.thumbnail_opacity = 1.0  # 0.0 = fully transparent, 1.0 = opaque

        self._containers = list(containers)
        self._last_frame_cache: dict[int, np.ndarray] = {}
        self._executor = ThreadPoolExecutor(max_workers=len(self._containers))

    @property
    def main_container(self):
        return self._containers[0]

    @property
    def side_containers(self):
        return self._containers[1:]

    def delete_side_containers(self, ids):
        self._containers = [
            container for i, container in enumerate(self._containers) if
            i == 0 or container.id not in ids]

    def add_side_container(self, container):
        self._containers.append(container)
        self._executor = ThreadPoolExecutor(max_workers=len(self._containers))
        self._last_frame_cache.clear()

    def serialize(self):
        return {
            'type': 'multi',
            'kwargs': {
                'containers': [c.serialize() for c in self._containers],
                'layout': self.layout,
                'container_id': self.id}}

    @staticmethod
    def deserialize(containers, **kwargs):
        containers = [deserialize_container(c) for c in containers]
        return MultiContainer(containers, **kwargs)

    @property
    def has_alpha(self):
        values = {c.has_alpha for c in self._containers}
        return values.pop() if len(values) == 1 else False

    @property
    def path(self):
        return self._containers[0].path

    def _first_video(self):
        for c in self._containers:
            if isinstance(c, VideoContainer):
                return c
        return self._containers[0]

    @property
    def fps(self):
        return self._first_video().fps

    @property
    def metadata(self):
        return self._containers[0].metadata

    @property
    def container(self):
        return self._containers[0].container

    @property
    def duration(self):
        return self._first_video().duration

    @property
    def length(self):
        return self._first_video().length

    @property
    def audio_samples(self):
        return self._first_video().audio_samples

    def thumbnail(self, height, frame=0):
        return self._containers[0].thumbnail(height, frame)

    def set_metadata(self, key, value):
        self._containers[0].set_metadata(key, value)

    def delete_metadata(self, key):
        self._containers[0].delete_metadata(key)

    def _frame_or_fallback(self, container, frame):
        if frame < container.length:
            return container.decode_frame(frame)
        if isinstance(container, ImageSequenceContainer):
            if container.id not in self._last_frame_cache:
                print('store frame')
                self._last_frame_cache[container.id] = container.decode_frame(
                    container.length - 1)
            return self._last_frame_cache[container.id]
        # VideoContainer: use stream metadata to build black frame without
        # decoding.
        h = container.stream.height
        w = container.stream.width
        channels = 4 if container.has_alpha else 3
        return np.zeros((h, w, channels), dtype=np.uint8)

    def decode_frame(self, frame):
        raw = list(self._executor.map(
            lambda c: self._frame_or_fallback(c, frame), self._containers))
        if not self.has_alpha:
            # Mixed or all-RGB: strip alpha from any RGBA frames
            raw = [f[..., :3] if f.shape[2] == 4 else f for f in raw]
        frames = _unify_channels(raw)

        if self.layout == 'horizontal':
            return self.combine_horizontal_layout(frames)

        if self.layout == 'vertical':
            return self.combine_vertical_layout(frames)

        if self.layout == 'thumbnail':
            return self.combine_thumnbails_layout(frames)

        return self.combine_grid_layout(frames)

    def combine_horizontal_layout(self, frames):
        target_h = max(f.shape[0] for f in frames)
        resized_arrays = [
            _resize_array(
                f, target_h, int(f.shape[1] * target_h / f.shape[0]))
            for f in frames]
        return self._apply_max_pixels(np.concatenate(resized_arrays, axis=1))

    def combine_vertical_layout(self, frames):
        target_w = max(f.shape[1] for f in frames)
        resized_arrays = [
            _resize_array(
                f, int(f.shape[0] * target_w / f.shape[1]), target_w)
            for f in frames]
        return self._apply_max_pixels(np.concatenate(resized_arrays, axis=0))

    def combine_thumnbails_layout(self, frames):
        main = frames[0]
        main_h, main_w = main.shape[:2]
        thumb_h = max(1, int(main_h * self.thumbnail_height_proportion))
        result = main.copy()
        x_offset = 0
        for thumb_frame in frames[1:]:
            ratio = thumb_frame.shape[1] / thumb_frame.shape[0]
            thumb_w = max(1, int(thumb_h * ratio))
            if x_offset + thumb_w > main_w:
                break
            resized = _resize_array(thumb_frame, thumb_h, thumb_w)
            region = result[:thumb_h, x_offset:x_offset + thumb_w]
            if self.thumbnail_opacity < 1.0:
                a = self.thumbnail_opacity
                blended = (
                    a * resized.astype(np.float32)
                    + (1 - a) * region.astype(np.float32)
                ).astype(np.uint8)
                result[:thumb_h, x_offset:x_offset + thumb_w] = blended
            else:
                result[:thumb_h, x_offset:x_offset + thumb_w] = resized
            x_offset += thumb_w
        return result

    def combine_grid_layout(self, frames):
        n = len(frames)
        cols = int(np.ceil(np.sqrt(n)))
        rows = int(np.ceil(n / cols))
        target_h = frames[0].shape[0]
        target_w = frames[0].shape[1]
        ch = frames[0].shape[2]

        normalized = [
            _pad_width(_pad_height(f, target_h), target_w) for f in frames]

        if len(normalized) < rows * cols:
            blank = np.zeros((target_h, target_w, ch), dtype=frames[0].dtype)
            normalized += [blank] * (rows * cols - n)

        result = np.concatenate([
            np.concatenate(normalized[r * cols:(r + 1) * cols], axis=1)
            for r in range(rows)], axis=0)
        return self._apply_max_pixels(result)

    def _apply_max_pixels(self, arr):
        if self.max_pixels is None:
            return arr
        h, w = arr.shape[:2]
        if self.max_pixels is None or h * w <= self.max_pixels:
            return arr
        scale = (self.max_pixels / (h * w)) ** 0.5
        return _resize_array(arr, int(h * scale), int(w * scale))


def _unify_channels(arrays):
    max_ch = max(a.shape[2] for a in arrays)
    result = []
    for arr in arrays:
        ch = arr.shape[2]
        if ch == max_ch:
            result.append(arr)
        elif ch == 3 and max_ch == 4:
            alpha = np.full(arr.shape[:2] + (1,), 255, dtype=arr.dtype)
            result.append(np.concatenate([arr, alpha], axis=2))
        else:
            result.append(arr[..., :max_ch])
    return result


def _resize_array(arr, new_h, new_w):
    if arr.shape[0] == new_h and arr.shape[1] == new_w:
        return arr
    h, w, ch = arr.shape
    arr_c = np.ascontiguousarray(arr)
    fmt = (
        QtGui.QImage.Format.Format_RGBA8888 if ch == 4
        else QtGui.QImage.Format.Format_RGB888)
    img = QtGui.QImage(arr_c.data, w, h, arr_c.strides[0], fmt)
    img = img.scaled(
        new_w, new_h,
        QtCore.Qt.AspectRatioMode.IgnoreAspectRatio,
        QtCore.Qt.TransformationMode.SmoothTransformation)
    ptr = img.bits()
    bpl = img.bytesPerLine()
    result = np.frombuffer(ptr, dtype=np.uint8).reshape((new_h, bpl))
    return result[:, :new_w * ch].reshape((new_h, new_w, ch)).copy()


def _pad_height(arr, target_h):
    h = arr.shape[0]
    if h >= target_h:
        return arr[:target_h]
    pad = np.zeros(
        (target_h - h, arr.shape[1], arr.shape[2]), dtype=arr.dtype)
    return np.concatenate([arr, pad], axis=0)


def _pad_width(arr, target_w):
    w = arr.shape[1]
    if w >= target_w:
        return arr[:, :target_w]
    pad = np.zeros(
        (arr.shape[0], target_w - w, arr.shape[2]), dtype=arr.dtype)
    return np.concatenate([arr, pad], axis=1)


def deserialize_container(data):
    cls = {
        'video': VideoContainer,
        'image': ImageSequenceContainer,
        'multi': MultiContainer.deserialize}[data['type']]
    return cls(**data['kwargs'])


def build_container(media_path, metadata=None, container_id=None):
    if isinstance(media_path, (list, tuple)):
        containers = [build_container(p) for p in media_path]
        container = MultiContainer(containers, container_id=container_id)
        if metadata:
            for key, value in metadata.items():
                container.set_metadata(key, value)
        return container

    media_path = os.path.expandvars(media_path)
    if media_path.endswith(VIDEO_EXTENSIONS):
        try:
            return VideoContainer(
                video_path=media_path,
                metadata=metadata,
                container_id=container_id)
        except RuntimeError:
            print(f'Could not open {media_path}')
    else:
        try:
            return ImageSequenceContainer(
                path_pattern=media_path,
                metadata=metadata,
                container_id=container_id)
        except IndexError:
            print(f'Could not open {media_path}')


def numpy_to_qpixmap(array: np.ndarray) -> QtGui.QPixmap:
    array = np.ascontiguousarray(array)

    if not (2 <= array.ndim <= 3):
        raise ValueError("Unsupported ndarray shape for QPixmap conversion.")

    if array.ndim == 2:
        height, width = array.shape
        bytes_per_line = array.strides[0]
        image = QtGui.QImage(
            array.data,
            width,
            height,
            bytes_per_line,
            QtGui.QImage.Format_Grayscale8).copy()
        return QtGui.QPixmap.fromImage(image)

    height, width, channels = array.shape
    bytes_per_line = array.strides[0]

    image_format = {
        3: QtGui.QImage.Format.Format_RGB888,
        4: QtGui.QImage.Format.Format_RGBA8888}[channels]

    image = QtGui.QImage(
        array.data,
        width,
        height,
        bytes_per_line,
        image_format).copy()

    if not image:
        raise ValueError("Unsupported ndarray shape for QImage conversion.")

    return QtGui.QPixmap.fromImage(image)


def qpixmap_to_ndarray(pixmap: QtGui.QPixmap) -> np.ndarray:
    # Conversion time is ~0.02 second
    image = pixmap.toImage().convertToFormat(QtGui.QImage.Format.Format_RGB888)
    w, h = image.width(), image.height()
    ptr = image.bits()
    bpl = image.bytesPerLine()  # Manage horizontal padding in memory
    arr = np.frombuffer(ptr, dtype=np.uint8).reshape((h, bpl))
    arr = arr[:, :w*3].reshape((h, w, 3)).copy()
    return arr
