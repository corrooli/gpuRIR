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
from gpuRIR.extensions.filters.hrtf_filter import HRTF_Filter


from gpuRIR.extensions.hrtf.hrtf_binaural_receiver import BinauralReceiver


# Visualizes waveform and spectrogram of each generated IR file. Depending on filter, additional graphs are drawn.
visualize = False

# Prints calculation times and parameter/processing info onto the terminal if True. Needed for benchmarking, debugging and further info.
verbose = True

# If True, apply frequency dependent wall absorption coefficients to simulate realistic wall/ceiling/floor materials.
# Caution: Needs more resources!
freq_dep_abs_coeff = True

# Uses binaural (HRTF) processing to enable realistic sound in 3D spaces. Use of headphones recommended.
use_hrtf = False

# Wall, floor and ceiling materials the room is consisting of
# Structure: Array of six materials (use 'mat.xxx') corresponding to:
# Left wall | Right wall | Front wall | Back wall | Floor | Ceiling
wall_materials = 4 * [mat.wallpaper_on_lime_cement_plaster] + \
    [mat.parquet_glued] + [mat.concrete]

# Setup of binaural receiver with head position [m] and head direction [m].
head = BinauralReceiver(
    head_position=[1.5, 1.5, 1.6], head_direction=[0, -1, 0], verbose=verbose)


# Common gpuRIR parameters (applied to both channels)
room_sz = [5, 4, 3]  # Size of the room [m]
pos_src = [[1.5, 1.8, 1.8]]  # Positions of the sources [m]
orV_src = [0, -1, 0]  # Steering vector of source(s)
spkr_pattern = "omni"  # Source polar pattern
mic_pattern = "homni"  # Receiver polar patterny
T60 = 1.0  # Time for the RIR to reach 60dB of attenuation [s]
# Attenuation when start using the diffuse reverberation model [dB]
att_diff = 15.0
att_max = 60.0  # Attenuation at the end of the simulation [dB]
fs = 44100  # Sampling frequency [Hz]
# Bit depth of WAV file. Either np.int8 for 8 bit, np.int16 for 16 bit or np.int32 for 32 bit
bit_depth = np.int32

if visualize:
    head.visualize(room_sz, pos_src, orV_src)

# Define room parameters
params_left = rp.RoomParameters(
    room_sz=room_sz,
    pos_src=pos_src,
    orV_src=orV_src,
    spkr_pattern=spkr_pattern,
    mic_pattern=mic_pattern,
    T60=T60,
    att_diff=att_diff,
    att_max=att_max,
    fs=fs,
    bit_depth=bit_depth,
    wall_materials=wall_materials,

    # Positions of the receivers [m]
    pos_rcv=[head.ear_position_l],  # Position of left ear
    orV_rcv=head.ear_direction_l,  # Steering vector of left ear
    head_direction=head.direction,
    head_position=head.position
)

params_right = rp.RoomParameters(
    room_sz=room_sz,
    pos_src=pos_src,
    orV_src=orV_src,
    spkr_pattern=spkr_pattern,
    mic_pattern=mic_pattern,
    T60=T60,
    att_diff=att_diff,
    att_max=att_max,
    fs=fs,
    bit_depth=bit_depth,
    wall_materials=wall_materials,

    # Positions of the receivers [m]
    pos_rcv=[head.ear_position_r],  # Position of right ear
    orV_rcv=head.ear_direction_r,  # Steering vector of right ear
    head_direction=head.direction,
    head_position=head.position
)

# Generate two room impulse responses (RIR) with given parameters for each ear
if freq_dep_abs_coeff:
    receiver_channel_r = fdac.generate_RIR_freq_dep_walls(params_right, verbose=verbose, visualize=visualize,)
    receiver_channel_l = fdac.generate_RIR_freq_dep_walls(params_left)

else:
    receiver_channel_r = gRIR.generate_RIR(params_right)
    receiver_channel_l = gRIR.generate_RIR(params_left)

# Common filters, applied to both channels.
# All listed filters wil be applied in that order.
# Leave filters array empty if no filters should be applied.
filters_both = [
    # Speaker simulation.
    # Comment either one out
    # CharacteristicFilter(model.tiny_speaker, fs, visualize=visualize),
    # LinearFilter(101, (0, 100, 150, 7000, 7001, fs/2), (0, 0, 1, 1, 0, 0), fs),

    # Air absorption simulation.
    # Comment either one out
    # AirAbsBandpass(),
    # AirAbsSTFT(),

    # Mic simulation.
    # Comment either one out
    # CharacteristicFilter(model.sm57, fs, visualize=visualize),
    # LinearFilter(101, (0, 100, 150, 7000, 7001, fs/2), (0, 0, 1, 1, 0, 0), fs, visualize=visualize)
]

filters_r = filters_both + [HRTF_Filter('r', params_right, verbose=verbose)]
filters_l = filters_both + [HRTF_Filter('l', params_left, verbose=verbose)]

gIR.generate_stereo_IR(receiver_channel_r, receiver_channel_l,
                       filters_r, filters_l, bit_depth, fs, enable_adaptive_gain=True, verbose=verbose, visualize=visualize)
