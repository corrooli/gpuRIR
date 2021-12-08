import numpy as np

import gpuRIR.extensions.room_parameters as rp
import gpuRIR.extensions.generate_RIR as gRIR
import gpuRIR.extensions.generate_IR as gIR

from gpuRIR.extensions.wall_absorption.materials import Materials as mat
import gpuRIR.extensions.wall_absorption.freq_dep_abs_coeff as fdac

from gpuRIR.extensions.filters.air_absorption_bandpass import AirAbsBandpass
from gpuRIR.extensions.filters.air_absorption_stft import AirAbsSTFT
from gpuRIR.extensions.filters.characteristic_filter import CharacteristicFilter
from gpuRIR.extensions.filters import characteristic_models as model
from gpuRIR.extensions.filters.linear_filter import LinearFilter


# Visualizes waveform and spectrogram of each generated IR file. Depending on filter, additional graphs are drawn.
visualize = True

# Prints calculation times and parameter/processing info onto the terminal if True. Needed for benchmarking, debugging and further info.
verbose = False

# If True, apply frequency dependent wall absorption coefficients to simulate realistic wall/ceiling/floor materials.
# Caution: Needs more resources!
freq_dep_abs_coeff = True

# Wall, floor and ceiling materials the room is consisting of
# Structure: Array of six materials (use 'mat.xxx') corresponding to:
# Left wall | Right wall | Front wall | Back wall | Floor | Ceiling
wall_materials = 4 * [mat.wallpaper_on_lime_cement_plaster] + \
    [mat.parquet_glued] + [mat.concrete]

# Define room parameters
params = rp.RoomParameters(
    room_sz=[5, 4, 3],  # Size of the room [m]
    pos_src=[[3, 3,  1.8]],  # Positions of the sources [m]
    pos_rcv=[[1.5, 1.5, 1.6]],  # Positions of the receivers [m]
    orV_src=[0, -1, 0],  # Steering vector of source(s)
    orV_rcv=[0.1, 1, 0],  # Steering vector of receiver(s)
    spkr_pattern="omni",  # Source polar pattern
    mic_pattern="card",  # Receiver polar pattern
    T60=1.0,  # Time for the RIR to reach 60dB of attenuation [s]
    # Attenuation when start using the diffuse reverberation model [dB]
    att_diff=15.0,
    att_max=60.0,  # Attenuation at the end of the simulation [dB]
    fs=44100,  # Sampling frequency [Hz]
    # Bit depth of WAV file. Either np.int8 for 8 bit, np.int16 for 16 bit or np.int32 for 32 bit
    bit_depth=np.int32,
    # Absorption coefficient of walls, ceiling and floor.
    wall_materials=wall_materials
)

# Generate room impulse response (RIR) with given parameters
if freq_dep_abs_coeff:
    receiver_channels = fdac.generate_RIR_freq_dep_walls(
        params, LR = True, order = 50, band_width = 100, factor = 1.1, visualize = visualize, verbose = verbose)
else:
    receiver_channels = gRIR.generate_RIR(params)

for i in range(len(params.pos_rcv)):
    # All listed filters wil be applied in that order.
    # Leave filters array empty if no filters should be applied.

    filters = [
        # Speaker simulation.
        # Comment either one out
        # CharacteristicFilter(model.tiny_speaker, params.fs, visualize=visualize),
        # LinearFilter(101, (0, 100, 150, 7000, 7001, params.fs/2), (0, 0, 1, 1, 0, 0), params.fs),

        # Air absorption simulation.
        # Comment either one out
        # AirAbsBandpass(divisions=10, max_frequency=params.fs/2, order=12, verbose=verbose, visualize=visualize),
        # AirAbsSTFT(),

        # Mic simulation.
        # Comment either one out
        # CharacteristicFilter(model.sm57, params.fs, visualize=visualize),
        # LinearFilter(101, (0, 100, 150, 7000, 7001, params.fs/2), (0, 0, 1, 1, 0, 0), params.fs, visualize=visualize)
    ]

    gIR.generate_mono_IR(
        receiver_channels[i], filters, params.bit_depth, params.fs, visualize=visualize, verbose=verbose)
