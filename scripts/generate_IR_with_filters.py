""" 
Generates an impulse response WAV file (IR) with optional filters.
Example usage: Convolving (reverberating) an audio signal in an impulse response loader plug-in like Space Designer in Logic Pro X.
"""
from filters.filter import Filter
import librosa
from filters.characteristic_filter import CharacteristicFilter
from filters.air_absorption_bandpass import AirAbsBandpass
from filters.air_absorption_stft import AirAbsSTFT
from filters.linear_filter import LinearFilter

import filters.air_absorption_calculation as aa
import numpy as np
import numpy.matlib
import matplotlib.pyplot as plt
from math import ceil
from scipy.io import wavfile
import time
import gpuRIR
from create_spectrogram import create_spectrogram
import filters.characteristic_models as cm


def generate_RIR():
    '''
    Generates RIRs from the gpuRIR library.

    :return: Receiver channels (mono)
    '''
    gpuRIR.activateMixedPrecision(False)
    gpuRIR.activateLUT(False)

    room_sz = [8, 10, 3]  # Size of the room [m]
    nb_src = 1  # Number of sources
    pos_src = np.array([[4, 2, 1.7]])  # Positions of the sources ([m]
    nb_rcv = 1  # Number of receivers
    pos_rcv = np.array([[4, 8, 1.7]])	 # Position of the receivers [m]
    # Vectors pointing in the same direction than the receivers
    orV_rcv = np.matlib.repmat(np.array([0, 1, 0]), nb_rcv, 1)
    mic_pattern = "card"  # Receiver polar pattern
    abs_weights = [0.9]*5+[0.5]  # Absortion coefficient ratios of the walls
    T60 = 1.0	 # Time for the RIR to reach 60dB of attenuation [s]
    # Attenuation when start using the diffuse reverberation model [dB]
    att_diff = 15.0
    att_max = 60.0  # Attenuation at the end of the simulation [dB]
    fs = 44100  # Sampling frequency [Hz]
    # Bit depth of WAV file. Either np.int8 for 8 bit, np.int16 for 16 bit or np.int32 for 32 bit
    bit_depth = np.int32

    beta = gpuRIR.beta_SabineEstimation(
        room_sz, T60, abs_weights=abs_weights)  # Reflection coefficients
    # Time to start the diffuse reverberation model [s]
    Tdiff = gpuRIR.att2t_SabineEstimator(att_diff, T60)
    # Time to stop the simulation [s]
    Tmax = gpuRIR.att2t_SabineEstimator(att_max, T60)
    # Number of image sources in each dimension
    nb_img = gpuRIR.t2n(Tdiff, room_sz)
    RIRs = gpuRIR.simulateRIR(room_sz, beta, pos_src, pos_rcv, nb_img,
                              Tmax, fs, Tdiff=Tdiff, orV_rcv=orV_rcv, mic_pattern=mic_pattern)

    # return receiver channels (mono), number of receivers, sampling frequency and bit depth from RIRs.
    return RIRs[0], pos_rcv, fs, bit_depth


def automatic_gain_increase(source, bit_depth, ceiling):
    '''
    Increases amplitude (loudness) to defined ceiling.

    :param list source: Sound data to process.
    :param int bit_depth: Bit depth of source sound data.
    :param int ceiling: Maximum loudness (relative dB, e.g. -1dB) the sound data should be amplified to
    :return: Amplified source sound data.
    '''
    peak = np.max(source)
    negative_peak = np.abs(np.min(source))

    # Check if the negative or positive peak is of a higher magnitude
    if peak < negative_peak:
        peak = negative_peak

    max_gain = np.iinfo(bit_depth).max*10**(-ceiling/10)
    factor = max_gain/peak

    return source*factor


def generate_IR(source, filters, bit_depth):
    '''
    Generates an IR file out of given source sound data and an optional array of filters to be applied.

    :param list source: Sound data to be converted into an impulse response file.
    :param list filters: List of filters to be applied (in that order)
    '''
    # Prepare sound data arrays.
    source_signal = np.copy(source)
    filename_appendix = ""

    # Apply filters
    for i in range(len(filters)):
        start_time = time.time()
        source_signal = Filter(filters[i]).apply(source_signal)
        end_time = time.time()
        print(f"{filters[i].NAME} time = {end_time-start_time} seconds")
        filename_appendix = f"{filename_appendix}_{filters[i].NAME}"

    # Stack array vertically
    impulseResponseArray = np.vstack(source_signal)

    # Increase Amplitude to usable levels
    impulseResponseArray = automatic_gain_increase(
        impulseResponseArray, bit_depth, 3)

    # Create stereo file (dual mono)
    impulseResponseArray = np.concatenate(
        (impulseResponseArray, impulseResponseArray), axis=1)

    # Write impulse response file
    filename = f'IR_{filename_appendix}_{time.time()}.wav'
    wavfile.write(filename, fs, impulseResponseArray.astype(bit_depth))

    # Create spectrogram
    create_spectrogram(filename, filename_appendix)

    # Visualize waveform of IR
    plt.title(filename_appendix)
    plt.plot(impulseResponseArray)
    plt.show()


if __name__ == "__main__":
    receiver_channels, pos_rcv, fs, bit_depth = generate_RIR()
    for i in range(0, len(pos_rcv)):
        # All listed filters wil be applied in that order.
        # Leave filters array empty if no filters should be applied.
        filters = [
            # Speaker simulation
            #LinearFilter(101, (0, 100, 150, 7000, 7001, fs/2), (0, 0, 1, 1, 0, 0), fs),
            
            # Air absorption simulation
            #AirAbsBandpass(),

            # Mic simulation
            #CharacteristicFilter(cm.sm57_freq_response, fs),
        ]
        generate_IR(receiver_channels[i], filters, bit_depth)
