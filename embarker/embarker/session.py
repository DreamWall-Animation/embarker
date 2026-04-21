# link between MediaPlayer.playlist and Canvas
from PySide6 import QtGui, QtCore
from viewportmapper import NDCViewportMapper

from paintcanvas import CanvasModel, render_annotation
from embarker.appinfos import VERSION
from embarker.decoder import (
    VideoContainer, ImageSequenceContainer,
    qpixmap_to_ndarray, numpy_to_qpixmap)
from embarker.onionskin import OnionSkin
from embarker.playlist import Playlist


class Session:
    def __init__(self, playlist: Playlist):
        self.filepath = None
        self.playlist = playlist
        self.annotations = {}
        self.onionskin = OnionSkin(playlist)
        self.metadata = {}

    def is_empty(self):
        return self.filepath is None and not self.playlist.containers

    def clear_empty_annotations(self):
        self.annotations = {
            k: v for k, v in self.annotations.items() if not v.is_null()}

    def get_annotation_at(
            self,
            frame: int,
            viewportmapper: NDCViewportMapper = None)-> CanvasModel | None:
        """
        Return CanvasModel at timeline absolute frame.
        """
        if not self.playlist.containers:
            return CanvasModel(viewportmapper) if viewportmapper else None
        relative_frame = self.playlist.frames_frames[frame]
        container = self.playlist.frames_containers[frame]
        return self.annotations.get(
            (container.id, relative_frame),
            CanvasModel(viewportmapper) if viewportmapper else None)

    def get_container_annotations(
            self, container_id,
            include_empty_current_frame=False,
            exportable_only=False):
        """
        Return annotations on given container id
        """
        annotations = {
            (id_, relative_frame): a for
            (id_, relative_frame), a in
            self.annotations.items() if
            container_id == id_ and
            (not exportable_only or a.metadata.get('exportable', True)) }
        if not include_empty_current_frame:
            return annotations
        relative_frame = self.playlist.frames_frames[self.playlist.frame]
        index = (container_id, relative_frame)
        if index not in annotations:
            annotations[index] = self.get_annotation_at(self.playlist.frame)
        return annotations

    def delete_annotation_at(self, frame: int):
        """
        Delete CanvasModel at timeline absolute frame.
        """
        relative_frame = self.playlist.frames_frames[frame]
        container = self.playlist.frames_containers[frame]
        if (container.id, relative_frame) in self.annotations:
            del self.annotations[(container.id, relative_frame)]
        if frame in self.playlist.frames_images_overrides:
            del self.playlist.frames_images_overrides[frame]

    def add_annotation_at(self, frame: int, annotation: CanvasModel):
        """
        Add CanvasModel at timeline absolute frame
        """
        relative_frame = self.playlist.frames_frames[frame]
        container = self.playlist.frames_containers[frame]
        self.annotations[(container.id, relative_frame)] = annotation
        self.annotations = dict(sorted(
            self.annotations.items(),
            key=lambda a: (self.playlist.first_frames[a[0][0]], a[0][1])))

    def get_current_container_index(self) -> int:
        "Return the current container index"
        return self.playlist.get_container_index(self.playlist.frame)

    def get_current_container(self) -> VideoContainer | ImageSequenceContainer:
        """
        Return media container at current frame.
        """
        if self.playlist.frame == -1:
            return None
        if self.playlist.frame not in self.playlist.frames_containers:
            return None
        return self.playlist.frames_containers[self.playlist.frame]

    def get_current_annotation(self) -> CanvasModel:
        """
        Return CanvasModel at current frame.
        """
        if self.playlist.frame not in self.get_annotated_frames():
            return None
        relative_frame = self.playlist.frames_frames[self.playlist.frame]
        container = self.get_current_container()
        return self.annotations.get((container.id, relative_frame))

    def get_container(
            self, container_id) -> VideoContainer | ImageSequenceContainer:
        frame = self.playlist.first_frames[container_id]
        return self.playlist.frames_containers[frame]

    def cache_current_annotation(self):
        annotation = self.get_current_annotation()
        if not annotation or annotation.is_null():
            if self.playlist.frame in self.playlist.frames_images_overrides:
                del self.playlist.frames_images_overrides[self.playlist.frame]
            return
        pixmap = self.render_frame(self.playlist.frame)
        array = qpixmap_to_ndarray(pixmap)
        self.playlist.frames_images_overrides[self.playlist.frame] = array

    def cache_annotations(self, force=True):
        if force:
            self.playlist.frames_images_overrides.clear()
        for (container_id, frame) in self.annotations:
            frame = self.playlist.first_frames[container_id] + frame
            if frame in self.playlist.frames_images_overrides and not force:
                continue
            pixmap = self.render_frame(frame)
            array = qpixmap_to_ndarray(pixmap)
            self.playlist.frames_images_overrides[frame] = array

    def render_frame(self, frame, background=True):
        array = self.playlist.get_and_cache_frame(frame)
        if background:
            pixmap = numpy_to_qpixmap(array)
        else:
            pixmap = QtGui.QPixmap(numpy_to_qpixmap(array).size())
            pixmap.fill(QtCore.Qt.transparent)
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

    def render_container_annotated_frames(
            self, container_id) -> dict[int, QtGui.QPixmap]:

        start_frame = self.playlist.first_frames[container_id]
        annotations = [
            annotation for annotation, model in self.annotations.items()
            if annotation[0] == container_id and
            model.metadata.get('exportable', True)]
        r = {}
        for _, frame in annotations:
            r[frame] = self.render_frame(start_frame + frame)
        return r

    def serialize(self):
        return {
            'version': VERSION,
            'containers': [
                [container.id, container.path, container.metadata]
                for container in self.playlist.containers],
            'annotations': [
                [container_id, frame, model.serialize()]
                for (container_id, frame), model in self.annotations.items()],
            'metadata': self.metadata}

    def get_annotated_frames(self):
        return sorted([
            self.playlist.first_frames[container_id] + frame
            for (container_id, frame) in self.annotations])

    def get_containers_in_range(self, start_frame, end_frame):
        container_ids = []
        lenght = max(self.playlist.frames_containers.keys())
        end_frame = min((end_frame, lenght))
        for frame in range(start_frame, end_frame):
            container = self.playlist.frames_containers[frame]
            if container.id not in container_ids:
                container_ids.append(container.id)
        return [self.get_container(id_) for id_ in container_ids]

