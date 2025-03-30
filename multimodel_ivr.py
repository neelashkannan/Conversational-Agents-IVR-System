#!/usr/bin/env python
"""
Multimodal Interactive Voice Response (IVR) System
All-in-one implementation with Flask, Faster-Whisper, Octave TTS, and Ollama

Usage:
    python multimodal_ivr.py

Requirements:
    pip install flask flask-socketio faster-whisper pydub requests sounddevice numpy soundfile python-dotenv gtts
"""

import os
import io
import json
import uuid
import base64
import logging
import tempfile
import threading
import numpy as np
import requests
from datetime import datetime
from pathlib import Path

# Flask and extensions
from flask import Flask, render_template_string, request, jsonify, session
from flask_socketio import SocketIO, emit
from dotenv import load_dotenv

# Speech processing
try:
    from faster_whisper import WhisperModel
except ImportError:
    print("WARNING: faster-whisper not installed. Speech recognition will not work.")
    print("Install with: pip install faster-whisper")
    WhisperModel = None

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Create Flask application
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-please-change')
socketio = SocketIO(app, cors_allowed_origins="*")

# Global variables
OLLAMA_API_URL = os.environ.get('OLLAMA_API_URL', 'http://localhost:11434/api')
OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL', 'tinyllama')
WHISPER_MODEL_SIZE = os.environ.get('WHISPER_MODEL_SIZE', 'base')
USE_CUDA = os.environ.get('USE_CUDA', '0') == '1'
OCTAVE_TTS_API_URL = os.environ.get('OCTAVE_TTS_API_URL', 'http://localhost:8080/api/tts')
OCTAVE_TTS_API_KEY = os.environ.get('OCTAVE_TTS_API_KEY', '')

# Create data directory if not exists
Path("data").mkdir(exist_ok=True)

# ----- Speech Recognition Service -----

class SpeechRecognitionService:
    """Service for speech recognition using Faster-Whisper"""
    
    def __init__(self, model_size="base"):
        """Initialize the Whisper model
        
        Args:
            model_size: Size of the Whisper model to use (tiny, base, small, medium, large)
        """
        self.model_size = model_size
        self.model = None
        
        # Initialize in a separate thread to avoid blocking
        if WhisperModel:
            threading.Thread(target=self._initialize_model).start()
        
    def _initialize_model(self):
        """Initialize the Whisper model in a background thread"""
        try:
            # Use CUDA if available, otherwise CPU
            device = "cuda" if USE_CUDA else "cpu"
            compute_type = "float16" if device == "cuda" else "int8"
            
            logger.info(f"Loading Whisper model {self.model_size} on {device}...")
            self.model = WhisperModel(self.model_size, device=device, compute_type=compute_type)
            logger.info("Whisper model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading Whisper model: {str(e)}")
    
    def transcribe_audio(self, audio_data, sample_rate=16000):
        """Transcribe audio data to text
        
        Args:
            audio_data: Audio data as bytes or numpy array
            sample_rate: Sample rate of the audio
            
        Returns:
            str: Transcribed text
        """
        if not WhisperModel:
            logger.error("faster-whisper not installed")
            return "Speech recognition unavailable. Please install faster-whisper."
            
        if not self.model:
            logger.error("Whisper model not loaded yet")
            return "Speech recognition model is still loading. Please try again in a moment."
            
        try:
            # Convert audio bytes to temporary file if needed
            if isinstance(audio_data, (bytes, bytearray)):
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as temp_file:
                    temp_file.write(audio_data)
                    temp_file.flush()
                    # Perform transcription
                    segments, info = self.model.transcribe(temp_file.name, language="en")
            else:
                # Directly process numpy array
                segments, info = self.model.transcribe(audio_data, language="en")
            
            # Collect transcription from segments
            transcription = " ".join(segment.text for segment in segments)
            logger.info(f"Transcription: {transcription}")
            return transcription.strip()
            
        except Exception as e:
            logger.error(f"Error in transcription: {str(e)}")
            return ""


# ----- Text-to-Speech Service -----

class TextToSpeechService:
    """Service for text-to-speech synthesis using Octave TTS API or fallback"""
    
    def __init__(self, voice="alloy"):
        """Initialize the TTS service
        
        Args:
            voice: Voice to use for synthesis (varies by provider)
        """
        self.voice = voice
        self.api_url = OCTAVE_TTS_API_URL
        self.api_key = OCTAVE_TTS_API_KEY
        self.use_fallback = True  # Default to fallback
        
        # Test if Octave TTS is available
        try:
            response = requests.get(self.api_url, timeout=1)
            if response.status_code == 200:
                self.use_fallback = False
                logger.info("Octave TTS service is available")
            else:
                logger.warning("Octave TTS returned non-200 status code, using fallback")
        except requests.exceptions.RequestException:
            logger.warning("Could not connect to Octave TTS, using fallback TTS")
    
    def synthesize_speech(self, text):
        """Convert text to speech
        
        Args:
            text: Text to synthesize
            
        Returns:
            bytes: Audio data in bytes
        """
        if self.use_fallback:
            return self._fallback_tts(text)
            
        try:
            # Send request to Octave TTS API
            payload = {
                "text": text,
                "voice": self.voice,
                "format": "wav"
            }
            
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            response = requests.post(self.api_url, json=payload, headers=headers, timeout=5)
            
            if response.status_code == 200:
                return response.content
            else:
                logger.error(f"TTS API error: {response.status_code} - {response.text}")
                # Fallback to gTTS
                return self._fallback_tts(text)
                
        except Exception as e:
            logger.error(f"Error in speech synthesis: {str(e)}")
            return self._fallback_tts(text)
    
    def _fallback_tts(self, text):
        """Fallback TTS method when the primary method fails
        
        Args:
            text: Text to synthesize
            
        Returns:
            bytes: Audio data in bytes
        """
        try:
            # Import gtts only when needed (fallback)
            from gtts import gTTS
            
            tts = gTTS(text=text, lang='en')
            mp3_fp = io.BytesIO()
            tts.write_to_fp(mp3_fp)
            mp3_fp.seek(0)
            
            # Return the MP3 data
            return mp3_fp.read()
            
        except Exception as e:
            logger.error(f"Fallback TTS error: {str(e)}")
            # Return empty bytes
            return b""


# ----- Ollama LLM Service -----

