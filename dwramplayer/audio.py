import numpy as np
import sounddevice
from pydub import AudioSegment


SAMPLE_RATE = 44100


class AudioPlayer:
    def __init__(self):
        self.samples = None
        self.samplerate = SAMPLE_RATE
        self.frame_index = 0
        self.stream = None
        self.playing = False
        self.time = 0
        self.play_range_active = False
        self.range_start = None
        self.range_end = None

    def load_video(self, video_path, duration):
        self.samples = extract_audio_samples(video_path, duration)
        self.load_audio()

    def add_video(self, video_path, duration):
        samples = extract_audio_samples(video_path, duration)
        if self.samples is None:
            self.samples = samples
        else:
            self.samples = np.concatenate([self.samples, samples], axis=0)

    def load_videos(self, video_paths_and_durations):
        self.samples = None
        for path, duration in video_paths_and_durations.items():
            self.add_video(path, duration)
        self.load_audio()

    def load_audio(self):
        self.stream = sounddevice.OutputStream(
            samplerate=self.samplerate,
            channels=self.samples.shape[1],
            dtype='float32',
            # latency='low',
            # prime_output_buffers_using_stream_callback=True,
            callback=self.callback)

    def start(self):
        self.stream.start()
        self.playing = True

    def callback(self, outdata, frames_count, time_, status):
        self.time = self.frame_index / self.samplerate

        if not self.playing:
            outdata.fill(0)
            return

        if self.play_range_active:
            end_frame = self.range_end
        else:
            end_frame = len(self.samples)
        remaining = end_frame - self.frame_index
        if remaining <= 0:
            outdata.fill(0)
            self.playing = False
            self.play_range_active = False
            return

        frames_to_write = min(frames_count, remaining)
        if not frames_to_write:
            outdata.fill(0)
            return
        outdata[:frames_to_write] = self.samples[
            self.frame_index:self.frame_index + frames_to_write]
        if frames_to_write < frames_count:
            outdata[frames_to_write:] = 0  # pad rest with silence
        self.frame_index += frames_to_write

    def seek(self, seconds):
        self.frame_index = int(seconds * self.samplerate)

    def pause(self):
        self.playing = False

    def resume(self):
        self.playing = True

    def play_range(self, start_time, end_time):
        self.range_start = int(start_time * self.samplerate)
        self.range_end = int(end_time * self.samplerate)
        self.frame_index = self.range_start
        self.play_range_active = True
        self.playing = True
        self.start()


def extract_audio_samples(video_path, duration=None, samplerate=SAMPLE_RATE):
    try:
        audio_segment = AudioSegment.from_file(video_path)
    except Exception:
        # video has no audio, return silence
        total_samples = int(duration * samplerate)
        return np.zeros((total_samples, 2), dtype=np.float32)
    audio = audio_segment.set_channels(2).set_frame_rate(
        samplerate)
    samples = np.array(audio.get_array_of_samples()).astype(np.float32)
    if audio.channels == 2:
        samples = samples.reshape((-1, 2))  # stereo
    else:
        samples = samples.reshape((-1, 1))  # mono
    samples /= np.iinfo(audio.array_type).max  # normalize to -1.0 to 1.0
    return samples
