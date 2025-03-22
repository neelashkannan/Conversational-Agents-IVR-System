import torch.serialization
from TTS.api import TTS
from TTS.tts.configs.xtts_config import XttsConfig
import sounddevice as sd
# Add XttsConfig to the allowlist of safe globals
torch.serialization.add_safe_globals([XttsConfig])

# Initialize TTS with CPU
tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=False)

# Text to synthesize
text = "This is a longer piece of text that will be streamed chunk by chunk as it's being generated, allowing for real-time audio output without waiting for the entire text to be processed."

# Sample rate
sample_rate = 24000  # XTTS v2 uses 24kHz sample rate

# Function to play audio chunks
def play_audio_chunk(audio_chunk):
    sd.play(audio_chunk, sample_rate)
    sd.wait()

# Generate and stream audio chunks
for chunk in tts.tts_stream(
    text=text,
    speaker_wav="path/to/reference_audio.wav",
    language="en",
    stream_chunk_size=30  # Number of characters to process per chunk
):
    # Convert chunk to numpy array if needed
    chunk_np = np.array(chunk) if not isinstance(chunk, np.ndarray) else chunk
    play_audio_chunk(chunk_np)