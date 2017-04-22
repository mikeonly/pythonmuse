from multiprocessing import Pipe
import time
from server import *


# Create pipes for connection between MuseServer, Saver and Grapher.
# Duplex is false, for `conn1, conn2 = Pipe(duplex=False)` guarantees that
# conn1 can only receive data and conn2 can only send data.
saver_pipe = Pipe(duplex=False)
grapher_pipe = Pipe(duplex=False)

# MuseServer applies .send() method to eeg_pipes once eeg_callback function is
# called.
relay = MuseServer(port=5000, eeg_pipes=[saver_pipe, grapher_pipe])
saver = Saver(pipe=saver_pipe, name='Saver', savefile='data.csv')
grapher = Grapher(pipe=grapher_pipe, name='Grapher')

# Starts all the processes.
if __name__ == '__main__':
    relay.start()
    saver.start()
    grapher.start()
    time.sleep(100)
