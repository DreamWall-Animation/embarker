import numpy as np
import sounddevice
from pydub import AudioSegment


CHANNELS = 2


class AudioPlayer:
    def __init__(self, device_index=None):

        self.samples: np.array | None = None
        self.frame_index = 0
        self.stream = None
        self.playing = False
        self.time = 0
        self.play_range_active = False
        self.range_start = None
        self.range_end = None

        self.samplerate: int | None = None
        self.stream: sounddevice.OutputStream
        self.set_output_device(device_index)

    def set_output_device(self, device_index=None) -> bool:
        # Select device
        devices = sounddevice.query_devices()
        device_index = (
            device_index if device_index is not None
            else sounddevice.default.device['output'])
        old_samplerate = self.samplerate
        self.samplerate = int(devices[device_index]['default_samplerate'])
        sounddevice.default.device[1] = device_index

        # Create stream
        del self.stream
        self.stream = sounddevice.OutputStream(
            device=(sounddevice.default.device[0], device_index),
            samplerate=self.samplerate,
            channels=CHANNELS,
            dtype='float32',
            # latency='low',
            # prime_output_buffers_using_stream_callback=True,
            callback=self.callback)

        # Return if sample rate has changed
        return old_samplerate != self.samplerate

    def load_audio(self, samples: np.array):
        self.samples = samples

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


def get_output_devices():
    output_devices = [
        d for d in sounddevice.query_devices()
        if d['max_output_channels']]
    return {d['name']: d['index'] for d in output_devices}


def current_sample_rate():
    device_index = sounddevice.default.device[1]
    return int(sounddevice.query_devices()[device_index]['default_samplerate'])


def create_silence_samples(duration, samplerate=None):
    samplerate = current_sample_rate() if samplerate is None else samplerate
    total_samples = int(duration * samplerate)
    return np.zeros((total_samples, 2), dtype=np.float32)


def extract_audio_samples(video_path, duration):
    samplerate = current_sample_rate()
    try:
        audio_segment = AudioSegment.from_file(video_path)
    except Exception:
        # video has no audio, return silence
        return create_silence_samples(duration, samplerate)
    audio = audio_segment.set_channels(2).set_frame_rate(
        samplerate)
    samples = np.array(audio.get_array_of_samples()).astype(np.float32)
    samples = samples.reshape((-1, CHANNELS))
    samples /= np.iinfo(audio.array_type).max  # normalize to -1.0 to 1.0
    expected_samples_count = int(duration * samplerate)
    if expected_samples_count < samples.shape[0]:
        samples = samples[:expected_samples_count]
    else:
        extra_count = expected_samples_count - samples.shape[0]
        samples = np.vstack([samples, np.zeros((extra_count, 2))])
    return samples
