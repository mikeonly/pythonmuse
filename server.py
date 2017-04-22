# relay.py recieves the OSC stream and relays packets to other processes.
import time
import logging
import sys

from multiprocessing import Process
from threading import Thread

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
        # multiprocessing config.
        self.input_p, output_p = pipe  # In and out are relative to the obj.
        # Bokeh config.
        self.doc = curdoc()
        # self.doc.add_root(self.fig)
        self.session = push_session(self.doc)

    def run(self):
        '''Function runs as daemon once Grapher class starts. It constantly reads
        data from the pipe and saves it to the intermidiate buffer associated
        with each data channel: timestamp, LAUX and RAUX, but can be more.'''
        # Receive arguments from pipe for the first time. It iniaites lists for
        # further appending.
        source = ColumnDataSource(data=dict(x=[], y=[]))
        fig = figure()
        # self.timestamp0, LAUX, TP9, AF7, AF8, TP10, RAUX = self.input_p.recv()
        fig.line(source=source, x='x', y='y',
                 line_width=2, alpha=0.85, color='red')
        # self.timestamp += [self.timestamp0]  # Only for the first time.
        # # open a session to keep our local document in sync with server
        session = push_session(curdoc())

        timestamp0, LAUX, TP9, AF7, AF8, TP10, RAUX = self.input_p.recv()
        source.stream(dict(x=[0], y=[LAUX]))

        def update():
            # On update, recieve arguments from OSC channel
            timestamp, LAUX, TP9, AF7, AF8, TP10, RAUX = self.input_p.recv()
            # Update source with the recieved variables.
            time = timestamp-timestamp0
            source.stream(dict(x=[time], y=[LAUX]), rollover=1000)

        curdoc().add_periodic_callback(update, 2)
        session.show(fig) # open the document in a browser
        session.loop_until_closed() # run forever