import streamlit as st
import time
import os
import json
from datetime import datetime
import re
import random
import uuid
import requests
import traceback
import threading
import tempfile
import queue
import numpy as np
import base64
from typing import Dict, List, Tuple, Optional, Any, Union

# Dependency imports with proper error handling
try:
    import ollama
    HAS_OLLAMA_PKG = True
except ImportError:
    HAS_OLLAMA_PKG = False

try:
    import pyttsx3
    HAS_TTS = True
except ImportError:
    HAS_TTS = False

try:
    from faster_whisper import WhisperModel
    import sounddevice as sd
    import soundfile as sf
    HAS_FASTER_WHISPER = True
except ImportError:
    HAS_FASTER_WHISPER = False


# ===== Constants and Config ===== #
DEFAULT_MODEL = "deepseek-r1:latest"
OLLAMA_API_URL = "http://localhost:11434/api/generate"
TAX_RATE = 0.08  # 8% tax
SAMPLE_RATE = 16000  # Sample rate for audio recording

# Entity extraction patterns
PATTERNS = {
    'phone': r'\b\d{10}\b',  # 10-digit phone number
    'zip_code': r'\b\d{5}\b',  # 5-digit zip code
    'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'  # Email pattern
}

# Database file paths
ORDERS_DB_FILE = 'orders_database.json'
USERS_DB_FILE = 'users_database.json'


# ===== TTS Engine Singleton ===== #
class TTSEngine:
    """Singleton class to manage TTS functionality"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TTSEngine, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize the TTS engine"""
        self.engine = None
        if HAS_TTS:
            try:
                self.engine = pyttsx3.init()
                self.engine.setProperty('rate', 150)
                self.engine.setProperty('volume', 0.9)
                print("TTS engine initialized successfully")
            except Exception as e:
                print(f"Error initializing TTS: {e}")
                self.engine = None
    
    def speak(self, text):
        """Speak the given text"""
        if not self.engine:
            print("TTS engine not available")
            return False
        
        try:
            self.engine.say(text)
            self.engine.runAndWait()
            return True
        except Exception as e:
            print(f"Error with TTS: {e}")
            return False


# ===== Menu Data ===== #
class MenuData:
    """Singleton class to manage menu data"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MenuData, cls).__new__(cls)
            cls._instance._load_menu()
        return cls._instance
    
    def _load_menu(self):
        """Load the menu data - could be extended to load from file/database"""
        self.menu = {
            'pizza': {
                'margherita': {'price': 10.99, 'description': 'Classic cheese and tomato pizza'},
                'pepperoni': {'price': 12.99, 'description': 'Pizza with pepperoni toppings'},
                'vegetarian': {'price': 11.99, 'description': 'Pizza loaded with fresh vegetables'},
                'hawaiian': {'price': 13.99, 'description': 'Pizza with ham and pineapple'},
                'supreme': {'price': 14.99, 'description': 'Pizza with multiple toppings including pepperoni, sausage, vegetables'}
            },
            'burger': {
                'classic burger': {'price': 8.99, 'description': 'Simple beef patty with lettuce and tomato'},
                'cheeseburger': {'price': 9.99, 'description': 'Beef patty with cheese, lettuce and tomato'},
                'veggie burger': {'price': 8.99, 'description': 'Plant-based patty with lettuce and tomato'},
                'double bacon burger': {'price': 12.99, 'description': 'Two beef patties with bacon, cheese, lettuce and tomato'},
                'chicken burger': {'price': 10.99, 'description': 'Chicken patty with lettuce and mayo'}
            },
            'sides': {
                'french fries': {'price': 3.99, 'description': 'Crispy fried potatoes'},
                'onion rings': {'price': 4.99, 'description': 'Battered and fried onion rings'},
                'mozzarella sticks': {'price': 5.99, 'description': 'Breaded and fried mozzarella cheese'},
                'garlic bread': {'price': 3.49, 'description': 'Bread with garlic butter'},
                'salad': {'price': 4.49, 'description': 'Fresh garden salad'}
            },
            'drinks': {
                'soda': {'price': 1.99, 'description': 'Carbonated soft drink'},
                'bottled water': {'price': 1.49, 'description': 'Still mineral water'},
                'iced tea': {'price': 2.49, 'description': 'Cold tea with ice'},
                'milkshake': {'price': 4.99, 'description': 'Thick milk-based drink'},
                'coffee': {'price': 2.29, 'description': 'Hot brewed coffee'}
            }
        }
    
    def get_menu(self):
        """Return the complete menu"""
        return self.menu
    
    def get_item_details(self, category: str, item: str) -> Optional[Dict]:
        """Get details for a specific menu item"""
        if category in self.menu and item in self.menu[category]:
            return self.menu[category][item]
        return None
    
    def get_categories(self) -> List[str]:
        """Get all menu categories"""
        return list(self.menu.keys())
    
    def get_items_in_category(self, category: str) -> Dict:
        """Get all items in a specific category"""
        return self.menu.get(category, {})


# ===== Database Handler ===== #
class DatabaseHandler:
    """Class to handle database operations"""
    
    def __init__(self):
        self.orders_db_file = ORDERS_DB_FILE
        self.users_db_file = USERS_DB_FILE
        self.orders_db = self._load_or_create_db(self.orders_db_file, [])
        self.users_db = self._load_or_create_db(self.users_db_file, {})
    
    def _load_or_create_db(self, file_path: str, default_value: Any) -> Any:
        """Load a database file or create it if it doesn't exist"""
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading database {file_path}: {e}")
                return default_value
        else:
            with open(file_path, 'w') as f:
                json.dump(default_value, f)
            return default_value
    
    def save_orders(self):
        """Save the orders database"""
        try:
            with open(self.orders_db_file, 'w') as f:
                json.dump(self.orders_db, f)
            return True
        except IOError as e:
            print(f"Error saving orders database: {e}")
            return False
    
    def save_users(self):
        """Save the users database"""
        try:
            with open(self.users_db_file, 'w') as f:
                json.dump(self.users_db, f)
            return True
        except IOError as e:
            print(f"Error saving users database: {e}")
            return False
    
    def add_order(self, order: Dict) -> bool:
        """Add a new order to the database"""
        self.orders_db.append(order)
        return self.save_orders()
    
    def get_order_by_id(self, order_id: str) -> Optional[Dict]:
        """Find an order by ID"""
        for order in self.orders_db:
            db_order_id = order['order_id'].replace("-", "").upper()
            if db_order_id in order_id.replace("-", "").upper() or order_id.replace("-", "").upper() in db_order_id:
                return order
        return None
    
    def get_user(self, phone: str) -> Optional[Dict]:
        """Get a user by phone number"""
        return self.users_db.get(phone)
    
    def add_or_update_user(self, phone: str, user_data: Dict) -> bool:
        """Add or update a user in the database"""
        self.users_db[phone] = user_data
        return self.save_users()
    
    def add_order_to_user_history(self, phone: str, order_id: str) -> bool:
        """Add an order ID to a user's order history"""
        if phone not in self.users_db:
            return False
        
        if "order_history" not in self.users_db[phone]:
            self.users_db[phone]["order_history"] = []
        
        self.users_db[phone]["order_history"].append(order_id)
        return self.save_users()


