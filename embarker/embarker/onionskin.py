from embarker.playlist import Playlist


class OnionSkin:
    def __init__(self, playlist: Playlist):
        self.playlist = playlist
        self.enabled = False
        self.before_opacities = [0.2, 0.4, 0.6, 0.8]
        self.after_opacities = [.8, .6, .4, .2]

    def iter_from_frame(self, frame):
        count = -min((len(self.before_opacities), frame))
        for i in range(count, 0):
            yield frame + i, self.before_opacities[i]
        end = frame + len(self.after_opacities)
        limit = self.playlist.frames_count - end
        count = min((limit, len(self.after_opacities)))
        for i in range(1, count):
            yield frame + i, self.after_opacities[i]

