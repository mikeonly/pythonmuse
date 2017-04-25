# relay.py recieves the OSC stream and relays packets to other processes.
import logging

# Makes all process independent by spawning separate Python instances for each.
from multiprocessing import Process

# Creates and resolves streams.
import pylsl
from pylsl import StreamInfo, StreamOutlet, local_clock, StreamInlet

# Module for MuseServer that reads OSC stream.
from liblo import ServerThread, make_method

# Modules for Saver.
import numpy as np


class MuseServer(ServerThread):
    # Listen for messages
    """MuseServer receives OSC packets from TCP stream and makes them available
    at the specified EEG LSL stream."""

    def __init__(self, port, num_channels=6, freq=500, logger=None):
        ServerThread.__init__(self, port)
        self.logger = logger or logging.getLogger('server.MuseServer')

        # Create pylsl stream for EEG
        CHUNK_SIZE = 32
        OUT_BUFFER_SIZE = 360  # in seconds
        self.info = StreamInfo('Muse', 'EEG', num_channels,
                               freq, 'float32', 'muse-b0e5')
        self.info.desc().append_child_value('manufacturer', 'Interaxon')
        self.channels = self.info.desc().append_child('channels')
        for channel in ['LAUX', 'TP9', 'AF7', 'AF8', 'TP10', 'RAUX']:
            self.channels.append_child('channel') \
                .append_child_value('label', channel) \
                .append_child_value('unit', 'microvolts') \
                .append_child_value('type', 'EEG')
        self.outlet = StreamOutlet(self.info, CHUNK_SIZE, OUT_BUFFER_SIZE)
        self.logger.info('Created EEG outlet: {}'.format(self.info.desc()))

    # eeg_callback is called whenever a packet is received with the specified
    # /muse/eeg path.
    @make_method('/muse/eeg', 'ffffff')
    def eeg_callback(self, path, args):
        timestamp = local_clock()
        self.outlet.push_sample(args, timestamp)
        self.logger.info('Sent sample')


class Saver(Process):
    """Saver reads input from available LSL stream with EEG type and saves
     recieved data into the `savefile` file."""

    def __init__(self, name, savefile=None, buffer_size=100, logger=None):
        super(Saver, self).__init__(name=name, daemon=True)
        self.logger = logger or logging.getLogger('server.Saver')

        self.savefile = savefile or name + '.csv'
        self.buffer_size = buffer_size
        self.logger.info('Creating and instance of Saver')

        self.resolve()

    def run(self):
        # While running, keep the output file open.
        with open(self.savefile, mode='ab+') as f:
            while True:
                try:
                    chunk, timestamps = self.inlet.pull_chunk(
                        timeout=10.0, max_samples=self.buffer_size)
                    self.logger.info('Recieved packet from LSL stream')
                    self.buffer += [chunk + [timestamps]]
                    if len(self.buffer) > self.buffer_size:
                        self.save(f, self.buffer)
                        self.logger.info('Wrote buffer to the file')
                        self.buffer = []
                except pylsl.LostError as e:
                    self.logger.warn(e)
                    self.logger.info(
                        'Stream source has been lost, trying to resolve')
                    self.resolve()
                    continue

    def resolve(self):
        self.logger.info('Resolving LSL stream for EEG')
        # Resolve streams in LSL networks with type EEG, timeout in seconds.
        streams = pylsl.resolve_byprop('type', 'EEG', minimum=1, timeout=10)
        self.logger.info('Resolved EEG streams:\n {}'.format(streams))
        self.inlet = StreamInlet(streams[0])
        self.logger.info('Created stream inlet {}'.format(self.inlet))

    def save(self, f, data):
        # Save args into a csv file.
        np.savetxt(f, data, delimiter=',', newline='\n')


class Fourier(Process):
    '''Fourier class resolves EEG LSL stream, does FFT on data and makes
    Fourier LSL stream available for other processes'''

    def __init__(self, name, pipe):
        super(Fourier, self).__init__(name=name, daemon=True)

        # Create pylsl stream for Fourier.
        CHUNK_SIZE = 32
        OUT_BUFFER_SIZE = 360  # in seconds
        self.info = StreamInfo('Muse', 'Fourier', 'float32', 'muse-b0e5')
        self.info.desc().append_child_value('manufacturer', 'Interaxon')
        self.channels = self.info.desc().append_child('channels')
        for channel in ['LAUX', 'TP9', 'AF7', 'AF8', 'TP10', 'RAUX']:
            self.channels.append_child('channel') \
                .append_child_value('label', channel) \
                .append_child_value('unit', 'microvolts') \
                .append_child_value('type', 'Fourier')
        self.outlet = StreamOutlet(self.info, CHUNK_SIZE, OUT_BUFFER_SIZE)
        self.logger.info('Created Fourier outlet: {}'.format(self.info.desc()))

    def run(self):
        '''While running, recieve raw EEG data and do FFT on it.'''
        while True:
            chunk, timestamps = self.inlet.pull_chunk(
                timeout=10.0, max_samples=self.buffer_size)
            sample = []
            fft = sp.fft(signal)
            spectrum = abs(fft)[:NUM_SAMPLES/2]
            power = spectrum**2
            bins = simps(np.split(power, NUM_BINS))
        self.outlet.push_sample(sample)


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
            time = timestamp - timestamp0
            source.stream(dict(x=[time], y=[LAUX]), rollover=1000)

        curdoc().add_periodic_callback(update, 2)
        session.show(fig)  # open the document in a browser
        session.loop_until_closed()  # run forever
