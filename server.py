# relay.py recieves the OSC stream and relays packets to other processes.
import time
import logging
import sys

from multiprocessing import Process

# Modules for MuseServer.
from liblo import ServerThread, make_method

# Modules for Saver.
import numpy as np

# Modules for Grapher.
from bokeh.models import ColumnDataSource
from bokeh.plotting import curdoc, figure
from bokeh.client import push_session

from functools import partial
from tornado import gen


# Create a logger for debug purposes.
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(name=__name__)
# Specify logger format.
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s')
# Stream handler for console output
shandler = logging.StreamHandler(sys.stderr)
shandler.setFormatter(formatter)
logger.addHandler(shandler)


class MuseServer(ServerThread):
    # Listen for messages
    """MuseServer receives OSC packets from TCP stream and sends them to the
    specified ouput pipes."""
    def __init__(self, port, eeg_pipes):
        ServerThread.__init__(self, port)
        # In and out are relative to the obj.
        input_ps, self.eeg_output_ps = zip(*eeg_pipes)

    # eeg_callback is called whenever a packet is received with the specified
    # /muse/eeg path.
    @make_method('/muse/eeg', 'ffffff')
    def eeg_callback(self, path, args):
        timestamp = time.time()  # POSIX time format
        packet = [timestamp] + args  # Append time to packets
        for pipe in self.eeg_output_ps:
            pipe.send(packet)


class Saver(Process):
    "Saver reads the input pipe and save the data into a file."
    def __init__(self, name, pipe, savefile=None, buffer_size=100):
        # Saver reads one passed pipe for now. Maybe I should create a
        # decorator to allow for more pipe being read and saved?
        super(Saver, self).__init__(name=name, daemon=True)

        self.input_p, output_p = pipe  # In and out are relative to the obj.
        self.buffer = []  # Buffer for data recieved by pipe.
        self.savefile = savefile or name + '.csv'
        self.buffer_size = buffer_size

    def run(self):
        # While running, keep the output file open.
        with open(self.savefile, mode='ab+') as f:
            while True:
                # Read from the pipe. Waits until pipe is not empty.
                self.buffer += [self.input_p.recv()]
                if len(self.buffer) > self.buffer_size:
                    self.save(f, self.buffer)
                    self.buffer = []

    def save(self, f, data):
            # Save args into a csv file.
        np.savetxt(f, data, delimiter=',', newline='\n')


class Grapher(Process):
    """Grapher gets data into input pipe, create Bokeh backend and inputs
    received data into the Bokeh server."""
    def __init__(self, name, pipe):
        super(Grapher, self).__init__(name=name, daemon=True)
        # Predefine attributes to save received data to.
        self.timestamp0 = time.time()
        self.timestamp = []
        self.RAUX = []
        self.LAUX = []
        # multiprocessing config.
        self.input_p, output_p = pipe  # In and out are relative to the obj.
        # Bokeh config.
        self.doc = curdoc()
        self.source = ColumnDataSource(dict(LAUX=[], RAUX=[],
                                            time=[]))
        self.fig = figure()
        self.fig.line(source=self.source, x='time', y='LAUX',
                      line_width=2, alpha=0.85, color='red')
        self.fig.line(source=self.source, x='time', y='RAUX',
                      line_width=2, alpha=0.85, color='red')
        self.doc.add_root(self.fig)
        self.session = push_session(self.doc)

    def run(self):
        '''Function runs as daemon once Grapher class starts. It constantly reads
        data from the pipe and saves it to the intermidiate buffer associated
        with each data channel: timestamp, LAUX and RAUX, but can be more.'''
        # Receive arguments from pipe for the first time. It iniaites lists for
        # further appending.
        self.timestamp0, LAUX, TP9, AF7, AF8, TP10, RAUX = self.input_p.recv()
        self.timestamp += [self.timestamp0]  # Only for the first time.
        self.LAUX += [LAUX]
        self.RAUX += [RAUX]
        ct = 0  # Counter for debug.
        while True:
            # Get all possible arguemnts.
            timestamp, LAUX, TP9, AF7, AF8, TP10, RAUX = self.input_p.recv()
            self.timestamp += [timestamp]
            self.RAUX += [RAUX]
            self.LAUX += [LAUX]
            ct += 1  # Create a counting variable.
            if ct % 100 == 0:  # Update the plot on each 100th packet.
                self.update()

    @gen.coroutine
    def update(self):
        time = [t - self.timestamp0 for t in self.timestamp]
        self.source.stream(dict(time=[time], LAUX=[self.LAUX],
                                RAUX=[self.RAUX]), 100)
        # Clean arrays after updating.
        self.timestamp = []
        self.LAUX = []
        self.RAUX = []
