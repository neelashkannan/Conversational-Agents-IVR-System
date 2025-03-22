# solara_site.py
import solara
import sounddevice as sd
import numpy as np
import queue
import threading
import time
from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor 

# Global variables
audio_queue = queue.Queue()
is_recording = False
transcription = "No transcription yet"
debug_log = "Starting up...\n"
sample_rate = 16000  # Required sample rate for wav2vec2

# Function to add to the debug log
def log_debug(message):
    global debug_log
    debug_log += f"{time.strftime('%H:%M:%S')}: {message}\n"
    print(message)  # Also print to console

# Initialize the processor and model
log_debug("Loading wav2vec2 model...")
try:
    wav2vec2_processor = Wav2Vec2Processor.from_pretrained("facebook/wav2vec2-base-960h")
    wav2vec2_model = Wav2Vec2ForCTC.from_pretrained("facebook/wav2vec2-base-960h")
    log_debug("Model loaded successfully")
except Exception as e:
    error_msg = f"Error loading wav2vec2 model: {e}"
    log_debug(error_msg)
    # Provide fallbacks if loading fails
    wav2vec2_processor = None
    wav2vec2_model = None

# Audio callback function
def audio_callback(indata, frames, time_info, status):
    if status:
        log_debug(f"Audio callback error: {status}")
    if is_recording:
        log_debug(f"Audio received: {len(indata)} samples")
        audio_queue.put(indata.copy())

# Process audio and update transcription
def process_audio():
    global transcription
    
    log_debug("Audio processing thread started")
    
    # Start audio stream
    try:
        log_debug("Initializing audio stream...")
        stream = sd.InputStream(callback=audio_callback,
                              channels=1,
                              samplerate=sample_rate,
                              blocksize=int(sample_rate * 0.5))  # Process 0.5s chunks
        stream.start()
        log_debug("Audio stream started")
        
        while True:
            if not audio_queue.empty():
                audio_data = audio_queue.get()
                log_debug(f"Processing audio chunk: {audio_data.shape}")
                audio_data = audio_data.flatten()
                
                if wav2vec2_processor is not None and wav2vec2_model is not None:
                    # Convert to PyTorch tensor
                    import torch
                    try:
                        input_values = wav2vec2_processor(
                            audio_data, 
                            sampling_rate=sample_rate, 
                            return_tensors="pt"
                        ).input_values
                        
                        # Get logits from model
                        with torch.no_grad():
                            logits = wav2vec2_model(input_values).logits
                        
                        # Get predicted ids
                        predicted_ids = torch.argmax(logits, dim=-1)
                        
                        # Convert ids to text
                        transcribed_text = wav2vec2_processor.batch_decode(predicted_ids)[0]
                        log_debug(f"Transcribed text: '{transcribed_text}'")
                        
                        # Update the transcription
                        transcription += " " + transcribed_text
                        log_debug(f"Updated transcription: '{transcription}'")
                    except Exception as e:
                        log_debug(f"Error during transcription: {e}")
                else:
                    log_debug("Model not loaded, cannot transcribe")
            
            # Small delay to prevent CPU overuse
            time.sleep(0.1)
            
    except Exception as e:
        log_debug(f"Error in audio processing thread: {e}")
    finally:
        if 'stream' in locals():
            stream.stop()
            stream.close()
            log_debug("Audio stream closed")

# Start audio processing in a separate thread
audio_thread = None

def start_audio_processing():
    global audio_thread
    if audio_thread is None or not audio_thread.is_alive():
        log_debug("Starting audio processing thread")
        audio_thread = threading.Thread(target=process_audio, daemon=True)
        audio_thread.start()
        log_debug("Audio thread started")
        return True
    return False

# Button press/release handlers
def on_button_press():
    global is_recording, transcription
    log_debug("Button pressed - starting recording")
    is_recording = True
    transcription = ""  # Clear previous transcription

def on_button_release():
    global is_recording
    log_debug("Button released - stopping recording")
    is_recording = False

# Test microphone function
def test_microphone():
    try:
        log_debug("Testing microphone...")
        devices = sd.query_devices()
        log_debug(f"Available audio devices: {devices}")
        
        # Try to get default input device
        default_device = sd.query_devices(kind='input')
        log_debug(f"Default input device: {default_device}")
        
        # Try recording a short sample
        duration = 1  # seconds
        recording = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1)
        sd.wait()
        log_debug(f"Recorded test audio: shape={recording.shape}, min={recording.min()}, max={recording.max()}")
        return "Microphone test completed, see logs for details"
    except Exception as e:
        error_msg = f"Microphone test failed: {e}"
        log_debug(error_msg)
        return error_msg

# Start the audio thread
start_result = start_audio_processing()
log_debug(f"Audio processing thread start result: {start_result}")

# Main Solara UI component
@solara.component
def Page():
    global transcription, debug_log
    
    # Use React state for the transcription and debug log
    current_text, set_current_text = solara.use_state("")
    current_debug, set_current_debug = solara.use_state("")
    mic_test_result, set_mic_test_result = solara.use_state("")
    
    # Function to update the transcription display
    def update_display():
        set_current_text(transcription)
        set_current_debug(debug_log)
    
    # Function to test microphone
    def run_mic_test():
        result = test_microphone()
        set_mic_test_result(result)
    
    # UI layout
    with solara.Column(align="center", style={"margin": "2rem"}):
        solara.Title("Real-time Speech-to-Text")
        solara.Markdown("Press and hold the button to speak, then click Update to see the transcription")
        
        with solara.Row():
            solara.Button(
                "Press and Hold to Speak",
                on_mouse_down=on_button_press,
                on_mouse_up=on_button_release,
                style={"height": "5rem", "fontSize": "1.5rem"}
            )
            
            solara.Button(
                "Update Display",
                on_click=update_display,
                style={"height": "5rem", "fontSize": "1.5rem"}
            )
            
            solara.Button(
                "Test Microphone",
                on_click=run_mic_test,
                style={"height": "5rem", "fontSize": "1.5rem"}
            )
        
        # Show microphone test result if available
        if mic_test_result:
            with solara.Card(style={"width": "100%", "margin-top": "1rem", "padding": "1rem"}):
                solara.Markdown("## Microphone Test Result")
                solara.Markdown(mic_test_result)
        
        with solara.Card(style={"width": "100%", "margin-top": "1rem", "padding": "1rem", "min-height": "10rem"}):
            solara.Markdown("## Transcription")
            solara.Markdown(current_text if current_text else "No transcription available yet")
        
        with solara.Card(style={"width": "100%", "margin-top": "1rem", "padding": "1rem", "max-height": "20rem", "overflow": "auto"}):
            solara.Markdown("## Debug Logs")
            solara.Markdown(f"```\n{current_debug}\n```")

# Requirements (save as requirements.txt):
# solara
# sounddevice
# numpy
# torch
# transformers