# ===== LLM Service ===== #
class LLMService:
    """Service to handle LLM queries"""
    
    def __init__(self, model: str = DEFAULT_MODEL, api_url: str = OLLAMA_API_URL):
        self.model = model
        self.api_url = api_url
        self.use_ollama_pkg = HAS_OLLAMA_PKG
    
    def query(self, prompt: str, system_prompt: str = "You are a helpful assistant") -> Optional[str]:
        """Query the LLM using the best available method"""
        try:
            if self.use_ollama_pkg:
                return self._query_with_package(prompt, system_prompt)
            return self._query_with_api(prompt, system_prompt)
        except Exception as e:
            print(f"Error querying LLM: {e}")
            traceback.print_exc()
            return None
    
    def _query_with_package(self, prompt: str, system_prompt: str) -> Optional[str]:
        """Query using the Ollama package"""
        try:
            response = ollama.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                options={"temperature": 0.3}
            )
            
            if response and "message" in response and "content" in response["message"]:
                return response["message"]["content"]
            
            print("Invalid response format from Ollama package")
            self.use_ollama_pkg = False  # Fall back to API calls
            return self._query_with_api(prompt, system_prompt)
        except Exception as e:
            print(f"Exception with Ollama package: {e}")
            self.use_ollama_pkg = False  # Fall back to API calls
            return self._query_with_api(prompt, system_prompt)
    
    def _query_with_api(self, prompt: str, system_prompt: str) -> Optional[str]:
        """Query using direct API calls"""
        try:
            data = {
                "model": self.model,
                "prompt": prompt,
                "system": system_prompt,
                "stream": False,
                "temperature": 0.3
            }
            
            response = requests.post(self.api_url, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                return result.get('response', '')
            
            print(f"Error from Ollama API: {response.status_code}")
            print(response.text)
            return None
        except requests.RequestException as e:
            print(f"Request exception when calling Ollama API: {e}")
            return None


# ===== Speech Services ===== #
class SpeechServices:
    """Class to handle speech recognition"""
    
    def __init__(self):
        # Initialize speech recognition
        self.whisper_model = None
        self.sample_rate = SAMPLE_RATE
        if HAS_FASTER_WHISPER:
            try:
                print("Initializing Faster Whisper model...")
                self.whisper_model = WhisperModel("tiny", device="cpu", compute_type="int8")
                print("Faster Whisper initialized successfully")
            except Exception as e:
                print(f"Error initializing Faster Whisper: {e}")
    
    def stream_audio(self, audio_queue: queue.Queue, stop_event: threading.Event):
        """Stream audio from microphone to a queue"""
        if not HAS_FASTER_WHISPER:
            return
        
        def callback(indata, frames, time, status):
            if status:
                print(f"Stream callback status: {status}")
            audio_queue.put(indata.copy())
        
        try:
            with sd.InputStream(samplerate=self.sample_rate, channels=1, callback=callback):
                while not stop_event.is_set():
                    time.sleep(0.1)
        except Exception as e:
            print(f"Error streaming audio: {e}")
    
    def transcribe_audio(self, audio_data: np.ndarray) -> Optional[str]:
        """Transcribe audio data using Faster Whisper"""
        if not self.whisper_model:
            return None
        
        try:
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                sf.write(temp_file.name, audio_data, self.sample_rate)
                segments, info = self.whisper_model.transcribe(temp_file.name, beam_size=1)
                text = " ".join([segment.text for segment in segments])
                os.unlink(temp_file.name)
                return text.strip()
        except Exception as e:
            print(f"Error transcribing audio: {e}")
            return None


# ===== Food Ordering System ===== #
class FoodOrderingSystem:
    """Main class for the food ordering system"""
    
    def __init__(self):
        self.db_handler = DatabaseHandler()
        self.llm_service = LLMService()
        self.speech_services = SpeechServices()
        self.menu_data = MenuData()
    
    def extract_entities(self, text: str, entity_type: str) -> Optional[str]:
        """Extract entities like phone numbers, email addresses, etc. from text"""
        if entity_type in PATTERNS:
            pattern = PATTERNS[entity_type]
            matches = re.findall(pattern, text)
            return matches[0] if matches else None
        return None
    
    def detect_intent(self, text: str) -> str:
        """Use a language model to determine user intent"""
        system_prompt = """
        You are a food ordering assistant. Analyze the user's input and identify their intent.
        Return ONLY ONE of the following intents: order, info, modify, checkout, help, exit, or none.
        Do not include any explanations or additional text.
        """
        
        prompt = f"User input: '{text}'\nWhat is the user's intent?"
        response = self.llm_service.query(prompt, system_prompt)
        
        if response:
            response = response.strip().lower()
            intents = ['order', 'info', 'modify', 'checkout', 'help', 'exit']
            for intent in intents:
                if intent in response:
                    return intent
        
        return "none"
    
    def extract_items(self, text: str) -> List[Dict]:
        """Use a language model to extract food items and quantities from text"""
        menu_str = json.dumps(self.menu_data.get_menu())
        
        system_prompt = f"""
        You are a food ordering assistant. Your job is to extract food items and their quantities from the user's input.
        The restaurant's menu is: {menu_str}
        
        Return your analysis as JSON in this format:
        {{
            "items": [
                {{
                    "category": "category_name",
                    "name": "item_name",
                    "price": price_value,
                    "quantity": quantity_value
                }}
            ]
        }}
        
        Only include items that are clearly mentioned and in the menu. Include the category, exact item name as in the menu, price from the menu, and detected quantity (default to 1 if not specified).
        Return ONLY the JSON with no additional text.
        """
        
        prompt = f"User order: '{text}'"
        response = self.llm_service.query(prompt, system_prompt)
        
        if response:
            try:
                # Extract JSON from the response
                json_str = response
                if "```json" in response:
                    json_str = response.split("```json")[1].split("```")[0].strip()
                elif "```" in response:
                    json_str = response.split("```")[1].strip()
                
                result = json.loads(json_str)
                return result.get("items", [])
            except (json.JSONDecodeError, Exception) as e:
                print(f"Error extracting items: {e}")
                return []
        
        return []
    
    def generate_order_id(self) -> str:
        """Generate a unique order ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_digits = random.randint(1000, 9999)
        return f"ORD-{timestamp}-{random_digits}"
    
    def handle_menu_inquiry(self, message: str) -> Optional[str]:
        """Use language model to determine if the user is asking about the menu"""
        system_prompt = """
        You are a food ordering assistant. Determine if the user is asking about the menu.
        If they are asking about a specific category or menu item, identify which one.
        Return your response in JSON format:
        {
            "is_menu_inquiry": true/false,
            "category": "category_name or null if not asking about a category",
            "item": "item_name or null if not asking about a specific item"
        }
        Return ONLY the JSON with no additional text.
        """
        
        prompt = f"User input: '{message}'"
        llm_response = self.llm_service.query(prompt, system_prompt)
        
        if not llm_response:
            return None
        
        try:
            # Clean up response if needed
            json_str = llm_response
            if "```json" in llm_response:
                json_str = llm_response.split("```json")[1].split("```")[0].strip()
            elif "```" in llm_response:
                json_str = llm_response.split("```")[1].strip()
            
            result = json.loads(json_str)
            
            if not result.get("is_menu_inquiry"):
                return None
            
            # Handle the menu inquiry
            category = result.get("category")
            item = result.get("item")
            
            if category and category in self.menu_data.get_menu():
                menu_info = f"Here are our {category} options:\n"
                for item_name, details in self.menu_data.get_items_in_category(category).items():
                    menu_info += f"• {item_name.title()}: {details['description']} - ${details['price']:.2f}\n"
                return menu_info
            elif item:
                # Look for the item in all categories
                for category in self.menu_data.get_categories():
                    items = self.menu_data.get_items_in_category(category)
                    if item in items:
                        details = items[item]
                        return f"{item.title()}: {details['description']} - ${details['price']:.2f}"
            else:
                # General menu inquiry
                menu_info = "We offer the following categories:\n"
                for category in self.menu_data.get_categories():
                    menu_info += f"• {category.title()}\n"
                menu_info += "\nWhat would you like to know more about?"
                return menu_info
        except (json.JSONDecodeError, Exception) as e:
            print(f"Error handling menu inquiry: {e}")
        
        return None
    
    def calculate_total(self, cart: List[Dict]) -> float:
        """Calculate the total cost of items in the cart"""
        return sum(item['price'] * item['quantity'] for item in cart)
    
    def process_message(self, message: str, state: Dict) -> Tuple[str, Dict]:
        """Process a user message based on the current state"""
        user_id = state.get("user_id")
        current_state = state.get("current_state", "welcome")
        cart = state.get("cart", [])
        customer_info = state.get("customer_info", {})
        
        # Check for menu inquiries regardless of state
        menu_info = self.handle_menu_inquiry(message)
        if menu_info:
            return menu_info, state
        
        # Process based on current state
        if current_state == "welcome":
            return self._handle_welcome_state(message, state)
        elif current_state == "customer_identification":
            return self._handle_customer_identification(message, state)
        elif current_state == "get_customer_name":
            return self._handle_get_customer_name(message, state)
        elif current_state == "get_customer_phone":
            return self._handle_get_customer_phone(message, state)
        elif current_state == "get_customer_address":
            return self._handle_get_customer_address(message, state)
        elif current_state == "get_customer_zipcode":
            return self._handle_get_customer_zipcode(message, state)
        elif current_state == "order_food":
            return self._handle_order_food(message, state)
        elif current_state == "review_order":
            return self._handle_review_order(message, state)
        elif current_state == "modify_order":
            return self._handle_modify_order(message, state)
        elif current_state == "confirm_address":
            return self._handle_confirm_address(message, state)
        elif current_state == "update_address":
            return self._handle_update_address(message, state)
        elif current_state == "update_zipcode":
            return self._handle_update_zipcode(message, state)
        elif current_state == "select_payment":
            return self._handle_select_payment(message, state)
        elif current_state == "order_completed":
            return self._handle_order_completed(message, state)
        elif current_state == "check_order":
            return self._handle_check_order(message, state)
        elif current_state == "get_order_id":
            return self._handle_get_order_id(message, state)
        elif current_state == "show_order_details":
            return self._handle_show_order_details(message, state)
        elif current_state == "get_order_phone":
            return self._handle_get_order_phone(message, state)
        elif current_state == "show_phone_orders":
            return self._handle_show_phone_orders(message, state)
        elif current_state == "order_not_found":
            return self._handle_order_not_found(message, state)
        
        # Default fallback
        return "I'm not sure what you want to do. You can say 'order food', 'check my order', or ask for 'help'.", state
    
    # State handler methods
    def _handle_welcome_state(self, message: str, state: Dict) -> Tuple[str, Dict]:
        intent = self.detect_intent(message)
        
        if intent == 'order' or 'order' in message or 'food' in message:
            state["current_state"] = "customer_identification"
            return "Would you like to order as a new customer or are you a returning customer?", state
        elif 'check' in message or 'status' in message or 'existing' in message:
            state["current_state"] = "check_order"
            return "Do you know your order ID?", state
        elif intent == 'help' or 'help' in message:
            help_text = "Here's how you can use our system:\n\n"
            help_text += "• You can order food by saying something like 'I'd like to order a pepperoni pizza and a soda.'\n"
            help_text += "• You can ask about our menu by saying 'What pizzas do you have?' or 'Tell me about your burgers.'\n"
            help_text += "• When you're done ordering, say 'checkout' or 'I'm done' to complete your order.\n\n"
            help_text += "What would you like to do?"
            return help_text, state
        else:
            state["current_state"] = "customer_identification"
            return "I'll help you order some food. Are you a new customer or have you ordered with us before?", state
    
    def _handle_customer_identification(self, message: str, state: Dict) -> Tuple[str, Dict]:
        if 'new' in message.lower():
            state["current_state"] = "get_customer_name"
            return "Let's set you up as a new customer. What's your name?", state
        elif 'return' in message.lower() or 'before' in message.lower() or 'existing' in message.lower():
            state["current_state"] = "get_customer_phone"
            return "Welcome back! What's your phone number? (10 digits)", state
        else:
            state["current_state"] = "get_customer_name"
            return "I'll register you as a new customer. What's your name?", state
    
    def _handle_get_customer_name(self, message: str, state: Dict) -> Tuple[str, Dict]:
        customer_info = state.get("customer_info", {})
        customer_info["name"] = message
        state["customer_info"] = customer_info
        state["current_state"] = "get_customer_phone"
        return f"Nice to meet you, {customer_info['name']}. What's your phone number? (10 digits)", state
    
    def _handle_get_customer_phone(self, message: str, state: Dict) -> Tuple[str, Dict]:
        phone = self.extract_entities(message, 'phone')
        
        if not phone:
            return "I need a valid 10-digit phone number. Please try again.", state
        
        customer_info = state.get("customer_info", {})
        customer_info["phone"] = phone
        state["customer_info"] = customer_info
        
        # Check if returning customer
        existing_user = self.db_handler.get_user(phone)
        if existing_user:
            state["customer_info"] = existing_user
            state["current_state"] = "order_food"
            return f"Welcome back, {existing_user['name']}! What would you like to order today?", state
        else:
            state["current_state"] = "get_customer_address"
            return "What's your delivery address?", state
    
    def _handle_get_customer_address(self, message: str, state: Dict) -> Tuple[str, Dict]:
        customer_info = state.get("customer_info", {})
        customer_info["address"] = message
        state["customer_info"] = customer_info
        state["current_state"] = "get_customer_zipcode"
        return "What's your zip code? (5 digits)", state
    
    def _handle_get_customer_zipcode(self, message: str, state: Dict) -> Tuple[str, Dict]:
        zip_code = self.extract_entities(message, 'zip_code')
        
        if not zip_code:
            return "I need a valid 5-digit zip code. Please try again.", state
        
        customer_info = state.get("customer_info", {})
        customer_info["zip_code"] = zip_code
        if "order_history" not in customer_info:
            customer_info["order_history"] = []
        
        state["customer_info"] = customer_info
        
        # Save customer to database
        self.db_handler.add_or_update_user(customer_info["phone"], customer_info)
        
        state["current_state"] = "order_food"
        return f"Thanks, {customer_info['name']}! Your information has been saved. What would you like to order?", state
    
    def _handle_order_food(self, message: str, state: Dict) -> Tuple[str, Dict]:
        cart = state.get("cart", [])
        
        # Check intent
        intent = self.detect_intent(message)
        
        if intent == 'checkout':
            if not cart:
                return "Your cart is empty. Please add some items before checking out.", state
            else:
                state["current_state"] = "review_order"
                response = "Here's your current order:\n"
                for idx, item in enumerate(cart, 1):
                    response += f"{idx}. {item['name']} - ${item['price']:.2f} x {item['quantity']} = ${item['price'] * item['quantity']:.2f}\n"
                
                total = self.calculate_total(cart)
                response += f"\nTotal: ${total:.2f}\n\n"
                response += "Would you like to modify your order, proceed to checkout, or cancel?"
                return response, state
        
        # Extract items from the message
        items = self.extract_items(message)
        
        if not items:
            return "I didn't catch any menu items in your order. Here's what we have:\n\n" + \
                   "• Pizzas: Margherita, Pepperoni, Vegetarian, Hawaiian, Supreme\n" + \
                   "• Burgers: Classic Burger, Cheeseburger, Veggie Burger, Double Bacon Burger, Chicken Burger\n" + \
                   "• Sides: French Fries, Onion Rings, Mozzarella Sticks, Garlic Bread, Salad\n" + \
                   "• Drinks: Soda, Bottled Water, Iced Tea, Milkshake, Coffee\n\n" + \
                   "What would you like to order?", state
        
        # Add items to cart
        for item in items:
            cart.append(item)
        
        state["cart"] = cart
        
        response = ""
        for item in items:
            response += f"Added {item['quantity']} {item['name']}(s) to your cart.\n"
        
        response += "\nWould you like to order anything else?"
        return response, state
    
    def _handle_review_order(self, message: str, state: Dict) -> Tuple[str, Dict]:
        cart = state.get("cart", [])
        
        # Use language model to determine the customer's intention
        system_prompt = """
        You are a food ordering assistant. Determine what the user wants to do with their order.
        Return ONLY ONE of the following actions: "modify", "checkout", "cancel", or "unclear".
        Do not include any explanations or additional text.
        """
        
        prompt = f"User response: '{message}'. What does the user want to do with their order?"
        action = self.llm_service.query(prompt, system_prompt)
        
        if action:
            action = action.strip().lower()
            
            if 'modify' in action:
                state["current_state"] = "modify_order"
                return "What would you like to change? You can say 'remove' followed by an item, or add new items.", state
            
            elif 'checkout' in action:
                return self._prepare_checkout(state)
            
            elif 'cancel' in action:
                state["cart"] = []
                state["current_state"] = "welcome"
                return "Order canceled. Your cart has been cleared. What would you like to do?", state
        
        # Default to checkout if unclear
        return self._prepare_checkout(state)
    
    def _prepare_checkout(self, state: Dict) -> Tuple[str, Dict]:
        """Prepare the checkout process"""
        cart = state.get("cart", [])
        customer_info = state.get("customer_info", {})
        
        total = self.calculate_total(cart)
        tax = total * TAX_RATE
        final_total = total + tax
        
        state["current_state"] = "confirm_address"
        state["subtotal"] = total
        state["tax"] = tax
        state["final_total"] = final_total
        
        response = f"Your subtotal is ${total:.2f}\n"
        response += f"Tax is ${tax:.2f}\n"
        response += f"Final total is ${final_total:.2f}\n\n"
        response += f"Your order will be delivered to:\n{customer_info.get('address', '')}, {customer_info.get('zip_code', '')}\n\n"
        response += "Is this address correct?"
        
        return response, state
    
    def _handle_modify_order(self, message: str, state: Dict) -> Tuple[str, Dict]:
        cart = state.get("cart", [])
        
        # Check if removing items
        remove_item = None
        if 'remove' in message.lower() or 'delete' in message.lower() or 'cancel' in message.lower():
            system_prompt = """
            You are a food ordering assistant. Determine which item the user wants to remove from their order.
            Return ONLY the name of the item they want to remove, with no additional text.
            """
            
            prompt = f"User wants to modify order: '{message}'. Which item do they want to remove?"
            remove_item = self.llm_service.query(prompt, system_prompt)
        
        # Process removal if applicable
        response = ""
        if remove_item:
            remove_item = remove_item.strip().lower()
            found = False
            
            # Find and remove the item
            for idx, item in enumerate(cart):
                if remove_item in item['name'].lower():
                    removed_item = cart.pop(idx)
                    found = True
                    break
            
            response = f"Removed {remove_item} from your cart.\n\n" if found else f"I couldn't find {remove_item} in your cart.\n\n"
        
        # Extract any new items
        new_items = self.extract_items(message)
        if new_items:
            for item in new_items:
                cart.append(item)
                response += f"Added {item['quantity']} {item['name']}(s) to your cart.\n"
        
        state["cart"] = cart
        
        # Show the updated cart and set next state
        if cart:
            response += "\nHere's your updated order:\n"
            for idx, item in enumerate(cart, 1):
                response += f"{idx}. {item['name']} - ${item['price']:.2f} x {item['quantity']} = ${item['price'] * item['quantity']:.2f}\n"
            
            total = self.calculate_total(cart)
            response += f"\nTotal: ${total:.2f}\n\n"
            response += "Would you like to make more changes, proceed to checkout, or cancel your order?"
            state["current_state"] = "review_order"
        else:
            response += "Your cart is now empty. Would you like to order something else?"
            state["current_state"] = "order_food"
        
        return response, state
    
    def _handle_confirm_address(self, message: str, state: Dict) -> Tuple[str, Dict]:
        if 'yes' in message.lower() or 'correct' in message.lower() or 'right' in message.lower():
            state["current_state"] = "select_payment"
            return "How would you like to pay? You can say 'credit card' or 'cash on delivery'.", state
        else:
            state["current_state"] = "update_address"
            return "Let's update your delivery address. What's the correct address?", state
    
    def _handle_update_address(self, message: str, state: Dict) -> Tuple[str, Dict]:
        customer_info = state.get("customer_info", {})
        customer_info["address"] = message
        state["customer_info"] = customer_info
        state["current_state"] = "update_zipcode"
        return "And what's the correct zip code? (5 digits)", state
    
    def _handle_update_zipcode(self, message: str, state: Dict) -> Tuple[str, Dict]:
        zip_code = self.extract_entities(message, 'zip_code')
        
        if not zip_code:
            return "I need a valid 5-digit zip code. Please try again.", state
        
        customer_info = state.get("customer_info", {})
        customer_info["zip_code"] = zip_code
        state["customer_info"] = customer_info
        
        # Update in database
        if "phone" in customer_info:
            self.db_handler.add_or_update_user(customer_info["phone"], customer_info)
        
        state["current_state"] = "select_payment"
        return "How would you like to pay? You can say 'credit card' or 'cash on delivery'.", state
    
    def _handle_select_payment(self, message: str, state: Dict) -> Tuple[str, Dict]:
        customer_info = state.get("customer_info", {})
        cart = state.get("cart", [])
        
        if 'credit' in message.lower() or 'card' in message.lower():
            payment_type = "Credit Card"
            payment_msg = "We'll process your payment when your order is delivered."
        else:
            payment_type = "Cash on Delivery"
            payment_msg = "You'll pay cash when your order is delivered."
        
        # Generate order ID
        order_id = self.generate_order_id()
        
        # Create and save order record
        order_record = {
            'order_id': order_id,
            'customer_info': customer_info,
            'items': cart,
            'subtotal': state.get("subtotal", 0),
            'tax': state.get("tax", 0),
            'total': state.get("final_total", 0),
            'payment_method': payment_type,
            'status': 'Confirmed',
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        self.db_handler.add_order(order_record)
        
        # Add to customer's order history if customer has a phone number
        if "phone" in customer_info:
            self.db_handler.add_order_to_user_history(customer_info["phone"], order_id)
        
        # Clear cart and reset state
        response = f"Thank you for your order! {payment_msg}\n\n"
        response += f"Your order ID is: {order_id}\n\n"
        response += "Your order has been confirmed and will be delivered in 30-45 minutes.\n\n"
        response += "Is there anything else I can help you with today?"
        
        state["cart"] = []
        state["current_state"] = "order_completed"
        
        return response, state
    
    def _handle_order_completed(self, message: str, state: Dict) -> Tuple[str, Dict]:
        if 'yes' in message.lower() or 'yeah' in message.lower():
            state["current_state"] = "welcome"
            return "What would you like to do?", state
        else:
            state["current_state"] = "welcome"
            return "Thank you for using our service. Have a great day! Let me know if you need anything else.", state
    
    def _handle_check_order(self, message: str, state: Dict) -> Tuple[str, Dict]:
        if 'yes' in message.lower() or 'yeah' in message.lower() or 'order' in message.lower():
            if 'id' in message.lower() and any(c.isdigit() for c in message):
                state["temp_order_id"] = message
                state["current_state"] = "show_order_details"
                return self.process_message(message, state)
            else:
                state["current_state"] = "get_order_id"
                return "Great! What's your order ID?", state
        else:
            state["current_state"] = "get_order_phone"
            return "No problem. I can look up your orders using your phone number. What's your phone number? (10 digits)", state
    
    def _handle_get_order_id(self, message: str, state: Dict) -> Tuple[str, Dict]:
        order_id = message.replace(" ", "").replace("-", "").upper()
        state["temp_order_id"] = order_id
        state["current_state"] = "show_order_details"
        return self.process_message(message, state)
    
    def _handle_show_order_details(self, message: str, state: Dict) -> Tuple[str, Dict]:
        order_id = state.get("temp_order_id", message.replace(" ", "").replace("-", "").upper())
        
        # Try to find the order
        order_details = self.db_handler.get_order_by_id(order_id)
        
        if order_details:
            response = f"I found your order {order_details['order_id']}.\n\n"
            response += f"Status: {order_details['status']}\n"
            response += f"Order Date: {order_details['timestamp']}\n\n"
            response += "Items ordered:\n"
            
            for item in order_details['items']:
                response += f"• {item['quantity']} {item['name']}(s) - ${item['price'] * item['quantity']:.2f}\n"
            
            response += f"\nTotal: ${order_details['total']:.2f}\n\n"
            response += "Is there anything else I can help you with?"
            state["current_state"] = "order_completed"
            return response, state
        else:
            state["current_state"] = "order_not_found"
            return "I couldn't find that order. Would you like to place a new order instead?", state
    
    def _handle_get_order_phone(self, message: str, state: Dict) -> Tuple[str, Dict]:
        phone = self.extract_entities(message, 'phone')
        
        if not phone:
            return "I need a valid 10-digit phone number. Please try again.", state
        
        customer = self.db_handler.get_user(phone)
        if customer and 'order_history' in customer and customer['order_history']:
            state["current_state"] = "show_phone_orders"
            state["temp_phone"] = phone
            return self.process_message(message, state)
        else:
            return "I couldn't find any orders for this phone number. Would you like to place a new order?", state
    
    def _handle_show_phone_orders(self, message: str, state: Dict) -> Tuple[str, Dict]:
        phone = state.get("temp_phone", "")
        
        if not phone:
            return "I'm having trouble finding your phone number. Let's try again.", state
        
        customer = self.db_handler.get_user(phone)
        order_history = customer.get('order_history', [])
        
        if not order_history:
            state["current_state"] = "welcome"
            return "You don't have any previous orders. Would you like to place a new order?", state
        
        # Find the most recent order
        latest_order_id = order_history[-1]
        latest_order = self.db_handler.get_order_by_id(latest_order_id)
        
        if latest_order:
            response = f"I found {len(order_history)} orders for this phone number. Here's your most recent order:\n\n"
            response += f"Order ID: {latest_order['order_id']}\n"
            response += f"Status: {latest_order['status']}\n"
            response += f"Order Date: {latest_order['timestamp']}\n\n"
            response += "Items ordered:\n"
            
            for item in latest_order['items']:
                response += f"• {item['quantity']} {item['name']}(s) - ${item['price'] * item['quantity']:.2f}\n"
            
            response += f"\nTotal: ${latest_order['total']:.2f}\n\n"
            response += "Would you like to place a new order?"
            state["current_state"] = "order_completed"
            return response, state
        else:
            state["current_state"] = "welcome"
            return "I couldn't find details for your most recent order. Would you like to place a new order?", state
    
    def _handle_order_not_found(self, message: str, state: Dict) -> Tuple[str, Dict]:
        if 'yes' in message.lower() or 'yeah' in message.lower():
            state["current_state"] = "customer_identification"
            return "Let's place a new order. Have you ordered with us before?", state
        else:
            state["current_state"] = "welcome"
            return "Is there anything else I can help you with today?", state


# ===== Streamlit UI Application ===== #
def initialize_session_state():
    """Initialize the session state with default values"""
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "Welcome to QuickBite Food Ordering! How can I help you today? You can order food, check an existing order, or ask for help."}]
    
    if "order_state" not in st.session_state:
        st.session_state.order_state = {
            "user_id": str(uuid.uuid4()),
            "current_state": "welcome",
            "cart": [],
            "customer_info": {},
        }
    
    if "order_system" not in st.session_state:
        st.session_state.order_system = FoodOrderingSystem()
    
    if "tts_engine" not in st.session_state:
        st.session_state.tts_engine = TTSEngine()
    
    if "is_recording" not in st.session_state:
        st.session_state.is_recording = False
    
    if "audio_queue" not in st.session_state:
        st.session_state.audio_queue = queue.Queue()
    
    if "stop_audio" not in st.session_state:
        st.session_state.stop_audio = threading.Event()
    
    if "transcription" not in st.session_state:
        st.session_state.transcription = ""
    
    if "audio_buffer" not in st.session_state:
        st.session_state.audio_buffer = []


def speak_text_in_background(text):
    """Speak text in a background thread using the TTS engine"""
    # Ensure we use a global singleton TTS engine
    if 'tts_engine' in st.session_state:
        def speak_thread():
            try:
                st.session_state.tts_engine.speak(text)
            except Exception as e:
                print(f"Error in TTS thread: {e}")
        
        # Start the speech in a separate thread
        threading.Thread(target=speak_thread, daemon=True).start()
        return True
    return False


def start_recording():
    """Start recording audio from the microphone"""
    if not HAS_FASTER_WHISPER:
        st.warning("Faster Whisper is not available. Please install it first.")
        return
    
    if "order_system" not in st.session_state:
        st.warning("Order system not available")
        return
    
    system = st.session_state.order_system
    if not system.speech_services.whisper_model:
        st.warning("Whisper model not initialized.")
        return
    
    # Clear previous state
    st.session_state.audio_queue = queue.Queue()
    st.session_state.stop_audio.clear()
    st.session_state.is_recording = True
    st.session_state.audio_buffer = []
    st.session_state.transcription = ""
    
    # Define a safe thread function that doesn't access session state
    def audio_thread(system_services, audio_queue, stop_event):
        try:
            system_services.stream_audio(audio_queue, stop_event)
        except Exception as e:
            print(f"Error in audio thread: {e}")
    
    # Start audio streaming in a separate thread
    threading.Thread(
        target=audio_thread,
        args=(system.speech_services, st.session_state.audio_queue, st.session_state.stop_audio),
        daemon=True
    ).start()
    
    # Force a rerun
    st.rerun()


def stop_recording():
    """Stop recording and process the audio"""
    if not st.session_state.is_recording:
        return
    
    # Signal to stop recording
    st.session_state.stop_audio.set()
    st.session_state.is_recording = False
    
    # Process collected audio
    audio_chunks = []
    try:
        while not st.session_state.audio_queue.empty():
            chunk = st.session_state.audio_queue.get(block=False)
            audio_chunks.append(chunk)
    except queue.Empty:
        pass
    
    # Transcribe audio if we have enough data
    if audio_chunks and "order_system" in st.session_state:
        try:
            # Combine chunks
            audio_data = np.concatenate(audio_chunks)
            
            # Transcribe
            transcription = st.session_state.order_system.speech_services.transcribe_audio(audio_data)
            
            if transcription:
                st.session_state.transcription = transcription
                # Add to chat
                st.session_state.messages.append({"role": "user", "content": transcription})
                
                # Process message
                with st.spinner("Thinking..."):
                    response, updated_state = st.session_state.order_system.process_message(
                        transcription, st.session_state.order_state
                    )
                
                # Update state
                st.session_state.order_state = updated_state
                
                # Add response
                st.session_state.messages.append({"role": "assistant", "content": response})
                
                # Speak the response
                speak_text_in_background(response)
        except Exception as e:
            print(f"Error processing audio: {e}")
    
    # Force a rerun
    st.rerun()


def process_audio_continuously():
    """Process audio in chunks for continuous transcription"""
    if not st.session_state.is_recording:
        return
    
    # Check if there's audio to process
    if not st.session_state.audio_queue.empty() and "order_system" in st.session_state:
        # Get audio chunks
        chunks = []
        try:
            max_chunks = min(10, st.session_state.audio_queue.qsize())
            for _ in range(max_chunks):
                chunk = st.session_state.audio_queue.get(block=False)
                chunks.append(chunk)
                st.session_state.audio_buffer.append(chunk)
        except queue.Empty:
            pass
        
        # Limit buffer size
        max_buffer = 50
        if len(st.session_state.audio_buffer) > max_buffer:
            st.session_state.audio_buffer = st.session_state.audio_buffer[-max_buffer:]
        
        # Try to transcribe if we have enough audio
        if len(st.session_state.audio_buffer) > 5:
            try:
                audio_data = np.concatenate(st.session_state.audio_buffer)
                text = st.session_state.order_system.speech_services.transcribe_audio(audio_data)
                if text:
                    st.session_state.transcription = text
            except Exception as e:
                print(f"Error in continuous transcription: {e}")
    
    # Schedule next update
    if st.session_state.is_recording:
        time.sleep(0.5)
        st.rerun()


def cleanup():
    """Clean up resources when the app is closed"""
    if "stop_audio" in st.session_state:
        st.session_state.stop_audio.set()
    time.sleep(0.5)


def main():
    st.set_page_config(
        page_title="QuickBite Food Ordering",
        page_icon="🍔",
        layout="centered",
    )
    
    # Initialize session state
    initialize_session_state()
    
    # Display title
    st.title("🍔 QuickBite Food Ordering")
    st.markdown("Chat with our AI assistant to order food or check existing orders.")
    
    # Display cart status if it has items
    if st.session_state.order_state["cart"]:
        with st.sidebar:
            st.subheader("Your Cart")
            total = 0
            for item in st.session_state.order_state["cart"]:
                item_total = item["price"] * item["quantity"]
                total += item_total
                st.markdown(f"• {item['quantity']} {item['name']} - ${item_total:.2f}")
            st.markdown(f"**Total: ${total:.2f}**")
            
            if st.button("Checkout"):
                # Add a checkout message
                st.session_state.messages.append({"role": "user", "content": "checkout"})
                
                # Process the checkout request
                response, updated_state = st.session_state.order_system.process_message(
                    "checkout", st.session_state.order_state
                )
                
                # Update the order state
                st.session_state.order_state = updated_state
                
                # Add assistant response
                st.session_state.messages.append({"role": "assistant", "content": response})
                
                # Speak the response
                speak_text_in_background(response)
                
                # Force a rerun to show the updated UI
                st.rerun()
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Add controls for voice input
    col1, col2 = st.columns([5, 1])
    
    with col1:
        # Input for text message
        if prompt := st.chat_input("Type your message here..."):
            # Add user message to chat history
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            # Process the message
            with st.spinner("Thinking..."):
                response, updated_state = st.session_state.order_system.process_message(
                    prompt, st.session_state.order_state
                )
            
            # Update the order state
            st.session_state.order_state = updated_state
            
            # Add assistant response to chat history
            st.session_state.messages.append({"role": "assistant", "content": response})
            
            # Speak the response
            speak_text_in_background(response)
            
            # Force a rerun to show the updated UI
            st.rerun()
    
    with col2:
        # Voice input button
        if not st.session_state.is_recording:
            voice_button = st.button("🎤", key="voice_button")
            if voice_button and HAS_FASTER_WHISPER:
                start_recording()
                # Start continuous processing
                process_audio_continuously()
        else:
            stop_button = st.button("⏹️", key="stop_button")
            if stop_button:
                stop_recording()
    
    # Show transcription preview during recording
    if st.session_state.is_recording:
        st.markdown("**Recording...**")
        if st.session_state.transcription:
            st.markdown(f"*Transcribing: {st.session_state.transcription}*")
    
    # Display menu button
    if st.button("Show Menu"):
        menu_data = st.session_state.order_system.menu_data
        menu_text = "Here's our full menu:\n\n"
        for category in menu_data.get_categories():
            menu_text += f"**{category.upper()}**\n"
            for item_name, details in menu_data.get_items_in_category(category).items():
                menu_text += f"• {item_name.title()}: {details['description']} - ${details['price']:.2f}\n"
            menu_text += "\n"
        
        # Add the menu message to chat history
        st.session_state.messages.append({"role": "assistant", "content": menu_text})
        
        # Speak the menu
        speak_text_in_background(menu_text)
        
        # Force a rerun to show the updated UI
        st.rerun()

    # Register cleanup handler
    import atexit
    atexit.register(cleanup)


if __name__ == "__main__":
    main()