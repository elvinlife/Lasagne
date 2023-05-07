#!/usr/bin/env python

from __future__ import division
__author__ = 'alvin'

"""
 The current module is the buffer based adaptaion scheme used by Netflix. Current design is based
 on the design from the paper:

[1] Huang, Te-Yuan, et al. "A buffer-based approach to rate adaptation: Evidence from a large video streaming service."
    Proceedings of the 2014 ACM conference on SIGCOMM. ACM, 2014.
"""

import config_dash

class LookupTable:
    def __init__(self, fname):
        self.bw_bins = []
        self.buffer_bins = []
        self.prerate_bins = {}
        index_prerate = 0
        self.lookup_table = []
        with open(fname, "r") as fin:
            for line in fin:
                words = line.split("\t")
                if not words[0].isdigit():
                    continue
                if int(words[0]) not in self.bw_bins:
                    self.bw_bins.append(int(words[0]))
                if float(words[1]) not in self.buffer_bins:
                    self.buffer_bins.append(float(words[1]))
                if int(words[2]) not in self.prerate_bins:
                    self.prerate_bins[int(words[2])] = index_prerate
                    index_prerate += 1
                self.lookup_table.append(int(words[3]))
        self.bw_bins.sort()
        self.buffer_bins.sort()
        self.step_bw = len(self.buffer_bins) * len(self.prerate_bins)
        self.step_buffer = len(self.prerate_bins)
        self.gap_bw = (self.bw_bins[-1] - self.bw_bins[0]) / (len(self.bw_bins) - 1)
        self.gap_buffer = (self.buffer_bins[-1] - self.buffer_bins[0]) / (len(self.buffer_bins) - 1)

    def get_next_rate(self, bw, buffer, pre_rate):
        index_bw = 0
        if bw >= self.bw_bins[-1]:
            index_bw = len(self.bw_bins)-1
        elif bw > self.bw_bins[0]:
            index_bw = int((bw - self.bw_bins[0]) / self.gap_bw)
        index_buffer = 0
        if buffer >= self.buffer_bins[-1]:
            index_buffer = len(self.buffer_bins)-1
        elif buffer > self.buffer_bins[0]:
            index_buffer = int((buffer - self.buffer_bins[0]) / self.gap_buffer)
        final_index = index_bw * self.step_bw + index_buffer * self.step_buffer + self.prerate_bins[pre_rate]
        config_dash.LOG.info("FastMPC: bw: {} buffer: {} rate: {} next_bitrate: {} Kbps".format(
            bw, buffer, pre_rate, self.lookup_table[final_index]))
        return self.lookup_table[final_index]
    
lookup_table_ = LookupTable(config_dash.LOOKUP_FNAME)

def fastmpc_dash(bitrates, dash_player, recent_download_sizes,
                 previous_segment_times, previous_bitrate):
    """
    :param dash_player: the dash player
    :param bitrates: A tuple/list of available bitrates
    :param recent_download_sizes(KB): recent downloaded segment sizes
    :param previous_segment_times(second): recent download time
    """
    assert(len(previous_segment_times) == len(recent_download_sizes))
    while len(previous_segment_times) > config_dash.BASIC_DELTA_COUNT:
        previous_segment_times.pop(0)
    while len(recent_download_sizes) > config_dash.BASIC_DELTA_COUNT:
        recent_download_sizes.pop(0)
    if len(previous_segment_times) == 0 or len(recent_download_sizes) == 0:
        return bitrates[0], None
    sum_denominator = 0
    for i in range(len(previous_segment_times)):
        sum_denominator += 1 / (int(8 * recent_download_sizes[i]
                                / (previous_segment_times[i])) >> 10)
    predict_bw = len(previous_segment_times) / sum_denominator
    current_bitrate = lookup_table_.get_next_rate(predict_bw, dash_player.buffer_length, previous_bitrate)
    return current_bitrate
