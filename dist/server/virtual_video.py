from read_mpd import DashPlayback
from read_mpd import read_mpd

class VirtualVideo():
    def __init__(self, mpd_file):
        self.mpd_file = mpd_file
        self.file_list = []
        self.dp_object = DashPlayback()
        self.dp_object, _ = read_mpd(self.mpd_file, self.dp_object)
    
    def get_video(self, video_url):
        self.file_list.append(video_url)
        media_object = self.dp_object.video
        fields = video_url.split("/")
        bandwidth = int( fields[-2].split("_")[-1][:-3] )
        segment_id = int( fields[-1].split("_")[-1].split(".")[0][2:] )
        print("bw: {} segment_id: {} size: {}".format(bandwidth, segment_id, media_object[bandwidth].segment_sizes[segment_id-1]))
        return int(media_object[bandwidth].segment_sizes[segment_id-1])