class OllamaService:
    """Service for natural language processing using Ollama LLM"""
    
    def __init__(self, model_name="llama3", api_url=None):
        """Initialize the Ollama service
        
        Args:
            model_name: Name of the Ollama model to use
            api_url: URL of the Ollama API server
        """
        self.model_name = model_name
        self.api_url = api_url or OLLAMA_API_URL
        self.is_available = False
        
        # Check if Ollama is available
        try:
            response = requests.get(f"{self.api_url}/health", timeout=1)
            if response.status_code == 200:
                self.is_available = True
                logger.info(f"Ollama service is available with model {model_name}")
            else:
                logger.warning("Ollama service returned non-200 status code")
        except requests.exceptions.RequestException:
            logger.warning("Could not connect to Ollama service")
        
    def generate_response(self, prompt, system_prompt=None, temperature=0.7, max_tokens=1024):
        """Generate a response from the LLM
        
        Args:
            prompt: User's input prompt
            system_prompt: Optional system prompt to guide the model
            temperature: Controls randomness (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            
        Returns:
            str: Generated response
        """
        if not self.is_available:
            return "LLM service is not available. Using rule-based responses instead."
            
        try:
            # Prepare request to Ollama API
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens
                }
            }
            
            # Add system prompt if provided
            if system_prompt:
                payload["system"] = system_prompt
                
            # Make API request
            response = requests.post(
                f"{self.api_url}/generate",
                json=payload,
                timeout=30
            )
            
            # Parse response
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "")
            else:
                logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                return "I'm sorry, I couldn't process that request."
                
        except Exception as e:
            logger.error(f"Error in LLM generation: {str(e)}")
            return "I'm sorry, there was an error processing your request."
    
    def extract_intent(self, user_input):
        """Extract intent and entities from user input
        
        Args:
            user_input: User's input text
            
        Returns:
            dict: Intent and entities
        """
        if not self.is_available:
            # Fallback to rule-based intent extraction
            return self._rule_based_intent_extraction(user_input)
            
        system_prompt = """
        You are an assistant for an IVR system. Extract the user's intent and any relevant entities from their input.
        Respond with a JSON object that includes:
        - intent: The primary user intent (e.g., "schedule_appointment", "billing_inquiry", "speak_to_agent", "get_hours")
        - entities: Any relevant entities (e.g., {"date": "2023-04-15", "time": "14:30"})
        - confidence: Your confidence score (0.0 to 1.0)
        
        Common intents in our system:
        - schedule_appointment
        - cancel_appointment
        - billing_inquiry
        - account_info
        - location_hours
        - speak_to_agent
        - general_inquiry
        """
        
        prompt = f"Extract intent from: '{user_input}'"
        
        try:
            response = self.generate_response(prompt, system_prompt, temperature=0.3)
            
            # Extract JSON from response (handle cases where LLM adds explanation text)
            try:
                # Try to parse entire response
                intent_data = json.loads(response)
            except json.JSONDecodeError:
                # Try to extract JSON if there's surrounding text
                import re
                json_match = re.search(r'({.*})', response, re.DOTALL)
                if json_match:
                    try:
                        intent_data = json.loads(json_match.group(1))
                    except json.JSONDecodeError:
                        # Fallback to default intent
                        intent_data = {"intent": "general_inquiry", "entities": {}, "confidence": 0.5}
                else:
                    # Fallback to default intent
                    intent_data = {"intent": "general_inquiry", "entities": {}, "confidence": 0.5}
            
            return intent_data
            
        except Exception as e:
            logger.error(f"Error in intent extraction: {str(e)}")
            return {"intent": "general_inquiry", "entities": {}, "confidence": 0.5}
    
    def _rule_based_intent_extraction(self, user_input):
        """Simple rule-based intent extraction when Ollama is not available
        
        Args:
            user_input: User's input text
            
        Returns:
            dict: Intent and entities
        """
        user_input = user_input.lower()
        
        # Default intent
        intent = "general_inquiry"
        entities = {}
        confidence = 0.7
        
        # Simple keyword mapping
        if any(word in user_input for word in ["schedule", "appointment", "book", "reserve"]):
            intent = "schedule_appointment"
            confidence = 0.8
        elif any(word in user_input for word in ["cancel", "reschedule"]):
            intent = "cancel_appointment"
            confidence = 0.8
        elif any(word in user_input for word in ["bill", "billing", "payment", "pay", "account"]):
            intent = "billing_inquiry"
            confidence = 0.8
        elif any(word in user_input for word in ["location", "address", "hour", "open", "close"]):
            intent = "location_hours"
            confidence = 0.9
        elif any(word in user_input for word in ["agent", "human", "person", "representative", "speak", "talk"]):
            intent = "speak_to_agent"
            confidence = 0.9
        
        # Simple entity extraction (very basic example)
        if "tomorrow" in user_input:
            from datetime import date, timedelta
            tomorrow = date.today() + timedelta(days=1)
            entities["date"] = tomorrow.isoformat()
        
        return {
            "intent": intent,
            "entities": entities,
            "confidence": confidence
        }


# ----- Service Singletons -----

# Initialize services
speech_recognition_service = SpeechRecognitionService(model_size=WHISPER_MODEL_SIZE)
tts_service = TextToSpeechService(voice="alloy")
ollama_service = OllamaService(model_name=OLLAMA_MODEL, api_url=OLLAMA_API_URL)


# ----- Route Handlers -----

@app.route('/')
def index():
    """Render the main IVR interface"""
    # Generate a unique session ID if not already present
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    
    return render_template_string(INDEX_HTML)

@app.route('/phone')
def phone_interface():
    """Render the phone-only interface"""
    # Generate a unique session ID if not already present
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    
    return render_template_string(PHONE_HTML)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'service': 'multimodal-ivr',
        'version': '1.0.0'
    })

@app.route('/api/speech/recognize', methods=['POST'])
def recognize_speech():
    """Endpoint for speech recognition"""
    # Check if file is present in request
    if 'audio' not in request.files and 'audio_data' not in request.json:
        return jsonify({
            'error': 'No audio file or data provided'
        }), 400
    
    try:
        # Process audio file if provided
        if 'audio' in request.files:
            audio_file = request.files['audio']
            audio_data = audio_file.read()
        else:
            # Process base64 audio data if provided
            audio_b64 = request.json.get('audio_data')
            audio_data = base64.b64decode(audio_b64.split(',')[1] if ',' in audio_b64 else audio_b64)
        
        # Perform transcription
        transcription = speech_recognition_service.transcribe_audio(audio_data)
        
        return jsonify({
            'status': 'success',
            'transcription': transcription
        })
    
    except Exception as e:
        logger.error(f"Error in speech recognition: {str(e)}")
        return jsonify({
            'error': 'Failed to process audio',
            'details': str(e)
        }), 500

@app.route('/api/speech/synthesize', methods=['POST'])
def synthesize_speech():
    """Endpoint for text-to-speech synthesis"""
    # Validate request
    if not request.json or 'text' not in request.json:
        return jsonify({
            'error': 'No text provided'
        }), 400
    
    text = request.json.get('text')
    voice = request.json.get('voice', 'alloy')  # Default voice
    
    try:
        # Synthesize speech
        audio_data = tts_service.synthesize_speech(text)
        
        # Return base64 encoded audio data
        audio_b64 = base64.b64encode(audio_data).decode('utf-8')
        
        return jsonify({
            'status': 'success',
            'audio_data': audio_b64
        })
    
    except Exception as e:
        logger.error(f"Error in speech synthesis: {str(e)}")
        return jsonify({
            'error': 'Failed to synthesize speech',
            'details': str(e)
        }), 500


