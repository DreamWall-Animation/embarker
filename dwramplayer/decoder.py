import os
import glob
import uuid

import av
import numpy as np
import OpenImageIO as oiio
from PySide6 import QtGui


class VideoContainer:
    def __init__(self, video_path, container_id=None):
        self.id = container_id or str(uuid.uuid4())
        self.path = video_path
        self.has_alpha = False
        self.container = av.open(video_path, metadata_errors='ignore')
        self.stream = self.container.streams.video[0]
        self.stream.thread_type = 'AUTO'  # Important for performance

        self.duration = float(self.stream.duration * self.stream.time_base)
        self.length = self.stream.frames
        self.fps = float(
            self.stream.frames / self.stream.duration / self.stream.time_base)

        self._reset_decoder()

    def _reset_decoder(self):
        self.video_frame = None
        self.container.seek(0)
        self.stream = self.container.streams.video[0]
        self.decoder = self.container.decode(self.stream)

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


class ImageSequenceContainer:
    def __init__(self, image_path, fps=25.0, container_id=None):
        self.id = container_id or str(uuid.uuid4())
        self.path: str = image_path
        self.basename, self.ext = os.path.splitext(self.path)
        self.has_alpha = self.ext in '.exr', '.png'
        self.paths = self.search_for_other_images()
        self.length: int = len(self.paths)
        self.fps: float = fps
        self.duration: float = self.length / self.fps

    def search_for_other_images(self):
        for i, char in enumerate(reversed(self.basename)):
            if not char.isdigit():
                break
        prefix = self.basename[:-i]
        return glob.glob(f'{prefix}*{self.ext}')

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
    arr = np.frombuffer(ptr, dtype=np.uint8).reshape((h, w, 3)).copy()
    return arr
