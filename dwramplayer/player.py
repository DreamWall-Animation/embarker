import time
import ctypes

import numpy as np
from OpenGL import GL as gl
from PySide6 import QtCore
from PySide6.QtOpenGLWidgets import QOpenGLWidget

from viewportmapper import NDCViewportMapper
from dwramplayer.audio import AudioPlayer
from dwramplayer.playlist import Playlist


VERTEX_SHADER = """
#version 330 core
in vec2 position;
in vec2 texCoord;
uniform float zoom;
uniform vec2 origin;
uniform vec2 aspect;
out vec2 vTexCoord;
void main() {
    vec2 scaled = position * zoom * aspect;
    gl_Position = vec4(scaled + origin, 0.0, 1.0);
    vTexCoord = vec2(texCoord.x, 1.0 - texCoord.y);
}
"""

FRAGMENT_SHADER = """
#version 330 core
uniform sampler2D tex;
uniform float brightness;
in vec2 vTexCoord;
out vec4 fragColor;
void main() {
    vec4 color = texture(tex, vTexCoord);
    fragColor = vec4(color.rgb * brightness, color.a);
}
"""


class MediaPlayer(QOpenGLWidget):
    playing_state_changed = QtCore.Signal(bool)
    current_frame_changed = QtCore.Signal()

    def __init__(self, viewportmapper: NDCViewportMapper, playlist: Playlist):
        super().__init__()

        self.previous_size = None

        self.vpm = viewportmapper
        self.playlist = playlist

        self.texture = None
        self.shader_program = None
        self.vao = None
        self.brightness = 1.0

        self.audio_player = AudioPlayer()

        self.playback_timer = QtCore.QTimer(
            self, timerType=QtCore.Qt.TimerType.PreciseTimer)
        self.playback_timer.timeout.connect(self.playback_next_frame)

        self._audio_video_deltas = []
        self._frame_timings = []

    def initializeGL(self):
        gl.glClearColor(0, 0, 0, 1)
        self.shader_program = create_shader_program()
        self.setup_vertex_data()
        self.texture = gl.glGenTextures(1)

        gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture)
        gl.glTexParameteri(
            gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(
            gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(
            gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE)
        gl.glTexParameteri(
            gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)

        # Temporary allocation (will update with real dimensions later)
        gl.glTexImage2D(
            gl.GL_TEXTURE_2D, 0, gl.GL_RGB, 16, 16, 0, gl.GL_RGB,
            gl.GL_UNSIGNED_BYTE, None)

        self.set_frame(0)

    def paintGL(self):
        # Clear and load
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)
        gl.glUseProgram(self.shader_program)

        # Set shader parameters
        zoom_loc = gl.glGetUniformLocation(self.shader_program, 'zoom')
        if zoom_loc != -1:
            gl.glUniform1f(zoom_loc, self.vpm.zoom)

        aspect_loc = gl.glGetUniformLocation(self.shader_program, 'aspect')
        if aspect_loc != -1:
            gl.glUniform2f(
                aspect_loc, self.vpm.aspect.x(), self.vpm.aspect.y())

        origin_loc = gl.glGetUniformLocation(self.shader_program, 'origin')
        if origin_loc != -1:
            gl.glUniform2f(
                origin_loc, self.vpm.origin.x(), self.vpm.origin.y())

        brightness = gl.glGetUniformLocation(self.shader_program, 'brightness')
        gl.glUniform1f(brightness, self.brightness)

        # Draw
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture)
        gl.glBindVertexArray(self.vao)
        gl.glDrawArrays(gl.GL_TRIANGLE_STRIP, 0, 4)

    def _get_current_interval(self):
        return int(1000 / self.playlist.frames_fps[self.playlist.frame])

    def load_videos(self, video_paths, container_ids=None):
        self.frames_count, paths_durations = self.playlist.load_videos(
            video_paths, container_ids)
        self.audio_player.load_videos(paths_durations)
        self.playback_timer.setInterval(self._get_current_interval())
        self.set_frame(0)
        return self.frames_count

    def setup_vertex_data(self):
        vertices = np.array([
            -1, -1, 0, 0,
            1, -1, 1, 0,
            -1,  1, 0, 1,
            1,  1, 1, 1,
        ], dtype=np.float32)

        self.vao = gl.glGenVertexArrays(1)
        vbo = gl.glGenBuffers(1)
        gl.glBindVertexArray(self.vao)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, vbo)
        gl.glBufferData(
            gl.GL_ARRAY_BUFFER, vertices.nbytes, vertices, gl.GL_STATIC_DRAW)

        pos_attr = gl.glGetAttribLocation(self.shader_program, 'position')
        tex_attr = gl.glGetAttribLocation(self.shader_program, 'texCoord')
        gl.glEnableVertexAttribArray(pos_attr)
        gl.glVertexAttribPointer(
            pos_attr, 2, gl.GL_FLOAT, gl.GL_FALSE, 16, ctypes.c_void_p(0))
        gl.glEnableVertexAttribArray(tex_attr)
        gl.glVertexAttribPointer(
            tex_attr, 2, gl.GL_FLOAT, gl.GL_FALSE, 16, ctypes.c_void_p(8))

    def set_brightness(self, value):
        self.brightness = value / 100.0
        self.update()

    def next_frame(self):
        self.pause()
        next_frame = self.playlist.frame + 1
        start, end = self.playlist.get_playback_range()
        if end < next_frame:
            next_frame = start
        self.set_frame(next_frame)

    def previous_frame(self):
        self.pause()
        previous_frame = self.playlist.frame - 1
        start, end = self.playlist.get_playback_range()
        if previous_frame < start:
            previous_frame = end
        self.set_frame(previous_frame)

    def play(self):
        self.playing_state_changed.emit(True)
        frame = self.playlist.frame
        # Clear cache to reset decoders to first frames and ensure smooth
        # playback:
        self.playlist.frames_images.clear()
        # play from start if last frame:
        start, end = self.playlist.get_playback_range()
        if not start <= frame < end:
            frame = self.playlist.frame = start
            self.set_frame(self.playlist.frame)
        # Cache first frames
        for f in self.playlist.first_frames.values():
            self.playlist.get_and_cache_frame(f)
        # Cache next frame
        self.playlist.get_and_cache_frame(frame + 1)
        # Sync audio
        self.set_audio_time()
        # Go
        self.playback_timer.setInterval(self._get_current_interval())
        self.playback_timer.start()
        self.audio_player.start()

    def playback_next_frame(self):
        """
        First, display the image. Then buffer.
        This way, if decoding time varies, it has no direct impact on the
        timing on which the frames are displayed (fps / QTimer.interval)
        """
        # 1. display pre-cached frame:
        self.playlist.frame += 1
        frame = self.playlist.frame
        if frame in self.playlist.frames_images_overrides:
            image = self.playlist.frames_images_overrides[frame]
        else:
            image = self.playlist.frames_images[frame]
        self.draw_image(image, frame)

        # 3. handle playback
        first, last = self.playlist.get_playback_range()
        if last == frame:
            self.playback_timer.stop()
            self.audio_player.pause()
            self.current_frame_changed.emit()
            if self.playlist.playback_loop:
                interval = self._get_current_interval()
                # 1ms is not enough but compensate play() taking a bit of time:
                interval = max(0, interval - 20)
                QtCore.QTimer.singleShot(interval, self.play)
            return

        self.current_frame_changed.emit()
        # 3. decode next frame
        if frame != self.playlist.frames_count - 1:
            # self.playlist.decode_next_playback_frame()
            self.playlist.get_and_cache_frame(frame + 1)
            self.playlist.clear_extra_cache()

        # 4. adapt interval to ensure sync with audio
        delta = self.playlist.frames_times[frame] - self.audio_player.time
        fps = self.playlist.frames_fps[frame]
        self._audio_video_deltas.append(delta)
        self._frame_timings.append(time.time())
        self.playback_timer.setInterval(max(
            0, self._get_current_interval() + int(delta * 1000 / fps * 15)))

    def set_frame(self, frame):
        self.playlist.frame = frame
        self.play_current_frame()
        self.current_frame_changed.emit()

    def play_current_frame(self):
        frame = self.playlist.frame
        image = self.playlist.get_and_cache_frame(frame)
        self.draw_image(image, frame)
        self.playlist.clear_extra_cache()

    def draw_image(self, image, frame):
        has_alpha = self.playlist.frames_hasalpha[frame]
        channels = gl.GL_RGBA if has_alpha else gl.GL_RGB
        # Load frame
        self.image_height, self.image_width, _ = image.shape
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture)

        size = image.shape[1], image.shape[0]
        if image.shape != self.previous_size:
            # Resize texture once if image size changes
            gl.glTexImage2D(
                gl.GL_TEXTURE_2D, 0, channels,
                size[0], size[1], 0,
                channels, gl.GL_UNSIGNED_BYTE, None)
            self.previous_size = size

        gl.glTexSubImage2D(
            gl.GL_TEXTURE_2D, 0,
            0, 0, image.shape[1], image.shape[0],
            channels, gl.GL_UNSIGNED_BYTE,
            image.data)

        # Draw
        self.vpm.image_size = QtCore.QSize(*size)
        self.update()

    def set_audio_time(self):
        self.audio_player.seek(self.playlist.frames_times[self.playlist.frame])

    def _debug_deltas(self):
        import statistics
        ad = self._audio_video_deltas
        if not ad:
            return
        print(min(ad), statistics.mean(ad), max(ad))
        deltas = [
            self._frame_timings[i - 1] - self._frame_timings[i]
            for i in range(len(self._frame_timings))][1:]
        print(min(deltas), statistics.mean(deltas), max(deltas))
        self._frame_timings.clear()
        self._audio_video_deltas.clear()

    def pause(self):
        self.playing_state_changed.emit(False)
        self._debug_deltas()
        self.playback_timer.stop()
        self.audio_player.pause()
        self.set_audio_time()

    def play_pause(self):
        if self.playback_timer.isActive():
            self.pause()
        else:
            self.play()

    def play_audio_frame(self, frame=None):
        if frame is None:
            frame = self.playlist.frame
        try:
            self.audio_player.play_range(
                self.playlist.frames_times[frame],
                self.playlist.frames_times[frame + 1])
        except KeyError:
            return

    def is_playing(self):
        return self.playback_timer.isActive()


def compile_shader(src, shader_type):
    shader = gl.glCreateShader(shader_type)
    gl.glShaderSource(shader, src)
    gl.glCompileShader(shader)
    if not gl.glGetShaderiv(shader, gl.GL_COMPILE_STATUS):
        raise RuntimeError(gl.glGetShaderInfoLog(shader).decode())
    return shader


def create_shader_program():
    vertex = compile_shader(VERTEX_SHADER, gl.GL_VERTEX_SHADER)
    fragment = compile_shader(FRAGMENT_SHADER, gl.GL_FRAGMENT_SHADER)
    program = gl.glCreateProgram()
    gl.glAttachShader(program, vertex)
    gl.glAttachShader(program, fragment)
    gl.glLinkProgram(program)
    if not gl.glGetProgramiv(program, gl.GL_LINK_STATUS):
        raise RuntimeError(gl.glGetProgramInfoLog(program))
    return program