# ----- WebSocket Event Handlers -----

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info(f"Client connected: {request.sid}")
    emit('connection_status', {'status': 'connected'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info(f"Client disconnected: {request.sid}")

@socketio.on('start_session')
def handle_start_session(data):
    """Initialize a new session"""
    session_id = data.get('session_id') or str(uuid.uuid4())
    logger.info(f"Starting new session: {session_id}")
    
    # Send initial IVR greeting
    welcome_message = "Welcome to Super Company. How can I help you today?"
    
    # Generate audio for welcome message
    audio_data = tts_service.synthesize_speech(welcome_message)
    
    # Convert audio data to base64 for sending over WebSocket
    audio_base64 = base64.b64encode(audio_data).decode('utf-8')
    
    # Prepare menu options
    menu_options = [
        {"id": "customer_service", "text": "Customer Service"},
        {"id": "appointments", "text": "Schedule an Appointment"},
        {"id": "billing", "text": "Billing and Account Information"},
        {"id": "location", "text": "Location and Hours"},
        {"id": "agent", "text": "Speak to a Live Agent"}
    ]
    
    # Send response to client
    emit('ivr_response', {
        'session_id': session_id,
        'text': welcome_message,
        'audio': audio_base64,
        'menu_options': menu_options
    })

@socketio.on('voice_input')
def handle_voice_input(data):
    """Process voice input from the client"""
    session_id = data.get('session_id')
    audio_data = data.get('audio')
    
    logger.info(f"Received voice input for session {session_id}")
    
    # Check if audio data is provided
    if not audio_data:
        emit('error', {'message': 'No audio data received'})
        return
    
    try:
        # Decode base64 audio
        audio_bytes = base64.b64decode(audio_data.split(',')[1] if ',' in audio_data else audio_data)
        
        # Transcribe audio
        transcription = speech_recognition_service.transcribe_audio(audio_bytes)
        
        # Process the transcription
        process_user_input(transcription, session_id)
        
    except Exception as e:
        logger.error(f"Error processing voice input: {str(e)}")
        emit('error', {'message': 'Error processing voice input'})

@socketio.on('text_input')
def handle_text_input(data):
    """Process text input from the client"""
    session_id = data.get('session_id')
    text = data.get('text')
    
    logger.info(f"Received text input for session {session_id}: {text}")
    
    # Process the text input
    process_user_input(text, session_id)

@socketio.on('menu_selection')
def handle_menu_selection(data):
    """Process menu selection from the client"""
    session_id = data.get('session_id')
    selection_id = data.get('selection_id')
    
    logger.info(f"Received menu selection for session {session_id}: {selection_id}")
    
    # Map selection ID to intent
    intent_map = {
        "customer_service": "general_inquiry",
        "appointments": "schedule_appointment",
        "billing": "billing_inquiry",
        "location": "location_hours",
        "agent": "speak_to_agent"
    }
    
    # Process the selection based on the mapping
    intent = intent_map.get(selection_id, "general_inquiry")
    process_intent(intent, {}, session_id)


# ----- Business Logic Functions -----

def process_user_input(user_input, session_id):
    """Process user input and determine intent"""
    # Extract intent using LLM
    intent_data = ollama_service.extract_intent(user_input)
    logger.info(f"Extracted intent: {intent_data}")
    
    # Process the intent
    intent = intent_data.get("intent", "general_inquiry")
    entities = intent_data.get("entities", {})
    
    process_intent(intent, entities, session_id)

def process_intent(intent, entities, session_id):
    """Handle different intents and generate appropriate responses"""
    # Initialize response
    response_text = ""
    menu_options = []
    redirect = None
    
    # Handle different intents
    if intent == "schedule_appointment":
        response_text = "I'd be happy to help you schedule an appointment. What day would you prefer?"
        menu_options = [
            {"id": "today", "text": "Today"},
            {"id": "tomorrow", "text": "Tomorrow"},
            {"id": "next_week", "text": "Next Week"},
            {"id": "specify_date", "text": "Specify a Different Date"}
        ]
    
    elif intent == "billing_inquiry":
        response_text = "For billing inquiries, I'll need your account information. What's your account number or the phone number associated with your account?"
    
    elif intent == "location_hours":
        response_text = "Our main location is at 123 Business Ave. We're open Monday to Friday from 9 AM to 5 PM, and Saturday from 10 AM to 2 PM. Is there anything else you'd like to know?"
    
    elif intent == "speak_to_agent":
        response_text = "I'll connect you with the next available agent. Please hold while I transfer your call."
        redirect = "/agent_queue"
    
    else:  # Default for general_inquiry and unknown intents
        response_text = "How can I assist you today? You can ask about appointments, billing, location and hours, or speak to a live agent."
        menu_options = [
            {"id": "customer_service", "text": "Customer Service"},
            {"id": "appointments", "text": "Schedule an Appointment"},
            {"id": "billing", "text": "Billing and Account Information"},
            {"id": "location", "text": "Location and Hours"},
            {"id": "agent", "text": "Speak to a Live Agent"}
        ]
    
    # Generate audio for response
    audio_data = tts_service.synthesize_speech(response_text)
    audio_base64 = base64.b64encode(audio_data).decode('utf-8')
    
    # Send response to client
    socketio.emit('ivr_response', {
        'session_id': session_id,
        'text': response_text,
        'audio': audio_base64,
        'menu_options': menu_options,
        'redirect': redirect
    }, room=request.sid)


# ----- HTML Templates -----

# Main multimodal interface
INDEX_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Super Company - Multimodal IVR</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.6.1/socket.io.min.js"></script>
    <style>
        /* CSS styles */
        :root {
            --primary-color: #2196f3;
            --primary-dark: #1976d2;
            --primary-light: #bbdefb;
            --secondary-color: #4caf50;
            --secondary-dark: #388e3c;
            --secondary-light: #c8e6c9;
            --background-light: #f8f9fa;
            --background-dark: #343a40;
            --text-light: #f8f9fa;
            --text-dark: #343a40;
            --gray-light: #e9ecef;
            --gray-medium: #adb5bd;
            --gray-dark: #495057;
            --danger: #dc3545;
            --warning: #ffc107;
            --success: #28a745;
            --border-radius: 8px;
            --shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            --transition: all 0.3s ease;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
            line-height: 1.6;
            color: var(--text-dark);
            background-color: var(--background-light);
        }

        button {
            cursor: pointer;
            border: none;
            background: none;
            font-family: inherit;
        }

        button:focus {
            outline: none;
        }

        input {
            font-family: inherit;
            border: none;
            outline: none;
        }

        .app-container {
            display: flex;
            flex-direction: column;
            min-height: 100vh;
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 20px;
        }

        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px 0;
            border-bottom: 1px solid var(--gray-light);
        }

        .logo {
            display: flex;
            align-items: center;
        }

        .company-name {
            font-size: 1.5rem;
            font-weight: bold;
            color: var(--primary-dark);
        }

        .header-controls button {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            background-color: var(--primary-light);
            color: var(--primary-dark);
            display: flex;
            align-items: center;
            justify-content: center;
            transition: var(--transition);
        }

        .header-controls button:hover {
            background-color: var(--primary-color);
            color: var(--text-light);
        }

        main {
            flex: 1;
            padding: 30px 0;
        }

        footer {
            text-align: center;
            padding: 20px 0;
            border-top: 1px solid var(--gray-light);
            color: var(--gray-dark);
            font-size: 0.875rem;
        }

        .modal-interface {
            display: flex;
            gap: 30px;
        }

        .phone-display {
            flex: 1;
            background-color: white;
            border-radius: var(--border-radius);
            box-shadow: var(--shadow);
            overflow: hidden;
            display: flex;
            flex-direction: column;
            height: 600px;
            max-width: 350px;
            border: 10px solid var(--background-dark);
            border-radius: 30px;
            position: relative;
        }

        .guide-panel {
            flex: 1;
            padding: 20px;
            background-color: white;
            border-radius: var(--border-radius);
            box-shadow: var(--shadow);
        }

        .display-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 15px;
            background-color: var(--background-dark);
            color: var(--text-light);
        }

        .conversation-area {
            flex: 1;
            padding: 15px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 15px;
        }

        .message {
            max-width: 80%;
            padding: 10px 15px;
            border-radius: 18px;
            position: relative;
            line-height: 1.4;
        }

        .message.user {
            align-self: flex-end;
            background-color: var(--primary-light);
            color: var(--text-dark);
            border-bottom-right-radius: 4px;
        }

        .message.system {
            align-self: flex-start;
            background-color: var(--gray-light);
            color: var(--text-dark);
            border-bottom-left-radius: 4px;
        }

        .menu-options {
            display: flex;
            flex-direction: column;
            gap: 8px;
            padding: 0 15px 15px;
        }

        .menu-option {
            padding: 10px 15px;
            background-color: var(--primary-light);
            color: var(--primary-dark);
            border-radius: var(--border-radius);
            transition: var(--transition);
            text-align: left;
        }

        .menu-option:hover {
            background-color: var(--primary-color);
            color: var(--text-light);
        }

        .input-area {
            display: flex;
            padding: 10px 15px;
            border-top: 1px solid var(--gray-light);
            background-color: white;
        }

        .input-area input {
            flex: 1;
            padding: 8px 0;
        }

        .input-area button {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            background-color: var(--primary-light);
            color: var(--primary-dark);
            display: flex;
            align-items: center;
            justify-content: center;
            margin-left: 8px;
            transition: var(--transition);
        }

        .input-area button:hover {
            background-color: var(--primary-color);
            color: var(--text-light);
        }

        .voice-btn {
            background-color: var(--secondary-light) !important;
            color: var(--secondary-dark) !important;
        }

        .voice-btn:hover {
            background-color: var(--secondary-color) !important;
            color: var(--text-light) !important;
        }

        .voice-btn.active {
            background-color: var(--danger) !important;
            color: var(--text-light) !important;
            animation: pulse 1.5s infinite;
        }

        @keyframes pulse {
            0% {
                box-shadow: 0 0 0 0 rgba(220, 53, 69, 0.7);
            }
            70% {
                box-shadow: 0 0 0 10px rgba(220, 53, 69, 0);
            }
            100% {
                box-shadow: 0 0 0 0 rgba(220, 53, 69, 0);
            }
        }

        .status-panel {
            margin-top: 20px;
            padding: 15px;
            background-color: var(--gray-light);
            border-radius: var(--border-radius);
        }

        .status-panel h3 {
            margin-bottom: 10px;
            font-size: 1rem;
        }

        .status-item {
            display: flex;
            align-items: center;
            margin-bottom: 10px;
        }

        .status-indicator {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 10px;
        }

        .status-indicator.disconnected {
            background-color: var(--danger);
        }

        .status-indicator.connected {
            background-color: var(--success);
        }

        .status-indicator.inactive {
            background-color: var(--gray-medium);
        }

        .status-indicator.active {
            background-color: var(--success);
        }

        .guide-panel h2 {
            margin-bottom: 15px;
            color: var(--primary-dark);
        }

        .guide-panel p {
            margin-bottom: 15px;
        }

        .guide-panel ul {
            margin-bottom: 15px;
            padding-left: 20px;
        }

        .guide-panel li {
            margin-bottom: 8px;
        }

        .guide-panel i {
            color: var(--primary-dark);
            width: 20px;
            text-align: center;
            margin-right: 5px;
        }

        @media (max-width: 768px) {
            .modal-interface {
                flex-direction: column;
            }
            
            .phone-display {
                max-width: none;
                width: 100%;
            }
        }
    </style>
