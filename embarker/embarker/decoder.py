import os
import glob
import uuid

import av
import numpy as np
import OpenImageIO as oiio
from PySide6 import QtGui

from embarker.audio import create_silence_samples, extract_audio_samples


VIDEO_EXTENSIONS = 'mp4', 'mov', 'avi', 'mkv'
IMAGE_EXTENSIONS = 'exr', 'png', 'jpg', 'jpeg', 'tif', 'tiff'
EXTENSIONS = VIDEO_EXTENSIONS + IMAGE_EXTENSIONS


class VideoContainer:
    def __init__(self, video_path, metadata=None, container_id=None):
        self.id = container_id or str(uuid.uuid4())
        self.path = os.path.expandvars(video_path)
        self.has_alpha = False
        self.container = av.open(self.path, metadata_errors='ignore')
        self.stream = self.container.streams.video[0]
        self.stream.thread_type = 'AUTO'  # Important for performance
        self._metadata = metadata or {}

        self.duration = float(self.stream.duration * self.stream.time_base)
        self.length = self.stream.frames
        self.fps = float(
            self.stream.frames / self.stream.duration / self.stream.time_base)

        self.audio_samples = None
        self.load_audio()

        self._reset_decoder()

    def _reset_decoder(self):
        self.video_frame = None
        self.container.seek(0)
        self.stream = self.container.streams.video[0]
        self.decoder = self.container.decode(self.stream)

    def load_audio(self):
        self.audio_samples = extract_audio_samples(self.path, self.duration)

    @property
    def metadata(self):
        metadata = {}
        metadata.update(self._metadata)
        metadata.update(self.container.metadata)
        return metadata

    def set_metadata(self, key, value):
        self._metadata[key] = value

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

    def decode_frame(self, frame):
        if frame < self.next_frame:
            self._reset_decoder()  # Rewind to frame 0
        self._seek(frame)
        return self.decode_next_frame()

    # def __repr__(self):
    #     message = ''
    #     for stream in self.container.streams:
    #         codec = stream.codec_context.name if stream.codec_context else " "
    #         message += (
    #             f'Stream {stream.index} - Type: {stream.type}\n'
    #             f'Codec: {codec}\n')
    #     return message


class ImageSequenceContainer:
    def __init__(self, image_path, fps=25.0, metadata=None, container_id=None):
        self.id = container_id or str(uuid.uuid4())
        self.path: str = image_path
        self.basename, self.ext = os.path.splitext(self.path)
        self.has_alpha = self.ext in '.exr', '.png'
        self.paths = self.search_for_other_images()
        self.length: int = len(self.paths)
        self.fps: float = fps
        self.duration: float = self.length / self.fps
        self.metadata = metadata or {}

        self.audio_samples = None
        self.load_audio()

    def load_audio(self):
        self.audio_samples = create_silence_samples(self.duration)

    def search_for_other_images(self):
        for i, char in enumerate(reversed(self.basename)):
            if not char.isdigit():
                break
        prefix = self.basename[:-i]
        paths = glob.glob(f'{prefix}*{self.ext}')
        if not paths:
            return [self.path]
        return paths

    def decode_frame(self, frame):
        image_input = oiio.ImageInput.open(self.paths[frame])
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

    def __repr__(self):
        return ''


def get_container(video_path, metadata=None, container_id=None):
    video_path = os.path.expandvars(video_path)
    if video_path.endswith(VIDEO_EXTENSIONS):
        try:
            return VideoContainer(
                video_path=video_path,
                metadata=metadata,
                container_id=container_id)
        except RuntimeError:
            print(f'Could not open {video_path}')
    else:
        try:
            return ImageSequenceContainer(
                image_path=video_path,
                container_id=container_id)
        except IndexError:
            print(f'Could not open {video_path}')


def numpy_to_qpixmap(array: np.ndarray) -> QtGui.QPixmap:
    if not (2 <= array.ndim <= 3):
        raise ValueError("Unsupported ndarray shape for QPixmap conversion.")

    if array.ndim == 2:  # Greyscale
        height, width = array.shape
        bytes_per_line = width
        image = QtGui.QImage(
            array.data, width, height, bytes_per_line,
            QtGui.QImage.Format_Grayscale8).copy()
        return QtGui.QPixmap.fromImage(image)

    height, width, channels = array.shape
    bytes_per_line = channels * width
    image_format = {
        3: QtGui.QImage.Format.Format_RGB888,
        4: QtGui.QImage.Format.Format_RGBA8888}[channels]
    image = QtGui.QImage(
        array.data, width, height, bytes_per_line,
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
