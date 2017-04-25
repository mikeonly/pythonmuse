# pythonmuse
---
`pythonmuse` is Phyton code to work with real-time EEG data: recording, plotting and analysis. 

It was primiraly intended to work with Interaxon Muse EEG headband, but any other source can be used as an input. `pythonmuse` contains several classes that record incoming EEG stream to a file, perform Fast Fourier Transform (FFT) and plot the stream in real time.

## Table of Contents
 - [Requirements](#requirements)
 - [Installation](#installation)
 - [Implementation](#implementation)
 - [Connecting Other Devices](#connecting-other-devices)
 - [To-Do](#to-do)


## Requirements 

Python 3.x, muse-io, [Bokeh](http://bokeh.pydata.org/en/latest/), liblo, [liblsl](https://github.com/sccn/labstreaminglayer), [pylsl](https://github.com/sccn/labstreaminglayer/tree/master/LSL/liblsl-Python), numpy.

## Installation

To use `pythoncode`, just clone this repo:

```sh
$ git clone https://github.com/mikeonly/pythonmuse
```

To properly install `pylsl` and LSL library, follow build instructions [here](https://github.com/sccn/labstreaminglayer/blob/master/LSL/liblsl/INSTALL) for your platform. After `.ddl` or `.dylib` (depending on the platform) files after the build have been generated, place them under `/pylsl` folder and rename to `liblsl64` or `liblsl32`. For macOS, there should be `liblsl64.dylib` in the folder with `pylsl.py`.

If all requirements are met, `pythonmuse` should be ok to run. 

```sh
# First make EEG stream available
muse-io --preset AB --no-dsp --osc 'osc.udp://localhost:5000'
# Run main.py from this directory to analyse the stream
python main.py
```

## Implementation

`server.py` contains definitions of required classes. Each class corresponds to a separate process run in parallel, that does a particular function. Currently there are classes for: relaying incoming data to a LSL stream (`server.MuseServer`), saving data to a file (`server.Saver`) and FFT (`server.Fourier`).

`server.MuseServer` creates an LSL outlet with raw EEG data from an incoming OSC stream. The LSL outlet is then available for every other process requiring the raw data for different purposes.

`server.Saver` resolves LSL stream with EEG data created by `server.MuseServer` and saves data in the stream to a file.

`server.Fourier` picks up the same LSL stream with EEG data and performs FFT on it. FFT results is then made available in a separate LSL stream with `Fourier` type.

`main.py` governs run-time of a specific task, which starts recording, plotting, etc. It currently contains the required imports from `server.py`.

To create a process for relaying OSC data from Muse, create a `MuseServer` instance:

```python
relay = MuseServer(port)
relay.start()
```

Saving the data from stream is possible by creating an instance of `Saver`:
```python
# Name is just an identifier of the Saver process,
# `savefile` is the name of the file to which output the stream
saver = Saver(name='MuseSaver', savefile='data.csv')
```

`pythonmuse` is primiraly written to work with Interaxon Muse EEG headband, but any EEG source can be used as a data source. In fact, creating an LSL stream with `EEG` type should be enough in order for `Fourier`, `Saver`, etc. to pick up the required stream.

## Connecting Other Devices

In order to connect devices different from Interaxon Muse, you need to make them available as an LSL stream with appropriate data type. This can usually be made with LSL applications, written specifically for those purposes. 

First, locate the required application suitable for the EEG acqusition system in hand at SCCN FTP server: ftp://sccn.ucsd.edu/pub/software/LSL/Apps/. Most applications provide a Windows binary ready for running.

For example, to connect Brain Products VAmp acqusition system: 
1. Download the corresponding [archive](ftp://sccn.ucsd.edu/pub/software/LSL/Apps/Brain%20Products%20VAmp-1.11.zip) 
2. Unzip it
3. Run `VAmp.exe`
4. Configure the stream and link it to the network

For more information on linking the devices please consult the LSL documentation. In particular, useful demos are available on YouTube: https://www.youtube.com/watch?v=Y1at7yrcFW0.

## To-Do

- [x] Make devices available via LSL streaming
- [ ] Configure Bokeh for real-time plotting of an arbitrary number of EEG channels
- [ ] Try [EEGLearn](https://github.com/pbashivan/EEGLearn) for real-time EEG analysis