</head>
<body>
    <div class="app-container">
        <header>
            <div class="logo">
                <span class="company-name">Super Company</span>
            </div>
            <div class="header-controls">
                <button id="switchModeBtn" class="mode-switch" title="Switch to voice-only mode">
                    <i class="fas fa-phone"></i>
                </button>
            </div>
        </header>
        
        <main>
            <div class="modal-interface">
                <div class="phone-display">
                    <div class="display-header">
                        <span class="time" id="currentTime">12:34</span>
                        <span class="status">
                            <i class="fas fa-signal"></i>
                            <i class="fas fa-wifi"></i>
                            <i class="fas fa-battery-three-quarters"></i>
                        </span>
                    </div>
                    
                    <div class="conversation-area" id="conversationArea">
                        <!-- Conversation messages will be dynamically added here -->
                    </div>
                    
                    <div class="menu-options" id="menuOptions">
                        <!-- Menu options will be dynamically added here -->
                    </div>
                    
                    <div class="input-area">
                        <input type="text" id="textInput" placeholder="Type your message...">
                        <button id="sendTextBtn" title="Send message">
                            <i class="fas fa-paper-plane"></i>
                        </button>
                        <button id="voiceInputBtn" class="voice-btn" title="Speak">
                            <i class="fas fa-microphone"></i>
                        </button>
                    </div>
                </div>
                
                <div class="guide-panel">
                    <h2>How to Use</h2>
                    <p>You can interact with our system using:</p>
                    <ul>
                        <li><i class="fas fa-keyboard"></i> <strong>Text:</strong> Type your query in the input field</li>
                        <li><i class="fas fa-microphone"></i> <strong>Voice:</strong> Click the microphone button and speak</li>
                        <li><i class="fas fa-mouse-pointer"></i> <strong>Menu:</strong> Click on any menu option that appears</li>
                    </ul>
                    <p>You can freely switch between these methods at any time.</p>
                    
                    <div class="status-panel">
                        <h3>System Status</h3>
                        <div id="connectionStatus" class="status-item">
                            <span class="status-indicator disconnected"></span>
                            <span class="status-text">Disconnected</span>
                        </div>
                        <div id="micStatus" class="status-item">
                            <span class="status-indicator inactive"></span>
                            <span class="status-text">Microphone inactive</span>
                        </div>
                    </div>
                </div>
            </div>
        </main>
        
        <footer>
            <p>&copy; 2025 Super Company. All rights reserved.</p>
        </footer>
    </div>
    
    <!-- Audio element for playing responses -->
    <audio id="responseAudio" style="display: none;"></audio>
    
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            // DOM Elements
            const conversationArea = document.getElementById('conversationArea');
            const menuOptions = document.getElementById('menuOptions');
            const textInput = document.getElementById('textInput');
            const sendTextBtn = document.getElementById('sendTextBtn');
            const voiceInputBtn = document.getElementById('voiceInputBtn');
            const switchModeBtn = document.getElementById('switchModeBtn');
            const responseAudio = document.getElementById('responseAudio');
            const connectionStatus = document.getElementById('connectionStatus');
            const micStatus = document.getElementById('micStatus');
            const currentTimeEl = document.getElementById('currentTime');
            
            // State variables
            let sessionId = null;
            let isRecording = false;
            let mediaRecorder = null;
            let audioChunks = [];
            let socket = null;
            
            // Update current time
            function updateCurrentTime() {
                const now = new Date();
                const hours = now.getHours().toString().padStart(2, '0');
                const minutes = now.getMinutes().toString().padStart(2, '0');
                currentTimeEl.textContent = `${hours}:${minutes}`;
            }
            
            // Update time immediately and then every minute
            updateCurrentTime();
            setInterval(updateCurrentTime, 60000);
            
            // Initialize WebSocket connection
            function initializeSocket() {
                socket = io();
                
                socket.on('connect', function() {
                    console.log('Connected to server');
                    connectionStatus.innerHTML = '<span class="status-indicator connected"></span><span class="status-text">Connected</span>';
                    
                    // Start IVR session when connected
                    startIVRSession();
                });
                
                socket.on('disconnect', function() {
                    console.log('Disconnected from server');
                    connectionStatus.innerHTML = '<span class="status-indicator disconnected"></span><span class="status-text">Disconnected</span>';
                });
                
                socket.on('ivr_response', handleIVRResponse);
                
                socket.on('error', function(data) {
                    console.error('Error:', data.message);
                    addSystemMessage('Sorry, there was an error processing your request. Please try again.');
                });
            }
            
            // Start a new IVR session
            function startIVRSession() {
                sessionId = getCookie('session_id') || generateUUID();
                setCookie('session_id', sessionId, 1); // Store for 1 day
                
                console.log('Starting IVR session:', sessionId);
                socket.emit('start_session', { session_id: sessionId });
            }
            
            // Handle IVR response from server
            function handleIVRResponse(data) {
                console.log('Received IVR response:', data);
                
                // Add system message to conversation
                if (data.text) {
                    addSystemMessage(data.text);
                }
                
                // Play audio response if available
                if (data.audio) {
                    playAudioResponse(data.audio);
                }
                
                // Display menu options if available
                if (data.menu_options && data.menu_options.length > 0) {
                    displayMenuOptions(data.menu_options);
                } else {
                    // Clear menu options if none provided
                    menuOptions.innerHTML = '';
                }
                
                // Handle redirect if specified
                if (data.redirect) {
                    setTimeout(() => {
                        window.location.href = data.redirect;
                    }, 1000);
                }
            }
            
            // Add a system message to the conversation
            function addSystemMessage(text) {
                const messageEl = document.createElement('div');
                messageEl.className = 'message system';
                messageEl.textContent = text;
                conversationArea.appendChild(messageEl);
                
                // Scroll to bottom
                conversationArea.scrollTop = conversationArea.scrollHeight;
            }
            
            // Add a user message to the conversation
            function addUserMessage(text) {
                const messageEl = document.createElement('div');
                messageEl.className = 'message user';
                messageEl.textContent = text;
                conversationArea.appendChild(messageEl);
                
                // Scroll to bottom
                conversationArea.scrollTop = conversationArea.scrollHeight;
            }
            
            // Display menu options
            function displayMenuOptions(options) {
                menuOptions.innerHTML = '';
                
                options.forEach(option => {
                    const buttonEl = document.createElement('button');
                    buttonEl.className = 'menu-option';
                    buttonEl.textContent = option.text;
                    buttonEl.dataset.optionId = option.id;
                    
                    buttonEl.addEventListener('click', function() {
                        handleMenuSelection(option.id, option.text);
                    });
                    
                    menuOptions.appendChild(buttonEl);
                });
            }
            
            // Handle menu option selection
            function handleMenuSelection(optionId, optionText) {
                console.log('Selected menu option:', optionId);
                
                // Add user message
                addUserMessage(optionText);
                
                // Send to server
                socket.emit('menu_selection', {
                    session_id: sessionId,
                    selection_id: optionId
                });
            }
            
            // Play audio response
            function playAudioResponse(audioBase64) {
                try {
                    const audioSrc = `data:audio/wav;base64,${audioBase64}`;
                    responseAudio.src = audioSrc;
                    
                    responseAudio.oncanplaythrough = function() {
                        responseAudio.play().catch(error => {
                            console.error('Error playing audio:', error);
                        });
                    };
                    
                    responseAudio.onerror = function() {
                        console.error('Error loading audio');
                    };
                } catch (error) {
                    console.error('Error setting up audio:', error);
                }
            }
            
            // Send text input to server
            function sendTextInput() {
                const text = textInput.value.trim();
                if (!text) return;
                
                console.log('Sending text input:', text);
                
                // Add user message
                addUserMessage(text);
                
                // Send to server
                socket.emit('text_input', {
                    session_id: sessionId,
                    text: text
                });
                
                // Clear input field
                textInput.value = '';
            }
            
            // Handle voice input
            function toggleVoiceInput() {
                if (isRecording) {
                    stopRecording();
                } else {
                    startRecording();
                }
            }
            
            // Start recording audio
            async function startRecording() {
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                    
                    mediaRecorder = new MediaRecorder(stream);
                    audioChunks = [];
                    
                    mediaRecorder.ondataavailable = event => {
                        audioChunks.push(event.data);
                    };
                    
                    mediaRecorder.onstop = async () => {
                        const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                        await sendAudioToServer(audioBlob);
                        
                        // Release microphone
                        stream.getTracks().forEach(track => track.stop());
                    };
                    
                    // Start recording
                    mediaRecorder.start();
                    isRecording = true;
                    
                    // Update UI
                    voiceInputBtn.classList.add('active');
                    voiceInputBtn.innerHTML = '<i class="fas fa-stop"></i>';
                    micStatus.innerHTML = '<span class="status-indicator active"></span><span class="status-text">Microphone active</span>';
                    
                    console.log('Recording started');
                } catch (error) {
                    console.error('Error accessing microphone:', error);
                    alert('Could not access the microphone. Please ensure you have granted permission.');
                }
            }
            
            // Stop recording audio
            function stopRecording() {
                if (mediaRecorder && isRecording) {
                    mediaRecorder.stop();
                    isRecording = false;
                    
                    // Update UI
                    voiceInputBtn.classList.remove('active');
                    voiceInputBtn.innerHTML = '<i class="fas fa-microphone"></i>';
                    micStatus.innerHTML = '<span class="status-indicator inactive"></span><span class="status-text">Microphone inactive</span>';
                    
                    console.log('Recording stopped');
                }
            }
            
            // Send recorded audio to server
            async function sendAudioToServer(audioBlob) {
                try {
                    // Add user "speaking" message
                    addUserMessage('🎤 [Voice input]');
                    
                    // Convert Blob to base64
                    const reader = new FileReader();
                    reader.readAsDataURL(audioBlob);
                    
                    reader.onloadend = function() {
                        const base64Audio = reader.result;
                        
                        // Send to server
                        socket.emit('voice_input', {
                            session_id: sessionId,
                            audio: base64Audio
                        });
                    };
                } catch (error) {
                    console.error('Error sending audio to server:', error);
                }
            }
            
            // Switch between multimodal and voice-only mode
            function switchMode() {
                window.location.href = '/phone';
            }
            
            // Event listeners
            sendTextBtn.addEventListener('click', sendTextInput);
            voiceInputBtn.addEventListener('click', toggleVoiceInput);
            switchModeBtn.addEventListener('click', switchMode);
            
            textInput.addEventListener('keypress', function(event) {
                if (event.key === 'Enter') {
                    sendTextInput();
                }
            });
            
            // Initialize the app
            initializeSocket();
            
            // Utility functions
            function generateUUID() {
                return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
                    const r = Math.random() * 16 | 0;
                    const v = c === 'x' ? r : (r & 0x3 | 0x8);
                    return v.toString(16);
                });
            }
            
            function setCookie(name, value, days) {
                const expires = new Date();
                expires.setTime(expires.getTime() + days * 24 * 60 * 60 * 1000);
                document.cookie = `${name}=${value};expires=${expires.toUTCString()};path=/`;
            }
            
            function getCookie(name) {
                const nameEQ = `${name}=`;
                const ca = document.cookie.split(';');
                for (let i = 0; i < ca.length; i++) {
                    let c = ca[i];
                    while (c.charAt(0) === ' ') c = c.substring(1, c.length);
                    if (c.indexOf(nameEQ) === 0) return c.substring(nameEQ.length, c.length);
                }
                return null;
            }
        });
    </script>
