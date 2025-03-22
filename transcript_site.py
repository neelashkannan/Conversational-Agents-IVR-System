import streamlit as st
import av
import numpy as np
from streamlit_webrtc import webrtc_streamer, AudioProcessorBase
from transformers import pipeline

# Cache the ASR model so it loads only once.
@st.cache_resource
def load_asr_model():
    asr = pipeline("automatic-speech-recognition", model="facebook/wav2vec2-base-960h")
    return asr

asr_pipeline = load_asr_model()

class Wav2Vec2Recognizer(AudioProcessorBase):
    def __init__(self, buffer_duration=2.0, sample_rate=16000):
        # Buffer to accumulate audio samples.
        self.buffer = np.array([], dtype=np.float32)
        self.buffer_duration = buffer_duration  # seconds of audio per inference
        self.sample_rate = sample_rate
        self.text_chunks = []  # List to store recognized text chunks
        self.debug_info = ""   # For displaying debug information
        self.last_inference = {}  # Store last inference result for debugging

    def recv(self, frame: av.AudioFrame) -> av.AudioFrame:
        # Convert audio frame to a numpy array.
        audio = frame.to_ndarray()
        # If stereo, use only one channel.
        if audio.ndim > 1:
            audio = audio[:, 0]
        # If not already float32, convert (assuming int16 input).
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32) / 32768.0
        # Append the current frame's audio to our buffer.
        self.buffer = np.concatenate((self.buffer, audio))
        # Update debug info for buffer length.
        self.debug_info = f"Buffer length: {len(self.buffer)} samples"
        
        # When the buffer has enough samples, process a chunk.
        if len(self.buffer) >= int(self.buffer_duration * self.sample_rate):
            chunk_length = int(self.buffer_duration * self.sample_rate)
            chunk = self.buffer[:chunk_length]
            try:
                # Run inference on the chunk.
                result = asr_pipeline(chunk, sampling_rate=self.sample_rate)
                self.last_inference = result  # Save full result for debugging.
                recognized_text = result.get("text", "").strip()
                if recognized_text:
                    self.text_chunks.append(recognized_text)
                else:
                    # Log if the inference returned an empty result.
                    self.debug_info += " | Inference returned empty text."
            except Exception as e:
                self.debug_info += f" | Inference error: {e}"
            # Remove the processed audio from the buffer.
            self.buffer = self.buffer[chunk_length:]
        return frame

st.title("Real-time Speech Recognition with wav2vec2 (Debug Mode)")

# Start the WebRTC streamer to capture audio.
webrtc_ctx = webrtc_streamer(
    key="speech_recognition",
    audio_processor_factory=Wav2Vec2Recognizer,
    media_stream_constraints={"audio": True, "video": False},
)

# Auto-refresh for smoother UI updates.
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=500, key="speech-autorefresh")
except ImportError:
    st.info("For smoother updates, install streamlit-autorefresh: pip install streamlit-autorefresh")

# Display debug information and recognized text.
if webrtc_ctx.audio_processor:
    st.subheader("Debug Information:")
    st.write(webrtc_ctx.audio_processor.debug_info)
    st.write("Last Inference Result:")
    st.write(webrtc_ctx.audio_processor.last_inference)
    
    st.subheader("Recognized Text Chunks:")
    if webrtc_ctx.audio_processor.text_chunks:
        for i, chunk in enumerate(webrtc_ctx.audio_processor.text_chunks, start=1):
            st.write(f"Chunk {i}: {chunk}")
    else:
        st.write("No recognized text yet. Speak continuously for a few seconds...")
