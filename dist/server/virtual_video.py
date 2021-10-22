import sys
sys.path.append("./dist/util/")
import read_mpd
import config_dash
import numpy as np

class DashPlayback:
    """
    Audio[bandwidth] : {duration, url_list}
    Video[bandwidth] : {duration, url_list}
    """
    def __init__(self):

        self.min_buffer_time = None
        self.playback_duration = None
        self.audio = dict()
        self.video = dict()

class VirtualVideo():
    def __init__(self, mpd_file):
        self.mpd_file = mpd_file
        self.file_list = []
        self.dp_object = DashPlayback()
        self.dp_object, _ = read_mpd.read_mpd(self.mpd_file, self.dp_object)
        for bw, media_obj in self.dp_object.video.items():
            ave_chunk_size = np.mean(media_obj.segment_sizes)
            config_dash.LOG.info("bw: %d chunk_size: %d bitrate: %d" % (bw, ave_chunk_size, ave_chunk_size/4))
    
    def get_video(self, video_url):
        self.file_list.append(video_url)
        media_object = self.dp_object.video
        fields = video_url.split("/")
        bandwidth = int( fields[-2].split("_")[-1][:-3] )
        segment_id = int( fields[-1].split("_")[-1].split(".")[0][2:] )
        config_dash.LOG.info("bitrate: {} segment_id: {} size: {}KB".format(
            bandwidth, segment_id, media_object[bandwidth].segment_sizes[segment_id-1] >> 10))
        return int(media_object[bandwidth].segment_sizes[segment_id-1])