</body>
</html>
"""

# Phone-only interface
PHONE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Super Company - Voice IVR</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.6.1/socket.io.min.js"></script>
    <style>
        /* CSS styles for phone interface */
        :root {
            --primary-color: #2196f3;
            --primary-dark: #1976d2;
            --primary-light: #bbdefb;
            --secondary-color: #4caf50;
            --secondary-dark: #388e3c;
            --secondary-light: #c8e6c9;
            --background-light: #f8f9fa;
            --background-dark: #343a40;
            --text-light: #f8f9fa;
            --text-dark: #343a40;
            --gray-light: #e9ecef;
            --gray-medium: #adb5bd;
            --gray-dark: #495057;
            --danger: #dc3545;
            --warning: #ffc107;
            --success: #28a745;
            --border-radius: 8px;
            --shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            --transition: all 0.3s ease;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
            line-height: 1.6;
            color: var(--text-dark);
            background-color: var(--background-light);
        }

        button {
            cursor: pointer;
            border: none;
            background: none;
            font-family: inherit;
        }

        button:focus {
            outline: none;
        }

        .app-container {
            display: flex;
            flex-direction: column;
            min-height: 100vh;
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 20px;
        }

        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px 0;
            border-bottom: 1px solid var(--gray-light);
        }

        .logo {
            display: flex;
            align-items: center;
        }

        .company-name {
            font-size: 1.5rem;
            font-weight: bold;
            color: var(--primary-dark);
        }

        .header-controls button {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            background-color: var(--primary-light);
            color: var(--primary-dark);
            display: flex;
            align-items: center;
            justify-content: center;
            transition: var(--transition);
        }

        .header-controls button:hover {
            background-color: var(--primary-color);
            color: var(--text-light);
        }

        main {
            flex: 1;
            padding: 30px 0;
        }

        footer {
            text-align: center;
            padding: 20px 0;
            border-top: 1px solid var(--gray-light);
            color: var(--gray-dark);
            font-size: 0.875rem;
        }

        .phone-interface {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 20px;
        }

        .phone-display {
            background-color: white;
            border-radius: var(--border-radius);
            box-shadow: var(--shadow);
            overflow: hidden;
            display: flex;
            flex-direction: column;
            height: 600px;
            width: 350px;
            border: 10px solid var(--background-dark);
            border-radius: 30px;
            position: relative;
        }

        .centered {
            margin: 0 auto;
        }

        .display-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 15px;
            background-color: var(--background-dark);
            color: var(--text-light);
        }

        .mode-indicator {
            font-weight: bold;
        }

        .voice-interaction {
            flex: 1;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 20px;
            padding: 20px;
        }

        .voice-status {
            text-align: center;
        }

        .voice-animation {
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 5px;
            height: 50px;
            margin-bottom: 10px;
        }

        .voice-wave {
            width: 5px;
            height: 5px;
            background-color: var(--secondary-color);
            border-radius: 50%;
        }

        .listening .voice-wave {
            animation: wave 1.5s infinite;
        }

        .voice-wave:nth-child(2) {
            animation-delay: 0.2s;
        }

        .voice-wave:nth-child(3) {
            animation-delay: 0.4s;
        }

        .voice-wave:nth-child(4) {
            animation-delay: 0.6s;
        }

        .voice-wave:nth-child(5) {
            animation-delay: 0.8s;
        }

        @keyframes wave {
            0%, 100% {
                height: 5px;
            }
            50% {
                height: 30px;
            }
        }

        .voice-controls {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 10px;
        }

        .large-mic-btn {
            width: 80px;
            height: 80px;
            border-radius: 50%;
            background-color: var(--secondary-light);
            color: var(--secondary-dark);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
            transition: var(--transition);
        }

        .large-mic-btn:hover {
            background-color: var(--secondary-color);
            color: var(--text-light);
        }

        .large-mic-btn.active {
            background-color: var(--danger);
            color: var(--text-light);
            animation: pulse 1.5s infinite;
        }

        .voice-transcript {
            text-align: center;
            padding: 15px;
            background-color: var(--gray-light);
            border-radius: var(--border-radius);
            width: 100%;
        }

        .voice-transcript h3 {
            font-size: 0.875rem;
            color: var(--gray-dark);
            margin-bottom: 5px;
        }

        .dtmf-keypad {
            display: flex;
            flex-direction: column;
            gap: 10px;
            padding: 20px;
            width: 100%;
        }

        .keypad-row {
            display: flex;
            justify-content: space-between;
            gap: 10px;
        }

        .dtmf-key {
            flex: 1;
            aspect-ratio: 1;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            background-color: var(--gray-light);
            border-radius: var(--border-radius);
            font-size: 1.2rem;
            font-weight: bold;
            transition: var(--transition);
        }

        .dtmf-key span {
            font-size: 0.6rem;
            font-weight: normal;
            color: var(--gray-dark);
        }

        .dtmf-key:hover {
            background-color: var(--primary-light);
        }

        .dtmf-key:active {
            background-color: var(--primary-color);
            color: var(--text-light);
        }

        .call-controls {
            display: flex;
            gap: 20px;
            margin-top: 20px;
        }

        .end-call {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 5px;
            padding: 10px 20px;
            background-color: var(--danger);
            color: var(--text-light);
            border-radius: var(--border-radius);
            transition: var(--transition);
        }

        .end-call:hover {
            background-color: #bd2130;
        }

        .switch-to-text {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 5px;
            padding: 10px 20px;
            background-color: var(--primary-light);
            color: var(--primary-dark);
            border-radius: var(--border-radius);
            transition: var(--transition);
        }

        .switch-to-text:hover {
            background-color: var(--primary-color);
            color: var(--text-light);
        }

        @keyframes pulse {
            0% {
                box-shadow: 0 0 0 0 rgba(220, 53, 69, 0.7);
            }
            70% {
                box-shadow: 0 0 0 10px rgba(220, 53, 69, 0);
            }
            100% {
                box-shadow: 0 0 0 0 rgba(220, 53, 69, 0);
            }
        }
    </style>
</head>
<body class="voice-only-mode">
    <div class="app-container">
        <header>
            <div class="logo">
                <span class="company-name">Super Company</span>
            </div>
            <div class="header-controls">
                <button id="switchModeBtn" class="mode-switch" title="Switch to multimodal mode">
                    <i class="fas fa-desktop"></i>
                </button>
            </div>
        </header>
        
        <main>
            <div class="phone-interface">
                <div class="phone-display centered">
                    <div class="display-header">
                        <span class="mode-indicator">Voice Mode</span>
                        <span class="status">
                            <i class="fas fa-signal"></i>
                            <i class="fas fa-battery-three-quarters"></i>
                        </span>
                    </div>
                    
                    <div class="voice-interaction">
                        <div class="voice-status" id="voiceStatus">
                            <div class="voice-animation">
                                <div class="voice-wave"></div>
                                <div class="voice-wave"></div>
                                <div class="voice-wave"></div>
                                <div class="voice-wave"></div>
                                <div class="voice-wave"></div>
                            </div>
                            <p class="status-text">Waiting for voice input...</p>
                        </div>
                        
                        <div class="voice-controls">
                            <button id="voiceInputBtn" class="large-mic-btn" title="Speak">
                                <i class="fas fa-microphone"></i>
                            </button>
                            <p>Press and speak</p>
                        </div>
                        
                        <div class="voice-transcript">
                            <h3>Last heard:</h3>
                            <p id="lastTranscript">-</p>
                        </div>
                    </div>
                    
                    <div class="dtmf-keypad">
                        <div class="keypad-row">
                            <button class="dtmf-key" data-key="1">1</button>
                            <button class="dtmf-key" data-key="2">2 <span>ABC</span></button>
                            <button class="dtmf-key" data-key="3">3 <span>DEF</span></button>
                        </div>
                        <div class="keypad-row">
                            <button class="dtmf-key" data-key="4">4 <span>GHI</span></button>
                            <button class="dtmf-key" data-key="5">5 <span>JKL</span></button>
                            <button class="dtmf-key" data-key="6">6 <span>MNO</span></button>
                        </div>
                        <div class="keypad-row">
                            <button class="dtmf-key" data-key="7">7 <span>PQRS</span></button>
                            <button class="dtmf-key" data-key="8">8 <span>TUV</span></button>
                            <button class="dtmf-key" data-key="9">9 <span>WXYZ</span></button>
                        </div>
                        <div class="keypad-row">
                            <button class="dtmf-key" data-key="*">*</button>
                            <button class="dtmf-key" data-key="0">0</button>
                            <button class="dtmf-key" data-key="#">#</button>
                        </div>
                    </div>
                </div>
                
                <div class="call-controls">
                    <button id="endCallBtn" class="end-call">
                        <i class="fas fa-phone-slash"></i>
                        <span>End Call</span>
                    </button>
                    <button id="switchToTextBtn" class="switch-to-text">
                        <i class="fas fa-keyboard"></i>
                        <span>Use Text</span>
                    </button>
                </div>
            </div>
        </main>
        
        <footer>
            <p>&copy; 2025 Super Company. All rights reserved.</p>
        </footer>
    </div>
    
    <!-- Audio element for playing responses -->
    <audio id="responseAudio" style="display: none;"></audio>
    
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            // DOM Elements
            const voiceInputBtn = document.getElementById('voiceInputBtn');
            const endCallBtn = document.getElementById('endCallBtn');
            const switchToTextBtn = document.getElementById('switchToTextBtn');
            const voiceStatus = document.getElementById('voiceStatus');
            const lastTranscript = document.getElementById('lastTranscript');
            const responseAudio = document.getElementById('responseAudio');
            const dtmfKeys = document.querySelectorAll('.dtmf-key');
            const switchModeBtn = document.getElementById('switchModeBtn');
            
            // State variables
            let sessionId = null;
            let isRecording = false;
            let mediaRecorder = null;
            let audioChunks = [];
            let socket = null;
            
            // Initialize WebSocket connection
            function initializeSocket() {
                socket = io();
                
                socket.on('connect', function() {
                    console.log('Connected to server');
                    updateVoiceStatus('Connected. Waiting for voice input...');
                    
                    // Start IVR session when connected
                    startIVRSession();
                });
                
                socket.on('disconnect', function() {
                    console.log('Disconnected from server');
                    updateVoiceStatus('Disconnected. Please refresh the page.');
                });
                
                socket.on('ivr_response', handleIVRResponse);
                
                socket.on('error', function(data) {
                    console.error('Error:', data.message);
                    updateVoiceStatus('Error: ' + data.message);
                });
            }
            
            // Start a new IVR session
            function startIVRSession() {
                sessionId = getCookie('session_id') || generateUUID();
                setCookie('session_id', sessionId, 1); // Store for 1 day
                
                console.log('Starting IVR session:', sessionId);
                socket.emit('start_session', { session_id: sessionId });
            }
            
            // Handle IVR response from server
            function handleIVRResponse(data) {
                console.log('Received IVR response:', data);
                
                // Play audio response if available
                if (data.audio) {
                    playAudioResponse(data.audio);
                }
                
                // Update status with text response
                if (data.text) {
                    updateVoiceStatus(data.text);
                }
                
                // Handle redirect if specified
                if (data.redirect) {
                    setTimeout(() => {
                        window.location.href = data.redirect;
                    }, 1000);
                }
            }
            
            // Update voice status display
            function updateVoiceStatus(text) {
                const statusText = voiceStatus.querySelector('.status-text');
                statusText.textContent = text;
            }
            
            // Update last transcription display
            function updateLastTranscript(text) {
                lastTranscript.textContent = text || '-';
            }
            
            // Play audio response
            function playAudioResponse(audioBase64) {
                try {
                    const audioSrc = `data:audio/wav;base64,${audioBase64}`;
                    responseAudio.src = audioSrc;
                    
                    responseAudio.oncanplaythrough = function() {
                        responseAudio.play().catch(error => {
                            console.error('Error playing audio:', error);
                        });
                    };
                    
                    responseAudio.onerror = function() {
                        console.error('Error loading audio');
                    };
                } catch (error) {
                    console.error('Error setting up audio:', error);
                }
            }
            
            // Handle DTMF key press
            function handleDTMFKeyPress(key) {
                console.log('DTMF key pressed:', key);
                
                // Play DTMF tone
                playDTMFTone(key);
                
                // Send to server
                socket.emit('dtmf_input', {
                    session_id: sessionId,
                    key: key
                });
            }
            
            // Play DTMF tone
            function playDTMFTone(key) {
                // DTMF frequency mapping
                const frequencies = {
                    '1': [697, 1209],
                    '2': [697, 1336],
                    '3': [697, 1477],
                    '4': [770, 1209],
                    '5': [770, 1336],
                    '6': [770, 1477],
                    '7': [852, 1209],
                    '8': [852, 1336],
                    '9': [852, 1477],
                    '0': [941, 1336],
                    '*': [941, 1209],
                    '#': [941, 1477]
                };
                
                // Check if Web Audio API is available
                if (!window.AudioContext && !window.webkitAudioContext) {
                    console.warn('Web Audio API not supported');
                    return;
                }
                
                const AudioContext = window.AudioContext || window.webkitAudioContext;
                const context = new AudioContext();
                
                // Get frequencies for the key
                const freq = frequencies[key];
                if (!freq) return;
                
                // Create oscillators
                const osc1 = context.createOscillator();
                const osc2 = context.createOscillator();
                const gainNode = context.createGain();
                
                // Set frequencies
                osc1.frequency.value = freq[0];
                osc2.frequency.value = freq[1];
                
                // Connect nodes
                osc1.connect(gainNode);
                osc2.connect(gainNode);
                gainNode.connect(context.destination);
                
                // Set volume
                gainNode.gain.value = 0.1;
                
                // Play tone for 100ms
                osc1.start(0);
                osc2.start(0);
                
                setTimeout(() => {
                    osc1.stop();
                    osc2.stop();
                    context.close();
                }, 100);
            }
            
            // Handle voice input
            function toggleVoiceInput() {
                if (isRecording) {
                    stopRecording();
                } else {
                    startRecording();
                }
            }
            
            // Start recording audio
            async function startRecording() {
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                    
                    mediaRecorder = new MediaRecorder(stream);
                    audioChunks = [];
                    
                    mediaRecorder.ondataavailable = event => {
                        audioChunks.push(event.data);
                    };
                    
                    mediaRecorder.onstop = async () => {
                        const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                        await sendAudioToServer(audioBlob);
                        
                        // Release microphone
                        stream.getTracks().forEach(track => track.stop());
                    };
                    
                    // Start recording
                    mediaRecorder.start();
                    isRecording = true;
                    
                    // Update UI
                    voiceInputBtn.classList.add('active');
                    voiceInputBtn.innerHTML = '<i class="fas fa-stop"></i>';
                    voiceStatus.classList.add('listening');
                    updateVoiceStatus('Listening...');
                    
                    console.log('Recording started');
                    
                    // Auto-stop after 10 seconds to prevent very long recordings
                    setTimeout(() => {
                        if (isRecording) {
                            stopRecording();
                        }
                    }, 10000);
                } catch (error) {
                    console.error('Error accessing microphone:', error);
                    alert('Could not access the microphone. Please ensure you have granted permission.');
                }
            }
            
            // Stop recording audio
            function stopRecording() {
                if (mediaRecorder && isRecording) {
                    mediaRecorder.stop();
                    isRecording = false;
                    
                    // Update UI
                    voiceInputBtn.classList.remove('active');
                    voiceInputBtn.innerHTML = '<i class="fas fa-microphone"></i>';
                    voiceStatus.classList.remove('listening');
                    updateVoiceStatus('Processing your voice input...');
                    
                    console.log('Recording stopped');
                }
            }
            
            // Send recorded audio to server
            async function sendAudioToServer(audioBlob) {
                try {
                    // Convert Blob to base64
                    const reader = new FileReader();
                    reader.readAsDataURL(audioBlob);
                    
                    reader.onloadend = function() {
                        const base64Audio = reader.result;
                        
                        // Send to server
                        socket.emit('voice_input', {
                            session_id: sessionId,
                            audio: base64Audio
                        });
                    };
                } catch (error) {
                    console.error('Error sending audio to server:', error);
                    updateVoiceStatus('Error sending audio. Please try again.');
                }
            }
            
            // Handle end call
            function endCall() {
                // Add confirmation dialog
                if (confirm('Are you sure you want to end the call?')) {
                    window.location.href = '/';
                }
            }
            
            // Switch to text mode
            function switchToText() {
                window.location.href = '/';
            }
            
            // Event listeners
            voiceInputBtn.addEventListener('click', toggleVoiceInput);
            endCallBtn.addEventListener('click', endCall);
            switchToTextBtn.addEventListener('click', switchToText);
            switchModeBtn.addEventListener('click', switchToText);
            
            // Add event listeners to DTMF keys
            dtmfKeys.forEach(key => {
                key.addEventListener('click', function() {
                    const keyValue = this.dataset.key;
                    handleDTMFKeyPress(keyValue);
                });
            });
            
            // Keyboard shortcuts for DTMF
            document.addEventListener('keydown', function(event) {
                const key = event.key;
                if (/^[0-9*#]$/.test(key)) {
                    // Find and visually activate the corresponding button
                    const dtmfButton = document.querySelector(`.dtmf-key[data-key="${key}"]`);
                    if (dtmfButton) {
                        dtmfButton.classList.add('active');
                        setTimeout(() => dtmfButton.classList.remove('active'), 200);
                        handleDTMFKeyPress(key);
                    }
                } else if (key === ' ' || key === 'Enter') {
                    // Space or Enter to toggle recording
                    toggleVoiceInput();
                    event.preventDefault();
                }
            });
            
            // Initialize the app
            initializeSocket();
            
            // Utility functions
            function generateUUID() {
                return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
                    const r = Math.random() * 16 | 0;
                    const v = c === 'x' ? r : (r & 0x3 | 0x8);
                    return v.toString(16);
                });
            }
            
            function setCookie(name, value, days) {
                const expires = new Date();
                expires.setTime(expires.getTime() + days * 24 * 60 * 60 * 1000);
                document.cookie = `${name}=${value};expires=${expires.toUTCString()};path=/`;
            }
            
            function getCookie(name) {
                const nameEQ = `${name}=`;
                const ca = document.cookie.split(';');
                for (let i = 0; i < ca.length; i++) {
                    let c = ca[i];
                    while (c.charAt(0) === ' ') c = c.substring(1, c.length);
                    if (c.indexOf(nameEQ) === 0) return c.substring(nameEQ.length, c.length);
                }
                return null;
            }
        });
    </script>
</body>
</html>
"""


# ----- Main Entry Point -----

if __name__ == '__main__':
    print("Starting Multimodal IVR System...")
    print(f"Speech Recognition: {'Enabled (Faster-Whisper)' if WhisperModel else 'Disabled (install faster-whisper)'}")
    
    # Check TTS service in a way that handles connection errors
    try:
        is_octave_available = requests.get(OCTAVE_TTS_API_URL, timeout=1).status_code == 200
        print(f"TTS: {'Enabled (Octave TTS)' if is_octave_available else 'Falling back to gTTS'}")
    except:
        print("TTS: Falling back to gTTS (Octave TTS not available)")
    
    # Check Ollama service in a way that handles connection errors
    try:
        is_ollama_available = requests.get(f"{OLLAMA_API_URL}/health", timeout=1).status_code == 200
        print(f"LLM: {'Enabled (Ollama)' if is_ollama_available else 'Using rule-based responses (Ollama not available)'}")
    except:
        print("LLM: Using rule-based responses (Ollama not available)")
    
    print("Open http://localhost:5000 in your browser")
    
    # Run the application with WebSocket support
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)