# link between MediaPlayer.playlist and Canvas
from PySide6 import QtGui
from viewportmapper.ndc import NDCViewportMapper
from paintcanvas import CanvasModel, render_annotation
from dwramplayer.playlist import Playlist
from dwramplayer.decoder import numpy_to_qpixmap, qpixmap_to_ndarray


class Session:
    def __init__(self, playlist: Playlist):
        self.playlist = playlist
        self.annotations = {}

    def get_annotation_at(
            self, frame: int,
            viewportmapper: NDCViewportMapper) -> CanvasModel:
        relative_frame = self.playlist.frames_frames[frame]
        container = self.playlist.frames_containers[frame]
        return self.annotations.get(
            (container.id, relative_frame), CanvasModel(viewportmapper))

    def delete_annotation_at(self, frame: int):
        relative_frame = self.playlist.frames_frames[frame]
        container = self.playlist.frames_containers[frame]
        if (container.id, relative_frame) in self.annotations:
            del self.annotations[(container.id, relative_frame)]

    def add_annotation_at(self, frame: int, annotation: CanvasModel):
        relative_frame = self.playlist.frames_frames[frame]
        container = self.playlist.frames_containers[frame]
        self.annotations[(container.id, relative_frame)] = annotation

    def get_current_container(self):
        return self.playlist.frames_containers[self.playlist.frame]

    def render_frame(self, frame: int):
        array = self.playlist.get_and_cache_frame(frame)
        pixmap = numpy_to_qpixmap(array)
        viewportmapper = NDCViewportMapper(
            view_size=pixmap.size(),
            image_size=pixmap.size())
        annotation = self.get_annotation_at(frame, viewportmapper)
        painter = QtGui.QPainter(pixmap)
        render_annotation(
            painter=painter,
            viewportmapper=viewportmapper,
            model=annotation)
        painter.end()
        return pixmap

    def cache_annotations(self):
        self.playlist.frames_images_overrides.clear()
        for (container_id, frame) in self.annotations:
            frame = self.playlist.first_frames[container_id] + frame
            pixmap = self.render_frame(frame)
            array = qpixmap_to_ndarray(pixmap)
            self.playlist.frames_images_overrides[frame] = array

    def serialize(self):
        return {
            'containers': [
                [container.id, container.path] for container in
                self.playlist.containers],
            'annotations': [
                [container_id, frame, model.serialize()]
                for (container_id, frame), model in self.annotations.items()]}

    def get_annotated_frames(self):
        return sorted([
            self.playlist.first_frames[container_id] + frame
            for (container_id, frame) in self.annotations])
