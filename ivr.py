import tkinter as tk
from tkinter import ttk, messagebox, StringVar, Text, Scrollbar
import threading
import time
import os
import random
from datetime import datetime, timedelta
import sys
import traceback

# Enable detailed error tracking
print("Starting application...")
print(f"Python version: {sys.version}")
print(f"Current directory: {os.getcwd()}")

# Initialize optional dependency flags
HAS_PILLOW = False
HAS_TTS = False
HAS_SR = False
HAS_OLLAMA = False

# Try to import optional modules with detailed error reporting
try:
    from PIL import Image, ImageTk
    HAS_PILLOW = True
    print("Pillow module loaded successfully")
except ImportError:
    print("Pillow module not available - image features will be limited")
except Exception as e:
    print(f"Error loading Pillow: {e}")

try:
    import pyttsx3
    HAS_TTS = True
    print("Text-to-speech module loaded successfully")
except ImportError:
    print("pyttsx3 module not available - voice features will be limited")
except Exception as e:
    print(f"Error loading pyttsx3: {e}")

try:
    import speech_recognition as sr
    HAS_SR = True
    print("Speech recognition module loaded successfully")
except ImportError:
    print("speech_recognition module not available - voice input will be disabled")
except Exception as e:
    print(f"Error loading speech_recognition: {e}")

try:
    import ollama
    HAS_OLLAMA = True
    print("Ollama module loaded successfully")
except ImportError:
    print("Ollama module not available - AI features will be limited")
except Exception as e:
    print(f"Error loading ollama: {e}")

class UberEatsIVR:
    def __init__(self, root):
        print("Initializing main application...")
        self.root = root
        self.root.title("Uber Eats - Voice Assistant")
        self.root.geometry("400x700")
        self.root.configure(bg="#ffffff")
        
        # Set up the Ollama model name - using TinyLlama
        self.model_name = "tinyllama"
        
        # Define common fonts and colors
        self.setup_theme()
        
        if HAS_OLLAMA:
            # Initialize Ollama client
            self.ollama = ollama
            self.verify_ollama_connection()
        else:
            self.ollama = None
        
        if HAS_TTS:
            try:
                # Set up text-to-speech engine
                self.engine = pyttsx3.init()
                self.engine.setProperty('rate', 150)
                voices = self.engine.getProperty('voices')
                # Try to set a female voice if available
                for voice in voices:
                    if "female" in voice.name.lower():
                        self.engine.setProperty('voice', voice.id)
                        break
                print("Text-to-speech engine initialized")
            except Exception as e:
                print(f"Text-to-speech initialization error: {e}")
                self.engine = None
        else:
            self.engine = None
        
        if HAS_SR:
            try:
                # Set up speech recognizer
                self.recognizer = sr.Recognizer()
                self.recognizer.dynamic_energy_threshold = True
                self.recognizer.energy_threshold = 4000
                self.microphone = sr.Microphone()
                
                # Calibrate recognizer for ambient noise
                with self.microphone as source:
                    self.recognizer.adjust_for_ambient_noise(source, duration=1)
                print("Speech recognition initialized")
            except Exception as e:
                print(f"Speech recognition initialization error: {e}")
                self.recognizer = None
                self.microphone = None
        else:
            self.sr = None
            self.recognizer = None
            self.microphone = None
        
        # Initialize variables
        self.is_listening = False
        self.current_screen = "main"
        self.conversation_history = []
        self.user_info = {
            "name": "",
            "address": "",
            "phone": "",
            "payment_method": "",
            "recent_orders": []
        }
        
        # Simulated recent orders for demonstration
        self.generate_mock_data()
        
        # Show welcome dialog
        self.show_welcome_dialog()
    
    def setup_theme(self):
        """Set up fonts and colors for the UI"""
        # Colors
        self.color_primary = "#06C167"      # Green
        self.color_secondary = "#000000"    # Black
        self.color_accent = "#FF3B30"       # Red
        self.color_bg = "#FFFFFF"           # White
        self.color_dark_bg = "#222222"      # Dark gray
        self.color_light_text = "#FFFFFF"   # White
        self.color_dark_text = "#000000"    # Black
        self.color_gray_text = "#666666"    # Gray
        self.color_light_gray = "#F6F6F6"   # Light gray
        self.color_border = "#E6E6E6"       # Border color
        
        # Fonts - using system defaults for maximum compatibility
        self.font_large_bold = ("Arial", 18, "bold")
        self.font_large = ("Arial", 18)
        self.font_medium_bold = ("Arial", 14, "bold")
        self.font_medium = ("Arial", 14)
        self.font_small_bold = ("Arial", 12, "bold")
        self.font_small = ("Arial", 12)
        self.font_xs = ("Arial", 10)
        
        # Set up ttk styles
        style = ttk.Style()
        style.configure(
            "Custom.TProgressbar",
            troughcolor=self.color_light_gray,
            background=self.color_primary,
            thickness=10
        )
    
    def verify_ollama_connection(self):
        """Verify that Ollama is running and the model is available"""
        if not self.ollama:
            print("Ollama is not available")
            return False
            
        try:
            # List available models to check connection
            models = self.ollama.list()
            print("Connected to Ollama successfully")
            
            # Check if our model is available
            model_exists = any(model['name'] == self.model_name for model in models['models']) if 'models' in models else False
            
            if not model_exists:
                print(f"Model {self.model_name} not found.")
                messagebox.showwarning(
                    "Model Not Available", 
                    f"The {self.model_name} model was not found in Ollama.\n\n"
                    f"Please open a terminal and run:\n"
                    f"ollama pull {self.model_name}"
                )
                return False
            return True
        except Exception as e:
            print(f"Error connecting to Ollama: {e}")
            messagebox.showwarning(
                "Ollama Connection", 
                "Failed to connect to Ollama. Some AI features will be limited.\n\n"
                "This won't affect the basic functionality of the app."
            )
            return False
    
    def show_welcome_dialog(self):
        """Show a welcome dialog with proper sizing"""
        print("Showing welcome dialog...")
        try:
            # Create a translucent overlay
            overlay = tk.Toplevel(self.root)
            
            # Position it over the main window
            overlay.geometry(f"{self.root.winfo_width()}x{self.root.winfo_height()}+{self.root.winfo_x()}+{self.root.winfo_y()}")
            overlay.overrideredirect(True)  # Remove window decorations
            overlay.configure(bg="#000000")
            overlay.attributes("-alpha", 0.7)  # Semi-transparent overlay
            
            # Create welcome frame with SMALLER HEIGHT to ensure buttons are visible
            welcome_frame = tk.Frame(overlay, bg="white", padx=20, pady=20)
            welcome_frame.place(relx=0.5, rely=0.5, anchor="center", width=350, height=400)
            
            # Add Uber Eats logo (text only for stability)
            logo_label = tk.Label(
                welcome_frame, 
                text="UBER EATS", 
                font=self.font_large_bold,
                bg="white"
            )
            logo_label.pack(pady=(0, 10))
            
            # Welcome title
            title_label = tk.Label(
                welcome_frame, 
                text="Welcome", 
                font=self.font_large_bold,
                bg="white"
            )
            title_label.pack(pady=(0, 10))
            
            # Add ready status
            status_label = tk.Label(
                welcome_frame,
                text="Your AI assistant is ready!",
                font=self.font_small,
                fg=self.color_gray_text,
                bg="white"
            )
            status_label.pack(pady=(0, 15))
            
            # Generate a simple greeting
            greeting = "Welcome to Uber Eats! I'm your AI assistant and I'm here to help you order delicious food, track deliveries, and answer any questions. What would you like to do today?"
            
            # Add a greeting message box with fixed height
            greeting_frame = tk.Frame(
                welcome_frame,
                bg="#f5f5f5",
                padx=15,
                pady=15
            )
            greeting_frame.pack(fill=tk.X, pady=(0, 15))
            
            greeting_text = tk.Label(
                greeting_frame,
                text=greeting,
                font=self.font_small,
                bg="#f5f5f5",
                wraplength=280,
                justify=tk.LEFT
            )
            greeting_text.pack(anchor=tk.W)
            
            # Continue button with higher contrast and visibility
            continue_button = tk.Button(
                welcome_frame,
                text="Let's Start",
                font=self.font_small_bold,
                bg=self.color_primary,
                fg=self.color_light_text,
                padx=20,
                pady=10,
                bd=0,
                relief=tk.FLAT,
                command=lambda: self.dismiss_welcome(overlay)
            )
            continue_button.pack(pady=20)  # Add more padding to ensure visibility
            
            # Speak the greeting
            self.speak(greeting)
            
        except Exception as e:
            print(f"Error showing welcome dialog: {e}")
            print(traceback.format_exc())
            # If welcome dialog fails, just go to main screen
            self.create_main_screen()
    
    def dismiss_welcome(self, overlay):
        """Dismiss the welcome overlay and show the main screen"""
        try:
            overlay.destroy()
        except Exception as e:
            print(f"Error dismissing welcome: {e}")
        
        # Now show the main screen
        self.create_main_screen()
    
    def generate_mock_data(self):
        """Generate mock user data and orders"""
        print("Generating mock data...")
        try:
            # Generate some mock data for the user
            first_names = ["Alex", "Jordan", "Taylor", "Morgan", "Casey"]
            last_names = ["Smith", "Johnson", "Brown", "Davis", "Wilson"]
            streets = ["Main St", "Park Ave", "Oak Rd", "Maple Ln", "Cedar Blvd"]
            
            self.user_info["name"] = f"{random.choice(first_names)} {random.choice(last_names)}"
            self.user_info["address"] = f"{random.randint(100, 999)} {random.choice(streets)}, Apt {random.randint(1, 50)}"
            self.user_info["phone"] = f"({random.randint(100, 999)}) {random.randint(100, 999)}-{random.randint(1000, 9999)}"
            self.user_info["payment_method"] = random.choice(["Visa ending in 4242", "Mastercard ending in 5555", "PayPal"])
            
            # Generate random recent orders
            restaurants = ["Pizza Palace", "Burger Bistro", "Sushi Supreme", "Taco Time", "Pasta Paradise"]
            items = [
                ["Pepperoni Pizza", "Cheese Pizza", "Garlic Knots", "Caesar Salad"],
                ["Cheeseburger", "Bacon Burger", "Fries", "Milkshake"],
                ["California Roll", "Spicy Tuna Roll", "Miso Soup", "Edamame"],
                ["Beef Tacos", "Chicken Quesadilla", "Nachos", "Guacamole"],
                ["Spaghetti Carbonara", "Fettuccine Alfredo", "Garlic Bread", "Tiramisu"]
            ]
            
            # Generate 3 recent orders
            for i in range(3):
                restaurant_idx = random.randint(0, len(restaurants) - 1)
                restaurant = restaurants[restaurant_idx]
                
                # Select 1-3 random items from this restaurant
                num_items = random.randint(1, 3)
                order_items = random.sample(items[restaurant_idx], num_items)
                
                # Generate a random date within the last 30 days
                days_ago = random.randint(1, 30)
                order_date = (datetime.now() - timedelta(days=days_ago)).strftime("%B %d, %Y")
                
                # Generate a random total between $15 and $50
                total = round(random.uniform(15, 50), 2)
                
                self.user_info["recent_orders"].append({
                    "restaurant": restaurant,
                    "items": order_items,
                    "date": order_date,
                    "total": total,
                    "status": random.choice(["Delivered", "Cancelled"]) if days_ago > 1 else "In Progress"
                })
        except Exception as e:
            print(f"Error generating mock data: {e}")
            # Add a single fallback order if there's an error
            self.user_info["name"] = "Test User"
            self.user_info["address"] = "123 Main St, Apt 4B"
            self.user_info["phone"] = "(555) 123-4567"
            self.user_info["payment_method"] = "Visa ending in 4242"
            self.user_info["recent_orders"].append({
                "restaurant": "Pizza Palace",
                "items": ["Pepperoni Pizza", "Garlic Knots"],
                "date": datetime.now().strftime("%B %d, %Y"),
                "total": 24.99,
                "status": "In Progress"
            })

    def create_main_screen(self):
        """Create the main app screen with error handling"""
        print("Creating main screen...")
        try:
            # Clear any existing widgets
            for widget in self.root.winfo_children():
                widget.destroy()
            
            self.current_screen = "main"
            
            # Create a frame to hold all content with padding
            main_frame = tk.Frame(self.root, bg=self.color_bg, padx=20, pady=20)
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # Logo at the top (text-based for stability)
            logo_label = tk.Label(
                main_frame,
                text="UBER EATS",
                font=self.font_large_bold,
                bg=self.color_bg
            )
            logo_label.pack(pady=(0, 20))
            
            # Welcome header
            welcome_label = tk.Label(
                main_frame,
                text="Welcome to Uber Eats",
                font=self.font_large_bold,
                bg=self.color_bg,
                fg=self.color_dark_text
            )
            welcome_label.pack(pady=(0, 5))
            
            if self.user_info["name"]:
                name_label = tk.Label(
                    main_frame,
                    text=f"Hello, {self.user_info['name']}",
                    font=self.font_medium,
                    bg=self.color_bg,
                    fg=self.color_gray_text
                )
                name_label.pack(pady=(0, 20))
            
            # Guided ordering button - NEW!
            guided_button = tk.Button(
                main_frame,
                text="🤖 Start Guided Ordering",
                font=self.font_medium_bold,
                bg="#FF5733",  # Different color to stand out
                fg=self.color_light_text,
                padx=20,
                pady=15,
                bd=0,
                relief=tk.FLAT,
                command=self.show_guided_ordering
            )
            guided_button.pack(fill=tk.X, pady=(0, 20))
            
            # AI Assistant Button
            assistant_button = tk.Button(
                main_frame,
                text="💬 Ask Me Anything",
                font=self.font_medium_bold,
                bg=self.color_primary,
                fg=self.color_light_text,
                padx=20,
                pady=12,
                bd=0,
                relief=tk.FLAT,
                command=self.show_ai_assistant_dialog
            )
            assistant_button.pack(fill=tk.X, pady=(0, 20))
            
            # Main options frame with title
            options_label = tk.Label(
                main_frame,
                text="Quick Actions",
                font=self.font_medium_bold,
                bg=self.color_bg,
                anchor=tk.W
            )
            options_label.pack(anchor=tk.W, pady=(0, 10))
            
            # Create menu options
            self.create_menu_option(main_frame, "Order Food", "🍔", self.show_order_screen)
            self.create_menu_option(main_frame, "Track Delivery", "🚚", self.show_tracking_screen)
            self.create_menu_option(main_frame, "Past Orders", "📋", self.show_past_orders)
            self.create_menu_option(main_frame, "Account", "👤", self.show_account_screen)
            self.create_menu_option(main_frame, "Customer Service", "🎧", self.show_customer_service)
            
            # Voice assistant button at bottom
            voice_button = tk.Button(
                main_frame,
                text="🎤  Speak to Assistant",
                font=self.font_medium_bold,
                bg=self.color_dark_bg,
                fg=self.color_light_text,
                padx=20,
                pady=10,
                bd=0,
                relief=tk.FLAT,
                command=self.toggle_voice_recognition
            )
            voice_button.pack(fill=tk.X, pady=(20, 10), side=tk.BOTTOM)
            
            # Status indicator
            self.status_var = tk.StringVar()
            self.status_var.set("What would you like to do today?")
            
            status_label = tk.Label(
                main_frame,
                textvariable=self.status_var,
                font=self.font_xs,
                bg=self.color_bg,
                fg=self.color_gray_text
            )
            status_label.pack(side=tk.BOTTOM, pady=10)
            
            # Speak a welcome message highlighting guided ordering
            welcome_message = f"Welcome to Uber Eats{', ' + self.user_info['name'] if self.user_info['name'] else ''}. You can start a guided ordering experience where I'll help you through each step of placing your order. What would you like to do today?"
            self.speak(welcome_message)
            print("Main screen created successfully")
        except Exception as e:
            print(f"Error creating main screen: {e}")
            print(traceback.format_exc())
            # Try to create a very basic fallback screen
            self.create_fallback_screen("Error creating main screen", str(e))
    
    def create_fallback_screen(self, title, error_message):
        """Create a minimal fallback screen if normal screens fail"""
        print(f"Creating fallback screen due to: {error_message}")
        # Clear existing widgets
        for widget in self.root.winfo_children():
            widget.destroy()
            
        # Create a very simple frame
        frame = tk.Frame(self.root, bg="#ffffff", padx=20, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        tk.Label(
            frame, 
            text="Uber Eats Assistant", 
            font=("Arial", 18, "bold"),
            bg="#ffffff"
        ).pack(pady=(0, 20))
        
        # Error notice (not showing actual error to user)
        tk.Label(
            frame,
            text="We've encountered a temporary issue.",
            font=("Arial", 14),
            bg="#ffffff"
        ).pack(pady=(0, 10))
        
        # Main options
        tk.Button(
            frame,
            text="Order Food",
            font=("Arial", 14),
            bg="#06C167",
            fg="white",
            padx=20,
            pady=10,
            bd=0,
            command=self.show_order_screen
        ).pack(fill=tk.X, pady=10)
        
        tk.Button(
            frame,
            text="Track Delivery",
            font=("Arial", 14),
            bg="#06C167",
            fg="white",
            padx=20,
            pady=10,
            bd=0,
            command=self.show_tracking_screen
        ).pack(fill=tk.X, pady=10)
        
        # Status label
        tk.Label(
            frame,
            text="Limited functionality available",
            font=("Arial", 10),
            fg="#666666",
            bg="#ffffff"
        ).pack(side=tk.BOTTOM, pady=10)
    
    def create_menu_option(self, parent, text, emoji, command):
        """Create a menu option button with icon"""
        try:
            # Create a simple button with good size and padding
            option_frame = tk.Frame(
                parent, 
                bg=self.color_bg,
                highlightbackground=self.color_border,
                highlightthickness=1,
                padx=10, 
                pady=10
            )
            option_frame.pack(fill=tk.X, pady=5)
            
            # Left emoji icon
            emoji_label = tk.Label(
                option_frame,
                text=emoji,
                font=self.font_large,
                bg=self.color_bg
            )
            emoji_label.pack(side=tk.LEFT, padx=(10, 20))
            
            # Middle text
            text_label = tk.Label(
                option_frame,
                text=text,
                font=self.font_medium,
                bg=self.color_bg,
                anchor=tk.W
            )
            text_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            # Right arrow
            arrow_label = tk.Label(
                option_frame,
                text="→",
                font=self.font_medium,
                bg=self.color_bg
            )
            arrow_label.pack(side=tk.RIGHT, padx=10)
            
            # Make the entire frame clickable
            option_frame.bind("<Button-1>", lambda e: command())
            emoji_label.bind("<Button-1>", lambda e: command())
            text_label.bind("<Button-1>", lambda e: command())
            arrow_label.bind("<Button-1>", lambda e: command())
            
            # Change appearance on hover
            def on_enter(e):
                option_frame.config(bg=self.color_light_gray)
                emoji_label.config(bg=self.color_light_gray)
                text_label.config(bg=self.color_light_gray)
                arrow_label.config(bg=self.color_light_gray)
            
            def on_leave(e):
                option_frame.config(bg=self.color_bg)
                emoji_label.config(bg=self.color_bg)
                text_label.config(bg=self.color_bg)
                arrow_label.config(bg=self.color_bg)
            
            option_frame.bind("<Enter>", on_enter)
            option_frame.bind("<Leave>", on_leave)
            emoji_label.bind("<Enter>", on_enter)
            emoji_label.bind("<Leave>", on_leave)
            text_label.bind("<Enter>", on_enter)
            text_label.bind("<Leave>", on_leave)
            arrow_label.bind("<Enter>", on_enter)
            arrow_label.bind("<Leave>", on_leave)
            
        except Exception as e:
            print(f"Error creating menu option: {e}")
            # Create a simple fallback button
            fallback_button = tk.Button(
                parent,
                text=f"{emoji} {text}",
                bg="#f0f0f0",
                pady=10,
                command=command
            )
            fallback_button.pack(fill=tk.X, pady=5)
    
    def show_guided_ordering(self):
        """Show guided ordering screen"""
        print("Showing guided ordering screen")
        try:
            # Clear existing widgets
            for widget in self.root.winfo_children():
                widget.destroy()
            
            self.current_screen = "guided_ordering"
            
            # Create header with back button
            self.create_header("Guided Ordering", self.create_main_screen)
            
            # Main content frame
            content_frame = tk.Frame(self.root, bg=self.color_bg, padx=20, pady=10)
            content_frame.pack(fill=tk.BOTH, expand=True)
            
            # Intro title
            title_label = tk.Label(
                content_frame,
                text="AI-Guided Ordering",
                font=self.font_large_bold,
                bg=self.color_bg
            )
            title_label.pack(pady=(0, 15))
            
            # Assistant profile
            assistant_frame = tk.Frame(
                content_frame,
                bg=self.color_light_gray,
                padx=15,
                pady=15
            )
            assistant_frame.pack(fill=tk.X, pady=(0, 20))
            
            # Simple avatar label instead of canvas
            avatar_label = tk.Label(
                assistant_frame,
                text="🤖",
                font=("Arial", 24),
                bg=self.color_light_gray
            )
            avatar_label.pack(side=tk.LEFT, padx=(0, 15))
            
            # Assistant info
            info_frame = tk.Frame(assistant_frame, bg=self.color_light_gray)
            info_frame.pack(side=tk.LEFT)
            
            assistant_name = tk.Label(
                info_frame,
                text="Uber Eats Assistant",
                font=self.font_medium_bold,
                bg=self.color_light_gray
            )
            assistant_name.pack(anchor=tk.W)
            
            assistant_desc = tk.Label(
                info_frame,
                text="I'll help you place your order step by step",
                font=self.font_small,
                fg=self.color_gray_text,
                bg=self.color_light_gray
            )
            assistant_desc.pack(anchor=tk.W)
            
            # Step 1: Category selection
            step_label = tk.Label(
                content_frame,
                text="Step 1: Select Food Category",
                font=self.font_medium_bold,
                bg=self.color_bg
            )
            step_label.pack(pady=(20, 10))
            
            # Add a message
            message_frame = tk.Frame(
                content_frame,
                bg="#f0f7ff",
                padx=15,
                pady=10
            )
            message_frame.pack(fill=tk.X, pady=10)
            
            message_label = tk.Label(
                message_frame,
                text="What type of food would you like to order today?",
                font=self.font_small,
                bg="#f0f7ff",
                wraplength=300
            )
            message_label.pack(anchor=tk.W)
            
            # Category buttons
            categories = [
                ("Pizza", "pizza"), 
                ("Burgers", "burger"), 
                ("Sushi", "sushi"), 
                ("Salad", "salad"), 
                ("Mexican", "mexican")
            ]
            
            for cat_name, cat_id in categories:
                cat_button = tk.Button(
                    content_frame,
                    text=cat_name,
                    font=self.font_small_bold,
                    bg=self.color_light_gray,
                    bd=0,
                    relief=tk.FLAT,
                    padx=15,
                    pady=10,
                    command=lambda c=cat_name: self.select_category(c)
                )
                cat_button.pack(fill=tk.X, pady=5)
            
            # Voice control button
            voice_button = tk.Button(
                content_frame,
                text="🎤 Use Voice",
                font=self.font_small_bold,
                bg=self.color_dark_bg,
                fg=self.color_light_text,
                padx=15,
                pady=8,
                bd=0,
                relief=tk.FLAT,
                command=self.use_voice_input
            )
            voice_button.pack(fill=tk.X, pady=(20, 10), side=tk.BOTTOM)
            
            # Cancel button
            cancel_button = tk.Button(
                content_frame,
                text="Cancel",
                font=self.font_small,
                bg=self.color_light_gray,
                padx=15,
                pady=8,
                bd=0,
                relief=tk.FLAT,
                command=self.create_main_screen
            )
            cancel_button.pack(fill=tk.X, pady=(0, 10), side=tk.BOTTOM)
            
            # Speak guidance
            self.speak("What type of food would you like to order today? You can select a category or use voice to tell me.")
            
        except Exception as e:
            print(f"Error showing guided ordering: {e}")
            print(traceback.format_exc())
            messagebox.showinfo("Guided Ordering", "The guided ordering feature would appear here in the full version")
            self.create_main_screen()
    
    def select_category(self, category):
        """Handle category selection in guided ordering"""
        self.show_restaurant_selection(category)
    
    def show_restaurant_selection(self, category):
        """Show restaurant selection screen based on category"""
        try:
            # Clear existing widgets
            for widget in self.root.winfo_children():
                widget.destroy()
            
            self.current_screen = "restaurant_selection"
            
            # Create header with back button
            self.create_header("Select Restaurant", self.show_guided_ordering)
            
            # Main content frame
            content_frame = tk.Frame(self.root, bg=self.color_bg, padx=20, pady=10)
            content_frame.pack(fill=tk.BOTH, expand=True)
            
            # Step title
            step_label = tk.Label(
                content_frame,
                text=f"Step 2: Choose a {category} Restaurant",
                font=self.font_medium_bold,
                bg=self.color_bg
            )
            step_label.pack(pady=(10, 15))
            
            # Add a message
            message_frame = tk.Frame(
                content_frame,
                bg="#f0f7ff",
                padx=15,
                pady=10
            )
            message_frame.pack(fill=tk.X, pady=10)
            
            message_label = tk.Label(
                message_frame,
                text=f"Great choice! Select a restaurant for {category}:",
                font=self.font_small,
                bg="#f0f7ff",
                wraplength=300
            )
            message_label.pack(anchor=tk.W)
            
            # Get restaurants based on category
            restaurants = {
                "Pizza": ["Pizza Palace", "Pizza Heaven", "Slice of Life"],
                "Burgers": ["Burger Bistro", "Patty Palace", "Grill Masters"],
                "Sushi": ["Sushi Supreme", "Wasabi", "Tokyo Bites"],
                "Salad": ["Green Garden", "Fresh Greens", "Salad Bowl"],
                "Mexican": ["Taco Time", "Burrito Bros", "Spicy Mexico"]
            }
            
            options = restaurants.get(category, ["Restaurant 1", "Restaurant 2"])
            
            # Create restaurant buttons
            for restaurant in options:
                # Create random details for the restaurant
                rating = round(random.uniform(3.5, 4.9), 1)
                time = random.randint(15, 45)
                fee = round(random.uniform(0.99, 4.99), 2)
                
                # Restaurant frame with details
                rest_frame = tk.Frame(
                    content_frame,
                    bg=self.color_bg,
                    highlightbackground=self.color_border,
                    highlightthickness=1,
                    padx=15,
                    pady=15
                )
                rest_frame.pack(fill=tk.X, pady=8)
                
                # Restaurant name
                name_label = tk.Label(
                    rest_frame,
                    text=restaurant,
                    font=self.font_small_bold,
                    bg=self.color_bg,
                    anchor=tk.W
                )
                name_label.pack(anchor=tk.W)
                
                # Restaurant details
                details_label = tk.Label(
                    rest_frame,
                    text=f"⭐ {rating} • {time} min • ${fee} delivery",
                    font=self.font_xs,
                    fg=self.color_gray_text,
                    bg=self.color_bg,
                    anchor=tk.W
                )
                details_label.pack(anchor=tk.W, pady=(5, 0))
                
                # Make everything clickable
                rest_frame.bind("<Button-1>", lambda e, r=restaurant: self.select_restaurant(r, category))
                name_label.bind("<Button-1>", lambda e, r=restaurant: self.select_restaurant(r, category))
                details_label.bind("<Button-1>", lambda e, r=restaurant: self.select_restaurant(r, category))
                
                # Hover effect
                def on_enter(e, frame=rest_frame):
                    frame.config(bg=self.color_light_gray)
                    for widget in frame.winfo_children():
                        widget.config(bg=self.color_light_gray)
                
                def on_leave(e, frame=rest_frame):
                    frame.config(bg=self.color_bg)
                    for widget in frame.winfo_children():
                        widget.config(bg=self.color_bg)
                
                rest_frame.bind("<Enter>", on_enter)
                rest_frame.bind("<Leave>", on_leave)
                name_label.bind("<Enter>", on_enter)
                name_label.bind("<Leave>", on_leave)
                details_label.bind("<Enter>", on_enter)
                details_label.bind("<Leave>", on_leave)
            
            # Voice control button
            voice_button = tk.Button(
                content_frame,
                text="🎤 Use Voice",
                font=self.font_small_bold,
                bg=self.color_dark_bg,
                fg=self.color_light_text,
                padx=15,
                pady=8,
                bd=0,
                relief=tk.FLAT,
                command=self.use_voice_input
            )
            voice_button.pack(fill=tk.X, pady=(20, 10), side=tk.BOTTOM)
            
            # Back button
            back_button = tk.Button(
                content_frame,
                text="Back",
                font=self.font_small,
                bg=self.color_light_gray,
                padx=15,
                pady=8,
                bd=0,
                relief=tk.FLAT,
                command=self.show_guided_ordering
            )
            back_button.pack(fill=tk.X, pady=(0, 10), side=tk.BOTTOM)
            
            # Speak guidance
            self.speak(f"Great choice! Please select a restaurant for {category}")
            
        except Exception as e:
            print(f"Error showing restaurant selection: {e}")
            print(traceback.format_exc())
            messagebox.showinfo("Restaurant Selection", "Restaurant selection would appear here in the full version")
            self.create_main_screen()
    
    def select_restaurant(self, restaurant, category):
        """Handle restaurant selection"""
        self.show_menu_selection(restaurant, category)
    
    def show_menu_selection(self, restaurant, category):
        """Show menu items selection screen for the chosen restaurant"""
        try:
            # Clear existing widgets
            for widget in self.root.winfo_children():
                widget.destroy()
            
            self.current_screen = "menu_selection"
            
            # Create header with back button
            self.create_header("Select Items", lambda: self.show_restaurant_selection(category))
            
            # Main content frame
            content_frame = tk.Frame(self.root, bg=self.color_bg, padx=20, pady=10)
            content_frame.pack(fill=tk.BOTH, expand=True)
            
            # Restaurant title
            restaurant_label = tk.Label(
                content_frame,
                text=restaurant,
                font=self.font_large_bold,
                bg=self.color_bg
            )
            restaurant_label.pack(pady=(0, 5))
            
            # Rating info
            rating_label = tk.Label(
                content_frame,
                text=f"⭐ {round(random.uniform(4.0, 4.9), 1)} ({random.randint(50, 500)} ratings)",
                font=self.font_small,
                fg=self.color_gray_text,
                bg=self.color_bg
            )
            rating_label.pack(pady=(0, 15))
            
            # Add a message
            message_frame = tk.Frame(
                content_frame,
                bg="#f0f7ff",
                padx=15,
                pady=10
            )
            message_frame.pack(fill=tk.X, pady=10)
            
            message_label = tk.Label(
                message_frame,
                text=f"What would you like to order from {restaurant}?",
                font=self.font_small,
                bg="#f0f7ff",
                wraplength=300
            )
            message_label.pack(anchor=tk.W)
            
            # Menu items based on restaurant
            items = {
                "Pizza Palace": [
                    ("Pepperoni Pizza", "$13.99", "Classic pepperoni pizza with mozzarella cheese"),
                    ("Cheese Pizza", "$11.99", "Traditional cheese pizza with tomato sauce"),
                    ("Hawaiian Pizza", "$14.99", "Ham and pineapple on a classic base"),
                    ("Garlic Knots", "$5.99", "Freshly baked garlic knots with dipping sauce")
                ],
                "Burger Bistro": [
                    ("Cheeseburger", "$9.99", "Classic beef patty with cheddar cheese"),
                    ("Bacon Burger", "$11.99", "Beef patty topped with crispy bacon"),
                    ("Veggie Burger", "$10.99", "Plant-based patty with fresh toppings"),
                    ("Fries", "$3.99", "Crispy golden french fries")
                ],
                "Sushi Supreme": [
                    ("California Roll", "$8.99", "Crab, avocado and cucumber roll"),
                    ("Spicy Tuna Roll", "$10.99", "Fresh tuna with spicy mayo"),
                    ("Dragon Roll", "$12.99", "Eel and cucumber topped with avocado"),
                    ("Miso Soup", "$3.99", "Traditional Japanese soup")
                ]
            }
            
            # Use a default menu if the restaurant isn't in our predefined list
            menu_items = items.get(restaurant, [
                ("Signature Dish", "$12.99", "The restaurant's most popular item"),
                ("Special Item", "$14.99", "Chef's special creation"),
                ("Side Dish", "$5.99", "Perfect accompaniment"),
                ("Dessert", "$6.99", "Sweet treat to finish your meal")
            ])
            
            # Create scrollable canvas for menu items
            canvas_frame = tk.Frame(content_frame, bg=self.color_bg)
            canvas_frame.pack(fill=tk.BOTH, expand=True, pady=10)
            
            canvas = tk.Canvas(canvas_frame, bg=self.color_bg, highlightthickness=0)
            scrollbar = tk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
            
            scroll_frame = tk.Frame(canvas, bg=self.color_bg)
            
            # Configure the canvas
            canvas.configure(yscrollcommand=scrollbar.set)
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
            # Create a window in the canvas to hold the scrollable frame
            canvas.create_window((0, 0), window=scroll_frame, anchor="nw", width=canvas.winfo_reqwidth())
            
            # Create menu items
            for name, price, description in menu_items:
                # Item frame
                item_frame = tk.Frame(
                    scroll_frame,
                    bg=self.color_bg,
                    highlightbackground=self.color_border,
                    highlightthickness=1,
                    padx=15,
                    pady=15
                )
                item_frame.pack(fill=tk.X, pady=8)
                
                # Item header (name and price)
                header_frame = tk.Frame(item_frame, bg=self.color_bg)
                header_frame.pack(fill=tk.X)
                
                name_label = tk.Label(
                    header_frame,
                    text=name,
                    font=self.font_small_bold,
                    bg=self.color_bg,
                    anchor=tk.W
                )
                name_label.pack(side=tk.LEFT)
                
                price_label = tk.Label(
                    header_frame,
                    text=price,
                    font=self.font_small,
                    bg=self.color_bg,
                    anchor=tk.E
                )
                price_label.pack(side=tk.RIGHT)
                
                # Description
                desc_label = tk.Label(
                    item_frame,
                    text=description,
                    font=self.font_xs,
                    fg=self.color_gray_text,
                    bg=self.color_bg,
                    anchor=tk.W,
                    wraplength=300,
                    justify=tk.LEFT
                )
                desc_label.pack(anchor=tk.W, pady=(5, 0))
                
                # Add button
                add_button = tk.Button(
                    item_frame,
                    text="Add to Order",
                    font=self.font_small,
                    bg=self.color_primary,
                    fg=self.color_light_text,
                    padx=10,
                    pady=5,
                    bd=0,
                    relief=tk.FLAT,
                    command=lambda item=name: self.add_to_order(item, restaurant, category)
                )
                add_button.pack(anchor=tk.E, pady=(10, 0))
                
                # Make everything clickable except the add button
                item_frame.bind("<Button-1>", lambda e, item=name: self.add_to_order(item, restaurant, category))
                name_label.bind("<Button-1>", lambda e, item=name: self.add_to_order(item, restaurant, category))
                price_label.bind("<Button-1>", lambda e, item=name: self.add_to_order(item, restaurant, category))
                desc_label.bind("<Button-1>", lambda e, item=name: self.add_to_order(item, restaurant, category))
                
                # Hover effect
                def on_enter(e, frame=item_frame):
                    frame.config(bg=self.color_light_gray)
                    for widget in frame.winfo_children():
                        if widget != add_button:
                            widget.config(bg=self.color_light_gray)
                    header_frame.config(bg=self.color_light_gray)
                    for widget in header_frame.winfo_children():
                        widget.config(bg=self.color_light_gray)
                
                def on_leave(e, frame=item_frame):
                    frame.config(bg=self.color_bg)
                    for widget in frame.winfo_children():
                        if widget != add_button:
                            widget.config(bg=self.color_bg)
                    header_frame.config(bg=self.color_bg)
                    for widget in header_frame.winfo_children():
                        widget.config(bg=self.color_bg)
                
                item_frame.bind("<Enter>", on_enter)
                item_frame.bind("<Leave>", on_leave)
            
            # Update scroll region when frame size changes
            def on_frame_configure(event):
                canvas.configure(scrollregion=canvas.bbox("all"))
            
            scroll_frame.bind("<Configure>", on_frame_configure)
            
            # Voice control button
            voice_button = tk.Button(
                content_frame,
                text="🎤 Use Voice",
                font=self.font_small_bold,
                bg=self.color_dark_bg,
                fg=self.color_light_text,
                padx=15,
                pady=8,
                bd=0,
                relief=tk.FLAT,
                command=self.use_voice_input
            )
            voice_button.pack(fill=tk.X, pady=(10, 5), side=tk.BOTTOM)
            
            # Back button
            back_button = tk.Button(
                content_frame,
                text="Back",
                font=self.font_small,
                bg=self.color_light_gray,
                padx=15,
                pady=8,
                bd=0,
                relief=tk.FLAT,
                command=lambda: self.show_restaurant_selection(category)
            )
            back_button.pack(fill=tk.X, pady=(0, 10), side=tk.BOTTOM)
            
            # Speak guidance
            self.speak(f"Here's the menu from {restaurant}. What would you like to order?")
            
        except Exception as e:
            print(f"Error showing menu selection: {e}")
            print(traceback.format_exc())
            messagebox.showinfo("Menu Selection", "Menu selection would appear here in the full version")
            self.create_main_screen()
    
    def add_to_order(self, item, restaurant, category):
        """Handle adding an item to the order"""
        print(f"Adding {item} from {restaurant} to the order")
        
        # Normally we would build an order structure
        # For this demo, just go to order summary
        self.show_order_summary(restaurant, [item])
    
    def show_order_summary(self, restaurant, items):
        """Show order summary and checkout screen"""
        try:
            # Clear existing widgets
            for widget in self.root.winfo_children():
                widget.destroy()
            
            self.current_screen = "order_summary"
            
            # Create header with back button
            self.create_header("Review Order", self.create_main_screen)
            
            # Main content frame
            content_frame = tk.Frame(self.root, bg=self.color_bg, padx=20, pady=10)
            content_frame.pack(fill=tk.BOTH, expand=True)
            
            # Restaurant title
            restaurant_label = tk.Label(
                content_frame,
                text=restaurant,
                font=self.font_medium_bold,
                bg=self.color_bg
            )
            restaurant_label.pack(pady=(0, 15))
            
            # Order items section
            items_label = tk.Label(
                content_frame,
                text="Your Order",
                font=self.font_medium_bold,
                bg=self.color_bg,
                anchor=tk.W
            )
            items_label.pack(anchor=tk.W, pady=(0, 10))
            
            # Generate prices for the items
            total = 0
            for item in items:
                price = round(random.uniform(8.99, 15.99), 2)
                total += price
                
                # Item frame
                item_frame = tk.Frame(
                    content_frame,
                    bg=self.color_bg,
                    padx=5,
                    pady=5
                )
                item_frame.pack(fill=tk.X, pady=3)
                
                # Item name
                name_label = tk.Label(
                    item_frame,
                    text=item,
                    font=self.font_small,
                    bg=self.color_bg,
                    anchor=tk.W
                )
                name_label.pack(side=tk.LEFT)
                
                # Item price
                price_label = tk.Label(
                    item_frame,
                    text=f"${price:.2f}",
                    font=self.font_small,
                    bg=self.color_bg,
                    anchor=tk.E
                )
                price_label.pack(side=tk.RIGHT)
            
            # Separator
            separator = tk.Frame(content_frame, height=1, bg=self.color_border)
            separator.pack(fill=tk.X, pady=15)
            
            # Totals section
            subtotal = total
            tax = round(subtotal * 0.08, 2)
            delivery_fee = round(random.uniform(1.99, 4.99), 2)
            final_total = subtotal + tax + delivery_fee
            
            # Subtotal
            subtotal_frame = tk.Frame(content_frame, bg=self.color_bg)
            subtotal_frame.pack(fill=tk.X, pady=3)
            
            tk.Label(
                subtotal_frame,
                text="Subtotal",
                font=self.font_small,
                bg=self.color_bg,
                anchor=tk.W
            ).pack(side=tk.LEFT)
            
            tk.Label(
                subtotal_frame,
                text=f"${subtotal:.2f}",
                font=self.font_small,
                bg=self.color_bg,
                anchor=tk.E
            ).pack(side=tk.RIGHT)
            
            # Tax
            tax_frame = tk.Frame(content_frame, bg=self.color_bg)
            tax_frame.pack(fill=tk.X, pady=3)
            
            tk.Label(
                tax_frame,
                text="Tax",
                font=self.font_small,
                bg=self.color_bg,
                anchor=tk.W
            ).pack(side=tk.LEFT)
            
            tk.Label(
                tax_frame,
                text=f"${tax:.2f}",
                font=self.font_small,
                bg=self.color_bg,
                anchor=tk.E
            ).pack(side=tk.RIGHT)
            
            # Delivery fee
            delivery_frame = tk.Frame(content_frame, bg=self.color_bg)
            delivery_frame.pack(fill=tk.X, pady=3)
            
            tk.Label(
                delivery_frame,
                text="Delivery Fee",
                font=self.font_small,
                bg=self.color_bg,
                anchor=tk.W
            ).pack(side=tk.LEFT)
            
            tk.Label(
                delivery_frame,
                text=f"${delivery_fee:.2f}",
                font=self.font_small,
                bg=self.color_bg,
                anchor=tk.E
            ).pack(side=tk.RIGHT)
            
            # Total (with emphasis)
            total_frame = tk.Frame(content_frame, bg=self.color_bg)
            total_frame.pack(fill=tk.X, pady=(10, 20))
            
            tk.Label(
                total_frame,
                text="Total",
                font=self.font_medium_bold,
                bg=self.color_bg,
                anchor=tk.W
            ).pack(side=tk.LEFT)
            
            tk.Label(
                total_frame,
                text=f"${final_total:.2f}",
                font=self.font_medium_bold,
                bg=self.color_bg,
                anchor=tk.E
            ).pack(side=tk.RIGHT)
            
            # Delivery info
            address_label = tk.Label(
                content_frame,
                text="Delivery Address",
                font=self.font_small_bold,
                bg=self.color_bg,
                anchor=tk.W
            )
            address_label.pack(anchor=tk.W, pady=(0, 5))
            
            address_value = tk.Label(
                content_frame,
                text=self.user_info["address"],
                font=self.font_small,
                bg=self.color_bg,
                anchor=tk.W
            )
            address_value.pack(anchor=tk.W, pady=(0, 10))
            
            # Payment info
            payment_label = tk.Label(
                content_frame,
                text="Payment Method",
                font=self.font_small_bold,
                bg=self.color_bg,
                anchor=tk.W
            )
            payment_label.pack(anchor=tk.W, pady=(0, 5))
            
            payment_value = tk.Label(
                content_frame,
                text=self.user_info["payment_method"],
                font=self.font_small,
                bg=self.color_bg,
                anchor=tk.W
            )
            payment_value.pack(anchor=tk.W, pady=(0, 20))
            
            # Place order button
            place_order_button = tk.Button(
                content_frame,
                text="Place Order",
                font=self.font_medium_bold,
                bg=self.color_primary,
                fg=self.color_light_text,
                padx=20,
                pady=10,
                bd=0,
                relief=tk.FLAT,
                command=lambda: self.place_order(restaurant, items, final_total)
            )
            place_order_button.pack(fill=tk.X, pady=(0, 10))
            
            # Cancel button
            cancel_button = tk.Button(
                content_frame,
                text="Cancel",
                font=self.font_small,
                bg=self.color_light_gray,
                padx=15,
                pady=8,
                bd=0,
                relief=tk.FLAT,
                command=self.create_main_screen
            )
            cancel_button.pack(fill=tk.X, pady=(0, 10))
            
            # Speak guidance
            self.speak(f"Here's your order summary. The total is ${final_total:.2f}. Please review and place your order when ready.")
            
        except Exception as e:
            print(f"Error showing order summary: {e}")
            print(traceback.format_exc())
            messagebox.showinfo("Order Summary", "Order summary would appear here in the full version")
            self.create_main_screen()
    
    def place_order(self, restaurant, items, total):
        """Handle placing the order"""
        try:
            # Add the order to user's recent orders
            new_order = {
                "restaurant": restaurant,
                "items": items,
                "date": datetime.now().strftime("%B %d, %Y"),
                "total": total,
                "status": "In Progress"
            }
            
            self.user_info["recent_orders"].insert(0, new_order)
            
            # Show confirmation
            self.show_order_confirmation(new_order)
            
        except Exception as e:
            print(f"Error placing order: {e}")
            print(traceback.format_exc())
            messagebox.showinfo("Order Placed", f"Your order from {restaurant} has been placed!")
            self.create_main_screen()
    
    def show_order_confirmation(self, order):
        """Show order confirmation screen"""
        try:
            # Clear existing widgets
            for widget in self.root.winfo_children():
                widget.destroy()
            
            self.current_screen = "order_confirmation"
            
            # Main content frame
            content_frame = tk.Frame(self.root, bg=self.color_bg, padx=20, pady=20)
            content_frame.pack(fill=tk.BOTH, expand=True)
            
            # Success icon
            success_label = tk.Label(
                content_frame,
                text="✅",
                font=("Arial", 48),
                bg=self.color_bg
            )
            success_label.pack(pady=(20, 10))
            
            # Confirmation title
            title_label = tk.Label(
                content_frame,
                text="Order Confirmed!",
                font=self.font_large_bold,
                bg=self.color_bg
            )
            title_label.pack(pady=(0, 5))
            
            # Order details
            details_label = tk.Label(
                content_frame,
                text=f"Your order from {order['restaurant']} has been placed.",
                font=self.font_medium,
                bg=self.color_bg,
                wraplength=350
            )
            details_label.pack(pady=(0, 20))
            
            # Estimated delivery time
            delivery_time = datetime.now() + timedelta(minutes=random.randint(25, 45))
            time_str = delivery_time.strftime("%I:%M %p")
            
            time_frame = tk.Frame(content_frame, bg=self.color_bg)
            time_frame.pack(pady=(0, 30))
            
            time_label = tk.Label(
                time_frame,
                text="Estimated Delivery:",
                font=self.font_medium,
                bg=self.color_bg
            )
            time_label.pack()
            
            eta_label = tk.Label(
                time_frame,
                text=time_str,
                font=self.font_large_bold,
                bg=self.color_bg
            )
            eta_label.pack()
            
            # Order items
            items_label = tk.Label(
                content_frame,
                text="Your Order:",
                font=self.font_medium_bold,
                bg=self.color_bg,
                anchor=tk.W
            )
            items_label.pack(anchor=tk.W, pady=(0, 10))
            
            for item in order["items"]:
                item_label = tk.Label(
                    content_frame,
                    text=f"• {item}",
                    font=self.font_small,
                    bg=self.color_bg,
                    anchor=tk.W
                )
                item_label.pack(anchor=tk.W, pady=2)
            
            # Total
            total_label = tk.Label(
                content_frame,
                text=f"Total: ${order['total']:.2f}",
                font=self.font_medium_bold,
                bg=self.color_bg,
                anchor=tk.W
            )
            total_label.pack(anchor=tk.W, pady=(15, 30))
            
            # Track order button
            track_button = tk.Button(
                content_frame,
                text="Track Order",
                font=self.font_medium_bold,
                bg=self.color_primary,
                fg=self.color_light_text,
                padx=20,
                pady=10,
                bd=0,
                relief=tk.FLAT,
                command=self.show_tracking_screen
            )
            track_button.pack(fill=tk.X, pady=(0, 10))
            
            # Return to home button
            home_button = tk.Button(
                content_frame,
                text="Return to Home",
                font=self.font_small,
                bg=self.color_light_gray,
                padx=15,
                pady=8,
                bd=0,
                relief=tk.FLAT,
                command=self.create_main_screen
            )
            home_button.pack(fill=tk.X, pady=(0, 10))
            
            # Speak confirmation
            confirmation_message = f"Thank you for your order from {order['restaurant']}! Your food will be delivered around {time_str}. You can track your order status on the tracking screen."
            self.speak(confirmation_message)
            
        except Exception as e:
            print(f"Error showing order confirmation: {e}")
            print(traceback.format_exc())
            messagebox.showinfo("Order Confirmed", "Your order has been confirmed!")
            self.create_main_screen()
    
    def use_voice_input(self):
        """Handle voice input for ordering"""
        if not HAS_SR or not self.recognizer or not self.microphone:
            messagebox.showinfo("Voice Input", "Voice recognition is not available. Please install the required packages.")
            return
            
        try:
            # Show listening indicator
            self.status_var.set("🎤 Listening... Please speak")
            messagebox.showinfo("Voice Input", "In the full version, you would be able to speak your order preferences.")
        except Exception as e:
            print(f"Error with voice input: {e}")
    
    def show_order_screen(self):
        """Show order screen"""
        print("Showing order screen")
        try:
            # Clear existing widgets
            for widget in self.root.winfo_children():
                widget.destroy()
            
            self.current_screen = "order"
            
            # Create header with back button
            self.create_header("Order Food", self.create_main_screen)
            
            # Main content frame
            content_frame = tk.Frame(self.root, bg=self.color_bg, padx=20, pady=10)
            content_frame.pack(fill=tk.BOTH, expand=True)
            
            # Add AI food recommendation button at the top
            recommendation_button = tk.Button(
                content_frame,
                text="🧠 Get AI Food Recommendations",
                font=self.font_small_bold,
                bg=self.color_primary,
                fg=self.color_light_text,
                padx=15,
                pady=8,
                bd=0,
                relief=tk.FLAT,
                command=self.show_food_recommendations
            )
            recommendation_button.pack(fill=tk.X, pady=(0, 15))
            
            # Search bar
            search_frame = tk.Frame(content_frame, bg=self.color_bg, pady=10)
            search_frame.pack(fill=tk.X)
            
            search_var = tk.StringVar()
            search_entry = tk.Entry(
                search_frame,
                textvariable=search_var,
                font=self.font_small,
                bd=1,
                relief=tk.SOLID
            )
            search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=8)
            
            search_button = tk.Button(
                search_frame,
                text="🔍",
                font=self.font_small_bold,
                bg=self.color_light_gray,
                padx=10,
                pady=5,
                bd=1,
                relief=tk.SOLID
            )
            search_button.pack(side=tk.RIGHT, padx=(5, 0))
            
            # Category section
            category_label = tk.Label(
                content_frame,
                text="Categories",
                font=self.font_medium_bold,
                bg=self.color_bg,
                anchor=tk.W
            )
            category_label.pack(anchor=tk.W, pady=(20, 10))
            
            # Categories (simplified with just labels)
            categories_frame = tk.Frame(content_frame, bg=self.color_bg)
            categories_frame.pack(fill=tk.X, pady=(0, 20))
            
            categories = ["🍕 Pizza", "🍔 Burgers", "🍣 Sushi", "🥗 Salad", "🌮 Mexican"]
            
            for i, category in enumerate(categories):
                cat_button = tk.Button(
                    categories_frame,
                    text=category,
                    font=self.font_small,
                    bg=self.color_light_gray,
                    padx=10,
                    pady=5,
                    bd=0,
                    relief=tk.RAISED
                )
                cat_button.grid(row=0, column=i, padx=5)
            
            # Popular restaurants section
            popular_label = tk.Label(
                content_frame,
                text="Popular Restaurants",
                font=self.font_medium_bold,
                bg=self.color_bg,
                anchor=tk.W
            )
            popular_label.pack(anchor=tk.W, pady=(0, 10))
            
            # Restaurant listings
            restaurants = [
                "Pizza Palace", "Burger Bistro", "Sushi Supreme", 
                "Taco Time", "Pasta Paradise"
            ]
            
            for restaurant in restaurants:
                rest_frame = tk.Frame(
                    content_frame,
                    bg=self.color_bg,
                    highlightbackground=self.color_border,
                    highlightthickness=1,
                    padx=10,
                    pady=10
                )
                rest_frame.pack(fill=tk.X, pady=5)
                
                rest_name = tk.Label(
                    rest_frame,
                    text=restaurant,
                    font=self.font_small_bold,
                    bg=self.color_bg,
                    anchor=tk.W
                )
                rest_name.pack(anchor=tk.W)
                
                rest_details = tk.Label(
                    rest_frame,
                    text=f"⭐ 4.{random.randint(1, 9)} • {random.randint(15, 45)} min • ${random.randint(0, 3)}.99 delivery",
                    font=self.font_xs,
                    fg=self.color_gray_text,
                    bg=self.color_bg,
                    anchor=tk.W
                )
                rest_details.pack(anchor=tk.W)
                
                # Make clickable
                rest_frame.bind("<Button-1>", lambda e, r=restaurant: self.select_restaurant_from_list(r))
                rest_name.bind("<Button-1>", lambda e, r=restaurant: self.select_restaurant_from_list(r))
                rest_details.bind("<Button-1>", lambda e, r=restaurant: self.select_restaurant_from_list(r))
                
                # Add hover effect
                def on_enter(e, frame=rest_frame):
                    frame.config(bg=self.color_light_gray)
                    for widget in frame.winfo_children():
                        widget.config(bg=self.color_light_gray)
                
                def on_leave(e, frame=rest_frame):
                    frame.config(bg=self.color_bg)
                    for widget in frame.winfo_children():
                        widget.config(bg=self.color_bg)
                
                rest_frame.bind("<Enter>", on_enter)
                rest_frame.bind("<Leave>", on_leave)
                rest_name.bind("<Enter>", on_enter)
                rest_name.bind("<Leave>", on_leave)
                rest_details.bind("<Enter>", on_enter)
                rest_details.bind("<Leave>", on_leave)
            
            # Voice assistant button
            voice_button = tk.Button(
                content_frame,
                text="🎤 Voice Search",
                font=self.font_small_bold,
                bg=self.color_dark_bg,
                fg=self.color_light_text,
                padx=15,
                pady=8,
                bd=0,
                relief=tk.FLAT,
                command=self.use_voice_input
            )
            voice_button.pack(fill=tk.X, pady=(20, 10), side=tk.BOTTOM)
            
            # Speak guidance
            self.speak("Browse restaurants by category or search for your favorite food. You can also ask me for personalized recommendations.")
            
        except Exception as e:
            print(f"Error showing order screen: {e}")
            print(traceback.format_exc())
            self.show_simple_screen("Order Food", "Browse restaurants and place your order")
    
    def select_restaurant_from_list(self, restaurant):
        """Handle restaurant selection from list"""
        # For demo purposes, let's just show a fake menu
        self.show_menu_selection(restaurant, "Selected")
    
    def show_food_recommendations(self):
        """Show AI-powered food recommendations dialog"""
        print("Showing food recommendations")
        try:
            # Create a dialog window
            recommend_window = tk.Toplevel(self.root)
            recommend_window.title("Food Recommendations")
            recommend_window.geometry("350x450")
            recommend_window.configure(bg=self.color_bg)
            
            # Add a title
            title_label = tk.Label(
                recommend_window, 
                text="AI Food Recommendations", 
                font=self.font_medium_bold,
                bg=self.color_bg
            )
            title_label.pack(pady=(15, 10))
            
            # Question label
            question_label = tk.Label(
                recommend_window,
                text="What are you in the mood for?",
                font=self.font_small,
                bg=self.color_bg
            )
            question_label.pack(pady=(0, 15))
            
            # Option buttons
            options = [
                "Something healthy", 
                "Comfort food", 
                "Quick meal", 
                "Local specialties",
                "Surprise me!"
            ]
            
            for option in options:
                option_button = tk.Button(
                    recommend_window,
                    text=option,
                    font=self.font_small,
                    bg=self.color_light_gray,
                    padx=15,
                    pady=5,
                    bd=0,
                    relief=tk.FLAT,
                    command=lambda o=option: show_recommendations(o)
                )
                option_button.pack(fill=tk.X, padx=20, pady=5)
            
            # Custom preference frame
            custom_frame = tk.Frame(recommend_window, bg=self.color_bg, padx=20, pady=10)
            custom_frame.pack(fill=tk.X)
            
            custom_entry = tk.Entry(
                custom_frame,
                font=self.font_small,
                bd=1,
                relief=tk.SOLID
            )
            custom_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5)
            custom_entry.insert(0, "Custom preference...")
            
            def on_entry_click(event):
                if custom_entry.get() == "Custom preference...":
                    custom_entry.delete(0, tk.END)
                    custom_entry.config(fg="black")
                    
            def on_focus_out(event):
                if custom_entry.get() == "":
                    custom_entry.insert(0, "Custom preference...")
                    custom_entry.config(fg="gray")
                    
            custom_entry.bind("<FocusIn>", on_entry_click)
            custom_entry.bind("<FocusOut>", on_focus_out)
            custom_entry.config(fg="gray")
            
            custom_button = tk.Button(
                custom_frame,
                text="Go",
                font=self.font_small_bold,
                bg=self.color_primary,
                fg=self.color_light_text,
                padx=10,
                pady=5,
                bd=0,
                relief=tk.FLAT,
                command=lambda: show_recommendations(custom_entry.get() if custom_entry.get() != "Custom preference..." else "Something tasty")
            )
            custom_button.pack(side=tk.RIGHT, padx=(10, 0))
            
            # Result text area
            result_text = Text(
                recommend_window,
                wrap=tk.WORD,
                width=40,
                height=8,
                font=self.font_small,
                padx=10,
                pady=10,
                bg=self.color_light_gray,
                relief=tk.FLAT,
                state="disabled"
            )
            result_text.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
            
            # Close button
            close_button = tk.Button(
                recommend_window,
                text="Close",
                font=self.font_small,
                bg=self.color_light_gray,
                padx=15,
                pady=5,
                bd=0,
                relief=tk.FLAT,
                command=recommend_window.destroy
            )
            close_button.pack(pady=(0, 15))
            
            # Function to show recommendations
            def show_recommendations(preference):
                # Show loading message
                result_text.config(state="normal")
                result_text.delete("1.0", tk.END)
                result_text.insert("1.0", "Thinking of recommendations based on your preference...")
                result_text.config(state="disabled")
                result_text.update_idletasks()
                
                # Get recommendations
                def get_recommendations():
                    try:
                        if HAS_OLLAMA and self.ollama:
                            prompt = f"I'm looking for {preference} from Uber Eats. Can you suggest 2-3 specific dishes or restaurants that would be good, with a brief explanation why? Keep it conversational and under 100 words."
                            recommendations = self.generate_ollama_response(prompt, include_context=False)
                        else:
                            recommendations = f"Based on your preference for {preference}, I would recommend:\n\n" + \
                                            f"1. {random.choice(['Pizza Palace', 'Burger Bistro', 'Sushi Supreme'])}: Their specialties are perfect when you're looking for {preference.lower()}.\n\n" + \
                                            f"2. {random.choice(['Taco Time', 'Pasta Paradise', 'Green Garden'])}: Great options that match your mood for {preference.lower()}."
                        
                        # Update the result text
                        result_text.config(state="normal")
                        result_text.delete("1.0", tk.END)
                        result_text.insert("1.0", recommendations)
                        result_text.config(state="disabled")
                        
                        # Speak the recommendations
                        self.speak(recommendations)
                        
                    except Exception as e:
                        print(f"Error getting recommendations: {e}")
                        result_text.config(state="normal")
                        result_text.delete("1.0", tk.END)
                        result_text.insert("1.0", "Sorry, I couldn't generate recommendations right now. Please try again later.")
                        result_text.config(state="disabled")
                
                threading.Thread(target=get_recommendations).start()
                
        except Exception as e:
            print(f"Error showing food recommendations: {e}")
            print(traceback.format_exc())
            messagebox.showinfo("Food Recommendations", "Food recommendations would appear here in the full version")
    
    def show_tracking_screen(self):
        """Show tracking screen"""
        print("Showing tracking screen")
        try:
            # Clear existing widgets
            for widget in self.root.winfo_children():
                widget.destroy()
            
            self.current_screen = "tracking"
            
            # Create header with back button
            self.create_header("Track Your Delivery", self.create_main_screen)
            
            # Main content frame
            content_frame = tk.Frame(self.root, bg=self.color_bg, padx=20, pady=10)
            content_frame.pack(fill=tk.BOTH, expand=True)
            
            # Active order (mock data)
            if self.user_info["recent_orders"] and any(order["status"] == "In Progress" for order in self.user_info["recent_orders"]):
                active_order = next((order for order in self.user_info["recent_orders"] if order["status"] == "In Progress"), None)
                
                if active_order:
                    self.create_active_order_display(content_frame, active_order)
                    
                    # Add AI delivery insights button
                    insights_button = tk.Button(
                        content_frame,
                        text="🧠 Get AI Delivery Insights",
                        font=self.font_small_bold,
                        bg=self.color_primary,
                        fg=self.color_light_text,
                        padx=15,
                        pady=8,
                        bd=0,
                        relief=tk.FLAT,
                        command=lambda o=active_order: self.show_delivery_insights(o)
                    )
                    insights_button.pack(fill=tk.X, pady=10)
            else:
                # No active orders
                no_orders_frame = tk.Frame(content_frame, bg=self.color_bg, pady=50)
                no_orders_frame.pack(fill=tk.BOTH, expand=True)
                
                no_orders_label = tk.Label(
                    no_orders_frame,
                    text="No active deliveries",
                    font=self.font_medium_bold,
                    bg=self.color_bg
                )
                no_orders_label.pack()
                
                no_orders_desc = tk.Label(
                    no_orders_frame,
                    text="Your ordered food will appear here",
                    font=self.font_small,
                    fg=self.color_gray_text,
                    bg=self.color_bg
                )
                no_orders_desc.pack(pady=10)
                
                order_button = tk.Button(
                    no_orders_frame,
                    text="Order Food Now",
                    font=self.font_small_bold,
                    bg=self.color_primary,
                    fg=self.color_light_text,
                    padx=20,
                    pady=10,
                    bd=0,
                    relief=tk.FLAT,
                    command=self.show_order_screen
                )
                order_button.pack(pady=20)
            
            # Voice assistant button
            voice_button = tk.Button(
                content_frame,
                text="🎤 Voice Assistant",
                font=self.font_small_bold,
                bg=self.color_dark_bg,
                fg=self.color_light_text,
                padx=15,
                pady=8,
                bd=0,
                relief=tk.FLAT,
                command=self.toggle_voice_recognition
            )
            voice_button.pack(fill=tk.X, pady=(20, 10), side=tk.BOTTOM)
            
            # Speak the status
            if self.user_info["recent_orders"] and any(order["status"] == "In Progress" for order in self.user_info["recent_orders"]):
                active_order = next((order for order in self.user_info["recent_orders"] if order["status"] == "In Progress"), None)
                self.speak(f"Your order from {active_order['restaurant']} is on the way. You can ask for AI insights about your delivery.")
            else:
                self.speak("You don't have any active deliveries right now. Would you like to place a new order?")
                
        except Exception as e:
            print(f"Error showing tracking screen: {e}")
            print(traceback.format_exc())
            self.show_simple_screen("Track Order", "See your active deliveries and estimated arrival times")
    
    def create_active_order_display(self, parent, order):
        """Display active order status"""
        try:
            # Order status container
            status_frame = tk.Frame(parent, bg=self.color_bg, pady=20)
            status_frame.pack(fill=tk.X)
            
            # Restaurant name
            restaurant_label = tk.Label(
                status_frame,
                text=order["restaurant"],
                font=self.font_medium_bold,
                bg=self.color_bg,
                anchor=tk.W
            )
            restaurant_label.pack(anchor=tk.W)
            
            # Order items
            items_text = ", ".join(order["items"])
            items_label = tk.Label(
                status_frame,
                text=items_text,
                font=self.font_small,
                bg=self.color_bg,
                anchor=tk.W,
                wraplength=350,
                justify=tk.LEFT
            )
            items_label.pack(anchor=tk.W, pady=(5, 10))
            
            # Status progress bar
            progress_frame = tk.Frame(status_frame, bg=self.color_bg, pady=10)
            progress_frame.pack(fill=tk.X)
            
            progress_bar = ttk.Progressbar(
                progress_frame,
                style="Custom.TProgressbar",
                orient=tk.HORIZONTAL,
                length=350,
                mode='determinate'
            )
            progress_bar.pack(fill=tk.X)
            progress_bar['value'] = 65  # Simulated progress
            
            # Status steps
            steps_frame = tk.Frame(status_frame, bg=self.color_bg, pady=10)
            steps_frame.pack(fill=tk.X)
            
            steps = ["Order Received", "Preparing", "On the way", "Delivered"]
            for i, step in enumerate(steps):
                step_frame = tk.Frame(steps_frame, bg=self.color_bg)
                step_frame.grid(row=0, column=i, padx=(0, 40) if i < 3 else 0)
                
                # Determine if this step is completed
                completed = i <= int(progress_bar['value'] / 33)
                
                step_circle = tk.Canvas(
                    step_frame, 
                    width=20, 
                    height=20, 
                    bg=self.color_bg, 
                    highlightthickness=0
                )
                step_circle.pack()
                
                if completed:
                    step_circle.create_oval(2, 2, 18, 18, fill=self.color_primary, outline=self.color_primary)
                    step_circle.create_text(10, 10, text="✓", fill=self.color_light_text, font=(self.theme.font_family, 8, "bold"))
                else:
                    step_circle.create_oval(2, 2, 18, 18, fill=self.color_bg, outline=self.color_border)
                
                step_label = tk.Label(
                    step_frame,
                    text=step,
                    font=self.font_xs,
                    fg=self.color_dark_text if completed else self.color_gray_text,
                    bg=self.color_bg
                )
                step_label.pack(pady=(5, 0))
            
            # ETA section
            eta_frame = tk.Frame(parent, bg=self.color_bg, pady=20)
            eta_frame.pack(fill=tk.X)
            
            eta_label = tk.Label(
                eta_frame,
                text="Estimated Delivery",
                font=self.font_medium_bold,
                bg=self.color_bg,
                anchor=tk.W
            )
            eta_label.pack(anchor=tk.W)
            
            # Generate a random time 10-30 minutes from now
            now = datetime.now()
            delivery_time = now + timedelta(minutes=random.randint(10, 30))
            eta_time = delivery_time.strftime("%I:%M %p")
            
            time_label = tk.Label(
                eta_frame,
                text=eta_time,
                font=self.font_large_bold,
                bg=self.color_bg,
                anchor=tk.W
            )
            time_label.pack(anchor=tk.W)
            
            # Driver info (mock)
            driver_frame = tk.Frame(
                parent,
                bg=self.color_bg,
                highlightbackground=self.color_border,
                highlightthickness=1,
                padx=15,
                pady=15
            )
            driver_frame.pack(fill=tk.X)
            
            driver_name = random.choice(["Michael", "Sarah", "David", "Emma", "James"])
            
            driver_header = tk.Label(
                driver_frame,
                text="Your Delivery Person",
                font=self.font_small_bold,
                bg=self.color_bg,
                anchor=tk.W
            )
            driver_header.pack(anchor=tk.W)
            
            driver_label = tk.Label(
                driver_frame,
                text=f"👤 {driver_name}",
                font=self.font_medium,
                bg=self.color_bg,
                anchor=tk.W
            )
            driver_label.pack(anchor=tk.W, pady=(5, 10))
            
            # Contact button
            contact_button = tk.Button(
                driver_frame,
                text="Contact Driver",
                font=self.font_small,
                bg=self.color_light_gray,
                padx=15,
                pady=5,
                bd=0,
                relief=tk.FLAT
            )
            contact_button.pack(anchor=tk.W)
            
        except Exception as e:
            print(f"Error creating active order display: {e}")
            print(traceback.format_exc())
            # Create a simple fallback
            fallback_label = tk.Label(
                parent,
                text=f"Your order from {order['restaurant']} is on the way!",
                font=self.font_medium_bold,
                bg=self.color_bg
            )
            fallback_label.pack(pady=20)
    
    # Finishing the show_delivery_insights method first (it was cut off)
    def show_delivery_insights(self, order):
        """Show AI-powered insights about the delivery"""
        print("Showing delivery insights")
        try:
            # Create a toplevel window
            insights_window = tk.Toplevel(self.root)
            insights_window.title("Delivery Insights")
            insights_window.geometry("350x450")
            insights_window.configure(bg=self.color_bg)
            
            # Add a title
            title_label = tk.Label(
                insights_window, 
                text="AI Delivery Insights", 
                font=self.font_medium_bold,
                bg=self.color_bg
            )
            title_label.pack(pady=(15, 10))
            
            # Order details summary
            order_label = tk.Label(
                insights_window,
                text=f"Order from {order['restaurant']}",
                font=self.font_medium_bold,
                bg=self.color_bg
            )
            order_label.pack(pady=(0, 5))
            
            items_text = ", ".join(order["items"])
            items_label = tk.Label(
                insights_window,
                text=items_text,
                font=self.font_small,
                bg=self.color_bg,
                wraplength=300
            )
            items_label.pack(pady=(0, 15))
            
            # Loading indicator
            loading_frame = tk.Frame(insights_window, bg=self.color_bg)
            loading_frame.pack(fill=tk.X)
            
            loading_label = tk.Label(
                loading_frame,
                text="Generating insights...",
                font=self.font_xs,
                fg=self.color_gray_text,
                bg=self.color_bg
            )
            loading_label.pack(pady=(0, 10))
            
            # Progress bar
            progress = ttk.Progressbar(
                loading_frame, 
                style="Custom.TProgressbar",
                orient="horizontal",
                length=300, 
                mode="indeterminate"
            )
            progress.pack(pady=(0, 20))
            progress.start()
            
            # Insights text area (will be populated later)
            insights_text = Text(
                insights_window,
                wrap=tk.WORD,
                width=40,
                height=12,
                font=self.font_small,
                padx=15,
                pady=15,
                bg=self.color_light_gray,
                relief=tk.FLAT,
                state="disabled"
            )
            
            # Close button
            close_button = tk.Button(
                insights_window,
                text="Close",
                font=self.font_small,
                bg=self.color_light_gray,
                padx=15,
                pady=5,
                bd=0,
                relief=tk.FLAT,
                command=insights_window.destroy
            )
            close_button.pack(pady=(10, 15), side=tk.BOTTOM)
            
            # Generate and display insights
            def generate_insights():
                try:
                    now = datetime.now()
                    delivery_time = now + timedelta(minutes=random.randint(10, 30))
                    eta_time = delivery_time.strftime("%I:%M %p")
                    
                    if HAS_OLLAMA and self.ollama:
                        # Create a prompt for the LLM
                        prompt = f"""I have an Uber Eats order from {order['restaurant']} with items: {items_text}. 
                        It's estimated to arrive at {eta_time}. 
                        Can you provide helpful insights about my delivery, such as:
                        1. Optimal food temperature and freshness expectations
                        2. Any preparation I should do before it arrives
                        3. Estimated delivery timing factors
                        4. A fun fact about this type of food
                        
                        Keep the response conversational and helpful, around 150 words."""
                        
                        # Get insights from LLM
                        insights = self.generate_ollama_response(prompt, include_context=False)
                    else:
                        # Fallback insights if Ollama is not available
                        insights = f"""Your order from {order['restaurant']} is on track to be delivered around {eta_time}.
                        
                        For optimal enjoyment:
                        • Your food should still be at a good temperature when it arrives
                        • Consider setting up your dining area before the delivery arrives
                        • Traffic conditions are normal in your area, so your delivery should arrive on time
                        
                        Fun fact: Did you know that {order['items'][0] if order['items'] else 'this type of food'} is one of the most popular delivery items in the country?
                        
                        Enjoy your meal!"""
                    
                    # Update UI with insights
                    loading_frame.pack_forget()
                    
                    insights_text.config(state="normal")
                    insights_text.insert("1.0", insights)
                    insights_text.config(state="disabled")
                    insights_text.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 15))
                    
                    # Speak the insights
                    self.speak(insights)
                    
                except Exception as e:
                    print(f"Error generating insights: {e}")
                    print(traceback.format_exc())
                    
                    # Show error and fallback insights
                    loading_frame.pack_forget()
                    
                    fallback_insights = f"""Your order from {order['restaurant']} is on the way and should arrive soon.
                    
                    The food should still be at a good temperature upon arrival. Consider having your table set up so you can enjoy it immediately.
                    
                    Traffic conditions are normal in your area, so delivery should be on time. Your driver is doing their best to get your food to you quickly!
                    
                    Enjoy your meal!"""
                    
                    insights_text.config(state="normal")
                    insights_text.insert("1.0", fallback_insights)
                    insights_text.config(state="disabled")
                    insights_text.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 15))
                    
                    # Speak the fallback insights
                    self.speak(fallback_insights)
            
            # Run in a separate thread to prevent UI freezing
            threading.Thread(target=generate_insights).start()
            
        except Exception as e:
            print(f"Error showing delivery insights: {e}")
            print(traceback.format_exc())
            messagebox.showinfo("Delivery Insights", "Delivery insights would appear here in the full version")
    
    def show_past_orders(self):
        """Show past orders screen"""
        print("Showing past orders screen")
        try:
            # Clear existing widgets
            for widget in self.root.winfo_children():
                widget.destroy()
            
            self.current_screen = "past_orders"
            
            # Create header with back button
            self.create_header("Order History", self.create_main_screen)
            
            # Main content frame
            content_frame = tk.Frame(self.root, bg=self.color_bg, padx=20, pady=10)
            content_frame.pack(fill=tk.BOTH, expand=True)
            
            # Check if there are any past orders
            if not self.user_info["recent_orders"]:
                # No orders message
                no_orders_frame = tk.Frame(content_frame, bg=self.color_bg, pady=50)
                no_orders_frame.pack(fill=tk.BOTH, expand=True)
                
                no_orders_label = tk.Label(
                    no_orders_frame,
                    text="No past orders",
                    font=self.font_medium_bold,
                    bg=self.color_bg
                )
                no_orders_label.pack()
                
                no_orders_desc = tk.Label(
                    no_orders_frame,
                    text="You haven't placed any orders yet",
                    font=self.font_small,
                    fg=self.color_gray_text,
                    bg=self.color_bg
                )
                no_orders_desc.pack(pady=10)
                
                order_button = tk.Button(
                    no_orders_frame,
                    text="Order Food Now",
                    font=self.font_small_bold,
                    bg=self.color_primary,
                    fg=self.color_light_text,
                    padx=20,
                    pady=10,
                    bd=0,
                    relief=tk.FLAT,
                    command=self.show_order_screen
                )
                order_button.pack(pady=20)
            else:
                # Title
                history_label = tk.Label(
                    content_frame,
                    text="Your Order History",
                    font=self.font_medium_bold,
                    bg=self.color_bg
                )
                history_label.pack(pady=(0, 15))
                
                # Create scrollable canvas for order history
                canvas_frame = tk.Frame(content_frame, bg=self.color_bg)
                canvas_frame.pack(fill=tk.BOTH, expand=True)
                
                canvas = tk.Canvas(canvas_frame, bg=self.color_bg, highlightthickness=0)
                scrollbar = tk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
                
                scroll_frame = tk.Frame(canvas, bg=self.color_bg)
                
                # Configure the canvas
                canvas.configure(yscrollcommand=scrollbar.set)
                canvas.pack(side="left", fill="both", expand=True)
                scrollbar.pack(side="right", fill="y")
                
                # Create a window in the canvas to hold the scrollable frame
                canvas.create_window((0, 0), window=scroll_frame, anchor="nw", width=canvas.winfo_reqwidth())
                
                # Add each order
                for i, order in enumerate(self.user_info["recent_orders"]):
                    # Order container
                    order_frame = tk.Frame(
                        scroll_frame,
                        bg=self.color_bg,
                        highlightbackground=self.color_border,
                        highlightthickness=1,
                        padx=15,
                        pady=15
                    )
                    order_frame.pack(fill=tk.X, pady=8)
                    
                    # Restaurant and date
                    header_frame = tk.Frame(order_frame, bg=self.color_bg)
                    header_frame.pack(fill=tk.X)
                    
                    restaurant_label = tk.Label(
                        header_frame,
                        text=order["restaurant"],
                        font=self.font_small_bold,
                        bg=self.color_bg,
                        anchor=tk.W
                    )
                    restaurant_label.pack(side=tk.LEFT)
                    
                    date_label = tk.Label(
                        header_frame,
                        text=order["date"],
                        font=self.font_xs,
                        fg=self.color_gray_text,
                        bg=self.color_bg,
                        anchor=tk.E
                    )
                    date_label.pack(side=tk.RIGHT)
                    
                    # Status
                    status_label = tk.Label(
                        order_frame,
                        text=f"Status: {order['status']}",
                        font=self.font_xs,
                        fg="#06C167" if order["status"] == "Delivered" else 
                           "#FF3B30" if order["status"] == "Cancelled" else "#FF9500",
                        bg=self.color_bg,
                        anchor=tk.W
                    )
                    status_label.pack(anchor=tk.W, pady=(5, 5))
                    
                    # Items
                    items_text = ", ".join(order["items"])
                    items_label = tk.Label(
                        order_frame,
                        text=f"Items: {items_text}",
                        font=self.font_small,
                        bg=self.color_bg,
                        anchor=tk.W,
                        wraplength=300,
                        justify=tk.LEFT
                    )
                    items_label.pack(anchor=tk.W, pady=(0, 5))
                    
                    # Total
                    total_label = tk.Label(
                        order_frame,
                        text=f"Total: ${order['total']:.2f}",
                        font=self.font_small,
                        bg=self.color_bg,
                        anchor=tk.W
                    )
                    total_label.pack(anchor=tk.W)
                    
                    # Reorder button (if delivered)
                    if order["status"] == "Delivered":
                        reorder_button = tk.Button(
                            order_frame,
                            text="Reorder",
                            font=self.font_small,
                            bg=self.color_primary,
                            fg=self.color_light_text,
                            padx=10,
                            pady=5,
                            bd=0,
                            relief=tk.FLAT,
                            command=lambda r=order["restaurant"], i=order["items"]: self.show_order_summary(r, i)
                        )
                        reorder_button.pack(anchor=tk.E, pady=(10, 0))
                
                # Update scroll region when frame size changes
                def on_frame_configure(event):
                    canvas.configure(scrollregion=canvas.bbox("all"))
                
                scroll_frame.bind("<Configure>", on_frame_configure)
            
            # Add AI order analysis button
            if self.user_info["recent_orders"]:
                ai_analysis_button = tk.Button(
                    content_frame,
                    text="🧠 Get AI Order Analysis",
                    font=self.font_small_bold,
                    bg=self.color_primary,
                    fg=self.color_light_text,
                    padx=15,
                    pady=8,
                    bd=0,
                    relief=tk.FLAT,
                    command=self.show_order_analysis
                )
                ai_analysis_button.pack(fill=tk.X, pady=(20, 10), side=tk.BOTTOM)
            
            # Speak the status
            if self.user_info["recent_orders"]:
                self.speak(f"You have {len(self.user_info['recent_orders'])} orders in your history. You can view details or get AI analysis of your ordering patterns.")
            else:
                self.speak("You don't have any order history yet. Would you like to place your first order?")
            
        except Exception as e:
            print(f"Error showing past orders: {e}")
            print(traceback.format_exc())
            self.show_simple_screen("Order History", "View your past orders and reorder your favorites")
    
    def show_order_analysis(self):
        """Show AI analysis of ordering patterns"""
        print("Showing order analysis")
        try:
            # Create a toplevel window
            analysis_window = tk.Toplevel(self.root)
            analysis_window.title("Order Analysis")
            analysis_window.geometry("350x450")
            analysis_window.configure(bg=self.color_bg)
            
            # Add a title
            title_label = tk.Label(
                analysis_window, 
                text="AI Order Analysis", 
                font=self.font_medium_bold,
                bg=self.color_bg
            )
            title_label.pack(pady=(15, 10))
            
            # Orders summary
            summary_label = tk.Label(
                analysis_window,
                text=f"Based on your {len(self.user_info['recent_orders'])} recent orders",
                font=self.font_small,
                bg=self.color_bg
            )
            summary_label.pack(pady=(0, 15))
            
            # Loading indicator
            loading_frame = tk.Frame(analysis_window, bg=self.color_bg)
            loading_frame.pack(fill=tk.X)
            
            loading_label = tk.Label(
                loading_frame,
                text="Analyzing your orders...",
                font=self.font_xs,
                fg=self.color_gray_text,
                bg=self.color_bg
            )
            loading_label.pack(pady=(0, 10))
            
            # Progress bar
            progress = ttk.Progressbar(
                loading_frame, 
                style="Custom.TProgressbar",
                orient="horizontal",
                length=300, 
                mode="indeterminate"
            )
            progress.pack(pady=(0, 20))
            progress.start()
            
            # Analysis text area (will be populated later)
            analysis_text = Text(
                analysis_window,
                wrap=tk.WORD,
                width=40,
                height=12,
                font=self.font_small,
                padx=15,
                pady=15,
                bg=self.color_light_gray,
                relief=tk.FLAT,
                state="disabled"
            )
            
            # Close button
            close_button = tk.Button(
                analysis_window,
                text="Close",
                font=self.font_small,
                bg=self.color_light_gray,
                padx=15,
                pady=5,
                bd=0,
                relief=tk.FLAT,
                command=analysis_window.destroy
            )
            close_button.pack(pady=(10, 15), side=tk.BOTTOM)
            
            # Generate and display analysis
            def generate_analysis():
                try:
                    # Prepare order data for analysis
                    order_data = {
                        "restaurants": [order["restaurant"] for order in self.user_info["recent_orders"]],
                        "items": [item for order in self.user_info["recent_orders"] for item in order["items"]],
                        "dates": [order["date"] for order in self.user_info["recent_orders"]],
                        "totals": [order["total"] for order in self.user_info["recent_orders"]]
                    }
                    
                    # Get most ordered restaurant
                    from collections import Counter
                    restaurant_counts = Counter(order_data["restaurants"])
                    most_common_restaurant = restaurant_counts.most_common(1)[0][0]
                    
                    # Get most ordered item
                    item_counts = Counter(order_data["items"])
                    most_common_item = item_counts.most_common(1)[0][0]
                    
                    # Calculate average spending
                    avg_total = sum(order_data["totals"]) / len(order_data["totals"])
                    
                    if HAS_OLLAMA and self.ollama:
                        # Create a prompt for the LLM
                        prompt = f"""I've ordered from Uber Eats {len(self.user_info['recent_orders'])} times recently.
                        My most frequent restaurant is {most_common_restaurant}.
                        My most ordered item is {most_common_item}.
                        My average order total is ${avg_total:.2f}.
                        
                        Can you analyze my ordering patterns and provide:
                        1. Insights about my preferences
                        2. Suggestions for what I might enjoy trying
                        3. Any potential money-saving tips
                        
                        Keep the response friendly and conversational, around 150 words."""
                        
                        # Get analysis from LLM
                        analysis = self.generate_ollama_response(prompt, include_context=False)
                    else:
                        # Fallback analysis if Ollama is not available
                        analysis = f"""Based on your order history, here's an analysis of your ordering patterns:

Preferences:
• You order most frequently from {most_common_restaurant}
• Your favorite item is {most_common_item}
• Your average order total is ${avg_total:.2f}

Suggestions:
• Based on your preference for {most_common_restaurant}, you might enjoy trying other similar restaurants
• If you like {most_common_item}, consider trying variations or complementary items
• Look for deals and promotions to save on your favorite orders

Money-saving tips:
• Consider ordering family-size meals for better value
• Watch for restaurant promotions and seasonal specials
• Order during off-peak hours for potential discounts

Enjoy your next Uber Eats order!"""
                    
                    # Update UI with analysis
                    loading_frame.pack_forget()
                    
                    analysis_text.config(state="normal")
                    analysis_text.insert("1.0", analysis)
                    analysis_text.config(state="disabled")
                    analysis_text.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 15))
                    
                    # Speak the analysis
                    self.speak(analysis)
                    
                except Exception as e:
                    print(f"Error generating analysis: {e}")
                    print(traceback.format_exc())
                    
                    # Show error and fallback analysis
                    loading_frame.pack_forget()
                    
                    fallback_analysis = f"""Based on your order history, we can see you enjoy a variety of food types.

Your preferences show that you value convenience and quality in your food orders. Your order history suggests you might enjoy trying new restaurants with similar cuisine styles.

To save money on future orders, look out for special promotions and consider ordering during off-peak hours when delivery fees might be lower.

Thanks for using Uber Eats for your food delivery needs!"""
                    
                    analysis_text.config(state="normal")
                    analysis_text.insert("1.0", fallback_analysis)
                    analysis_text.config(state="disabled")
                    analysis_text.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 15))
                    
                    # Speak the fallback analysis
                    self.speak(fallback_analysis)
            
            # Run in a separate thread to prevent UI freezing
            threading.Thread(target=generate_analysis).start()
            
        except Exception as e:
            print(f"Error showing order analysis: {e}")
            print(traceback.format_exc())
            messagebox.showinfo("Order Analysis", "Order analysis would appear here in the full version")
    
    def show_account_screen(self):
        """Show account screen"""
        print("Showing account screen")
        try:
            # Clear existing widgets
            for widget in self.root.winfo_children():
                widget.destroy()
            
            self.current_screen = "account"
            
            # Create header with back button
            self.create_header("Account", self.create_main_screen)
            
            # Main content frame
            content_frame = tk.Frame(self.root, bg=self.color_bg, padx=20, pady=10)
            content_frame.pack(fill=tk.BOTH, expand=True)
            
            # Profile section
            profile_frame = tk.Frame(content_frame, bg=self.color_bg, pady=15)
            profile_frame.pack(fill=tk.X)
            
            # Avatar placeholder (larger circle)
            avatar_size = 80
            avatar_canvas = tk.Canvas(
                profile_frame, 
                width=avatar_size, 
                height=avatar_size, 
                bg=self.color_bg, 
                highlightthickness=0
            )
            avatar_canvas.pack(side=tk.LEFT, padx=(0, 15))
            
            # Draw circle with initials
            avatar_canvas.create_oval(2, 2, avatar_size-2, avatar_size-2, 
                                    fill=self.color_primary, outline=self.color_primary)
            
            # Add initials
            if self.user_info["name"]:
                initials = "".join([name[0].upper() for name in self.user_info["name"].split()])[:2]
            else:
                initials = "U"
                
            avatar_canvas.create_text(avatar_size//2, avatar_size//2, 
                                    text=initials, 
                                    fill=self.color_light_text, 
                                    font=("Arial", 24, "bold"))
            
            # User info
            info_frame = tk.Frame(profile_frame, bg=self.color_bg)
            info_frame.pack(side=tk.LEFT)
            
            name_label = tk.Label(
                info_frame,
                text=self.user_info["name"] or "User",
                font=self.font_medium_bold,
                bg=self.color_bg,
                anchor=tk.W
            )
            name_label.pack(anchor=tk.W)
            
            phone_label = tk.Label(
                info_frame,
                text=self.user_info["phone"] or "Phone not provided",
                font=self.font_small,
                fg=self.color_gray_text,
                bg=self.color_bg,
                anchor=tk.W
            )
            phone_label.pack(anchor=tk.W)
            
            # Edit profile button
            edit_button = tk.Button(
                content_frame,
                text="Edit Profile",
                font=self.font_small,
                bg=self.color_light_gray,
                padx=15,
                pady=8,
                bd=0,
                relief=tk.FLAT
            )
            edit_button.pack(fill=tk.X, pady=(0, 20))
            
            # Sections separator
            separator = tk.Frame(content_frame, height=1, bg=self.color_border)
            separator.pack(fill=tk.X, pady=15)
            
            # Account sections
            sections = [
                ("📍 Saved Addresses", "Manage your delivery addresses"),
                ("💳 Payment Methods", f"Current: {self.user_info['payment_method']}"),
                ("🔔 Notifications", "Manage your notification preferences"),
                ("⚙️ Account Settings", "Privacy, security, and app settings"),
                ("❓ Help Center", "Get support and answers to your questions")
            ]
            
            for icon_text, description in sections:
                section_frame = tk.Frame(
                    content_frame,
                    bg=self.color_bg,
                    padx=5,
                    pady=12
                )
                section_frame.pack(fill=tk.X)
                
                # Split icon_text into emoji and text
                parts = icon_text.split(" ", 1)
                icon = parts[0]
                text = parts[1] if len(parts) > 1 else ""
                
                icon_label = tk.Label(
                    section_frame,
                    text=icon,
                    font=self.font_medium,
                    bg=self.color_bg
                )
                icon_label.pack(side=tk.LEFT, padx=(0, 10))
                
                text_frame = tk.Frame(section_frame, bg=self.color_bg)
                text_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
                
                title_label = tk.Label(
                    text_frame,
                    text=text,
                    font=self.font_small_bold,
                    bg=self.color_bg,
                    anchor=tk.W
                )
                title_label.pack(anchor=tk.W)
                
                desc_label = tk.Label(
                    text_frame,
                    text=description,
                    font=self.font_xs,
                    fg=self.color_gray_text,
                    bg=self.color_bg,
                    anchor=tk.W
                )
                desc_label.pack(anchor=tk.W)
                
                arrow_label = tk.Label(
                    section_frame,
                    text="→",
                    font=self.font_medium,
                    bg=self.color_bg
                )
                arrow_label.pack(side=tk.RIGHT)
                
                # Add separator except for last item
                if sections.index((icon_text, description)) < len(sections) - 1:
                    item_separator = tk.Frame(content_frame, height=1, bg=self.color_border)
                    item_separator.pack(fill=tk.X)
            
            # Logout button at bottom
            logout_button = tk.Button(
                content_frame,
                text="Log Out",
                font=self.font_small_bold,
                bg=self.color_light_gray,
                padx=15,
                pady=8,
                bd=0,
                relief=tk.FLAT
            )
            logout_button.pack(fill=tk.X, pady=(30, 10), side=tk.BOTTOM)
            
            # Voice assistant button
            voice_button = tk.Button(
                content_frame,
                text="🎤 Voice Assistant",
                font=self.font_small_bold,
                bg=self.color_dark_bg,
                fg=self.color_light_text,
                padx=15,
                pady=8,
                bd=0,
                relief=tk.FLAT,
                command=self.toggle_voice_recognition
            )
            voice_button.pack(fill=tk.X, pady=(0, 10), side=tk.BOTTOM)
            
            # Speak guidance
            self.speak("You're viewing your account profile. Here you can manage your addresses, payment methods, and other account settings.")
            
        except Exception as e:
            print(f"Error showing account screen: {e}")
            print(traceback.format_exc())
            self.show_simple_screen("Account", "Manage your account, addresses, and payment methods")
    
    def show_customer_service(self):
        """Show customer service screen"""
        print("Showing customer service screen")
        try:
            # Clear existing widgets
            for widget in self.root.winfo_children():
                widget.destroy()
            
            self.current_screen = "customer_service"
            
            # Create header with back button
            self.create_header("Customer Service", self.create_main_screen)
            
            # Main content frame
            content_frame = tk.Frame(self.root, bg=self.color_bg, padx=20, pady=10)
            content_frame.pack(fill=tk.BOTH, expand=True)
            
            # Title
            title_label = tk.Label(
                content_frame,
                text="How can we help you?",
                font=self.font_large_bold,
                bg=self.color_bg
            )
            title_label.pack(pady=(0, 20))
            
            # AI assistant option (highlighted)
            ai_frame = tk.Frame(
                content_frame,
                bg=self.color_light_gray,
                highlightbackground=self.color_primary,
                highlightthickness=2,
                padx=15,
                pady=15
            )
            ai_frame.pack(fill=tk.X, pady=(0, 15))
            
            ai_title = tk.Label(
                ai_frame,
                text="🤖 Ask AI Assistant",
                font=self.font_medium_bold,
                bg=self.color_light_gray
            )
            ai_title.pack(anchor=tk.W)
            
            ai_desc = tk.Label(
                ai_frame,
                text="Get instant answers to your questions",
                font=self.font_small,
                bg=self.color_light_gray,
                wraplength=300,
                justify=tk.LEFT
            )
            ai_desc.pack(anchor=tk.W, pady=(5, 10))
            
            ai_button = tk.Button(
                ai_frame,
                text="Ask AI",
                font=self.font_small_bold,
                bg=self.color_primary,
                fg=self.color_light_text,
                padx=15,
                pady=5,
                bd=0,
                relief=tk.FLAT,
                command=self.show_ai_assistant_dialog
            )
            ai_button.pack(anchor=tk.W)
            
            # Support options
            options_label = tk.Label(
                content_frame,
                text="Support Options",
                font=self.font_medium_bold,
                bg=self.color_bg,
                anchor=tk.W
            )
            options_label.pack(anchor=tk.W, pady=(20, 10))
            
            options = [
                ("💬 Live Chat", "Chat with a support agent"),
                ("📞 Phone Support", "Call Uber Eats customer service"),
                ("📧 Email", "Send us an email"),
                ("📝 Report an Issue", "Report a problem with your order or delivery"),
                ("❓ FAQs", "Browse frequently asked questions")
            ]
            
            for icon_text, description in options:
                option_frame = tk.Frame(
                    content_frame,
                    bg=self.color_bg,
                    highlightbackground=self.color_border,
                    highlightthickness=1,
                    padx=15,
                    pady=15
                )
                option_frame.pack(fill=tk.X, pady=8)
                
                # Split icon_text into emoji and text
                parts = icon_text.split(" ", 1)
                icon = parts[0]
                text = parts[1]
                
                icon_label = tk.Label(
                    option_frame,
                    text=icon,
                    font=self.font_medium,
                    bg=self.color_bg
                )
                icon_label.pack(side=tk.LEFT, padx=(0, 10))
                
                text_frame = tk.Frame(option_frame, bg=self.color_bg)
                text_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
                
                title_label = tk.Label(
                    text_frame,
                    text=text,
                    font=self.font_small_bold,
                    bg=self.color_bg,
                    anchor=tk.W
                )
                title_label.pack(anchor=tk.W)
                
                desc_label = tk.Label(
                    text_frame,
                    text=description,
                    font=self.font_xs,
                    fg=self.color_gray_text,
                    bg=self.color_bg,
                    anchor=tk.W
                )
                desc_label.pack(anchor=tk.W)
                
                arrow_label = tk.Label(
                    option_frame,
                    text="→",
                    font=self.font_medium,
                    bg=self.color_bg
                )
                arrow_label.pack(side=tk.RIGHT)
                
                # Make the entire frame clickable
                option_frame.bind("<Button-1>", lambda e: messagebox.showinfo("Support", "This feature would be available in the full version"))
                
                # Add hover effect
                def on_enter(e, frame=option_frame):
                    frame.config(bg=self.color_light_gray)
                    for widget in frame.winfo_children():
                        widget.config(bg=self.color_light_gray)
                    text_frame.config(bg=self.color_light_gray)
                    for widget in text_frame.winfo_children():
                        widget.config(bg=self.color_light_gray)
                
                def on_leave(e, frame=option_frame):
                    frame.config(bg=self.color_bg)
                    for widget in frame.winfo_children():
                        widget.config(bg=self.color_bg)
                    text_frame.config(bg=self.color_bg)
                    for widget in text_frame.winfo_children():
                        widget.config(bg=self.color_bg)
                
                option_frame.bind("<Enter>", on_enter)
                option_frame.bind("<Leave>", on_leave)
            
            # Speak guidance
            self.speak("You can get help from our AI assistant for instant answers, or choose from other support options like live chat or phone support.")
            
        except Exception as e:
            print(f"Error showing customer service screen: {e}")
            print(traceback.format_exc())
            self.show_simple_screen("Customer Service", "Get help with your orders and account")
    
    def show_ai_assistant_dialog(self):
        """Show AI assistant dialog with simplified implementation"""
        print("Showing AI assistant dialog")
        try:
            # Create a translucent overlay
            overlay = tk.Toplevel(self.root)
            
            # Position it over the main window
            overlay.geometry(f"{self.root.winfo_width()}x{self.root.winfo_height()}+{self.root.winfo_x()}+{self.root.winfo_y()}")
            overlay.overrideredirect(True)  # Remove window decorations
            overlay.configure(bg="#000000")
            overlay.attributes("-alpha", 0.7)  # Semi-transparent overlay
            
            # Create assistant frame
            assistant_frame = tk.Frame(
                overlay, 
                bg=self.color_bg,
                padx=20, 
                pady=20
            )
            assistant_frame.place(relx=0.5, rely=0.5, anchor="center", width=350, height=500)
            
            # Add a title
            title_label = tk.Label(
                assistant_frame, 
                text="Ask Me Anything", 
                font=self.font_medium_bold,
                bg=self.color_bg
            )
            title_label.pack(pady=(0, 10))
            
            # Create a chat display area
            chat_frame = tk.Frame(assistant_frame, bg=self.color_bg)
            chat_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
            
            chat_display = Text(
                chat_frame,
                wrap=tk.WORD,
                width=35,
                height=15,
                font=self.font_small,
                padx=10,
                pady=10,
                bg=self.color_light_gray
            )
            chat_display.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            chat_display.insert("1.0", "Hi! I'm your Uber Eats AI assistant. You can ask me about food recommendations, delivery times, or anything related to Uber Eats. What can I help you with today?\n\n")
            chat_display.config(state="disabled")  # Make read-only
            
            # Add scrollbar
            chat_scrollbar = Scrollbar(chat_frame, command=chat_display.yview)
            chat_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            chat_display.config(yscrollcommand=chat_scrollbar.set)
            
            # User input field
            input_frame = tk.Frame(assistant_frame, bg=self.color_bg)
            input_frame.pack(fill=tk.X, pady=(0, 10))
            
            user_input = tk.Entry(
                input_frame,
                font=self.font_small,
                bd=1,
                relief=tk.SOLID
            )
            user_input.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=8)
            user_input.focus_set()
            
            # Function to handle user input
            def process_input(event=None):
                query = user_input.get().strip()
                if not query:
                    return
                    
                # Add user query to display
                chat_display.config(state="normal")
                chat_display.insert(tk.END, f"You: {query}\n\n")
                user_input.delete(0, tk.END)
                
                # Add thinking indicator
                chat_display.insert(tk.END, "Assistant: thinking...\n")
                chat_display.see(tk.END)
                chat_display.update_idletasks()
                
                # Process with LLM or fallback
                def get_response():
                    try:
                        if HAS_OLLAMA and self.ollama:
                            response = self.generate_ollama_response(query, include_context=True)
                        else:
                            response = self.get_fallback_response(query)
                        
                        # Update display with response
                        chat_display.config(state="normal")
                        # Remove thinking indicator
                        chat_display.delete("end-1l linestart", "end-1l lineend+1c")
                        chat_display.insert(tk.END, f"Assistant: {response}\n\n")
                        chat_display.see(tk.END)
                        chat_display.config(state="disabled")
                        
                        # Speak the response
                        self.speak(response)
                        
                    except Exception as e:
                        print(f"Error getting response: {e}")
                        print(traceback.format_exc())
                        
                        chat_display.config(state="normal")
                        # Remove thinking indicator
                        chat_display.delete("end-1l linestart", "end-1l lineend+1c")
                        chat_display.insert(tk.END, "Assistant: Sorry, I'm having trouble generating a response right now. Can you try asking something else?\n\n")
                        chat_display.see(tk.END)
                        chat_display.config(state="disabled")
                
                threading.Thread(target=get_response).start()
                
            # Send button
            send_button = tk.Button(
                input_frame,
                text="Send",
                font=self.font_small_bold,
                bg=self.color_primary,
                fg=self.color_light_text,
                padx=10,
                pady=5,
                bd=0,
                relief=tk.FLAT,
                command=process_input
            )
            send_button.pack(side=tk.RIGHT, padx=(10, 0))
            
            # Bind Enter key to send
            user_input.bind("<Return>", process_input)
            
            # Voice input button (only if speech recognition is available)
            if HAS_SR and self.recognizer and self.microphone:
                voice_button = tk.Button(
                    input_frame,
                    text="🎤",
                    font=self.font_small_bold,
                    bg=self.color_dark_bg,
                    fg=self.color_light_text,
                    padx=10,
                    pady=5,
                    bd=0,
                    relief=tk.FLAT,
                    command=lambda: self.assistant_voice_input(user_input, process_input)
                )
                voice_button.pack(side=tk.RIGHT, padx=(10, 0))
            
            # Close button
            close_button = tk.Button(
                assistant_frame,
                text="Close",
                font=self.font_small,
                bg=self.color_light_gray,
                padx=15,
                pady=5,
                bd=0,
                relief=tk.FLAT,
                command=overlay.destroy
            )
            close_button.pack(pady=(10, 0))
            
            # Speak greeting
            self.speak("Hi! I'm your Uber Eats AI assistant. What can I help you with today?")
        except Exception as e:
            print(f"Error showing AI assistant dialog: {e}")
            print(traceback.format_exc())
            messagebox.showinfo("AI Assistant", "The AI assistant dialog would appear here in the full version")
            
    def assistant_voice_input(self, entry_widget, submit_func):
        """Handle voice input with proper error handling"""
        if not HAS_SR or not self.recognizer or not self.microphone:
            messagebox.showinfo("Voice Recognition Unavailable", 
                              "Voice recognition is not available. Please install the speech_recognition package.")
            return
            
        try:
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, "🎤 Listening...")
            entry_widget.config(state="disabled")
            
            def listen():
                try:
                    with self.microphone as source:
                        audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=5)
                    
                    text = self.recognizer.recognize_google(audio)
                    
                    # Update entry widget with recognized text
                    entry_widget.config(state="normal")
                    entry_widget.delete(0, tk.END)
                    entry_widget.insert(0, text)
                    
                    # Submit the text
                    submit_func()
                    
                except Exception as e:
                    print(f"Voice recognition error: {e}")
                    entry_widget.config(state="normal")
                    entry_widget.delete(0, tk.END)
                    
            threading.Thread(target=listen).start()
        except Exception as e:
            print(f"Error in voice input: {e}")
            entry_widget.config(state="normal")
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, "Voice input error")
    
    def create_header(self, title, back_command):
        """Create a styled header with back button"""
        try:
            header_frame = tk.Frame(
                self.root, 
                bg=self.color_bg,
                highlightbackground=self.color_border,
                highlightthickness=1,
                padx=15, 
                pady=15
            )
            header_frame.pack(fill=tk.X)
            
            back_button = tk.Button(
                header_frame,
                text="←",
                font=self.font_medium_bold,
                bg=self.color_bg,
                fg=self.color_dark_text,
                padx=5,
                pady=0,
                bd=0,
                relief=tk.FLAT,
                command=back_command
            )
            back_button.pack(side=tk.LEFT)
            
            title_label = tk.Label(
                header_frame,
                text=title,
                font=self.font_medium_bold,
                bg=self.color_bg,
                fg=self.color_dark_text
            )
            title_label.pack(side=tk.LEFT, padx=15)
        except Exception as e:
            print(f"Error creating header: {e}")
            # Create simpler fallback header
            header_frame = tk.Frame(self.root, bg="#ffffff", padx=15, pady=15)
            header_frame.pack(fill=tk.X)
            
            back_button = tk.Button(
                header_frame,
                text="Back",
                command=back_command
            )
            back_button.pack(side=tk.LEFT)
            
            title_label = tk.Label(
                header_frame,
                text=title,
                font=("Arial", 14, "bold"),
                bg="#ffffff"
            )
            title_label.pack(side=tk.LEFT, padx=15)
    
    def show_simple_screen(self, title, description):
        """Show a simple screen with title and description"""
        try:
            # Clear existing widgets
            for widget in self.root.winfo_children():
                widget.destroy()
            
            # Create header with back button
            self.create_header(title, self.create_main_screen)
            
            # Main content frame
            content_frame = tk.Frame(self.root, bg=self.color_bg, padx=20, pady=50)
            content_frame.pack(fill=tk.BOTH, expand=True)
            
            # Title
            title_label = tk.Label(
                content_frame,
                text=title,
                font=self.font_large_bold,
                bg=self.color_bg
            )
            title_label.pack(pady=(0, 10))
            
            # Description
            desc_label = tk.Label(
                content_frame,
                text=description,
                font=self.font_medium,
                bg=self.color_bg,
                wraplength=300,
                justify=tk.CENTER
            )
            desc_label.pack(pady=(0, 30))
            
            # Notice
            notice_label = tk.Label(
                content_frame,
                text="This screen would be fully functional in the complete version",
                font=self.font_small,
                fg=self.color_gray_text,
                bg=self.color_bg,
                wraplength=300,
                justify=tk.CENTER
            )
            notice_label.pack(pady=(0, 20))
            
            # Back button
            back_button = tk.Button(
                content_frame,
                text="Back to Home",
                font=self.font_small_bold,
                bg=self.color_primary,
                fg=self.color_light_text,
                padx=20,
                pady=10,
                bd=0,
                relief=tk.FLAT,
                command=self.create_main_screen
            )
            back_button.pack()
        except Exception as e:
            print(f"Error showing simple screen: {e}")
            print(traceback.format_exc())
            # If even the simple screen fails, show a message box
            messagebox.showinfo(title, description)
            self.create_main_screen()
    
    def toggle_voice_recognition(self):
        """Toggle voice recognition on/off with UI updates"""
        # Check if speech recognition is available
        if not HAS_SR or not self.recognizer or not self.microphone:
            messagebox.showinfo("Voice Recognition Unavailable", 
                              "Voice recognition is not available. Please install the speech_recognition package.")
            return
            
        try:
            if self.is_listening:
                self.is_listening = False
                self.status_var.set("Voice assistant ready")
                # We would update the button appearance here
            else:
                self.is_listening = True
                self.status_var.set("Listening... Speak now")
                # We would update the button appearance here
                
                # Visual indicator of listening status
                status_label = tk.Label(
                    self.root,
                    text="🎤 Listening...",
                    font=self.font_small,
                    fg=self.color_primary,
                    bg=self.color_bg,
                    pady=10
                )
                status_label.place(relx=0.5, rely=0.9, anchor="center")
                self.root.after(2000, lambda: status_label.destroy())  # Remove after 2 seconds
                
                # Start listening in a separate thread
                threading.Thread(target=self.listen_for_speech).start()
        except Exception as e:
            print(f"Error toggling voice recognition: {e}")
            messagebox.showinfo("Voice Recognition Error", "There was an error with the voice recognition system.")
    
    def listen_for_speech(self):
        """Continuous speech recognition loop with visual feedback"""
        if not HAS_SR:
            return
            
        import speech_recognition as sr
        
        while self.is_listening:
            try:
                with self.microphone as source:
                    # Visual feedback
                    self.status_var.set("Listening... Speak now")
                    self.root.update_idletasks()
                    
                    # Listen for audio
                    audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=5)
                    
                    # Visual feedback for processing
                    self.status_var.set("Processing speech...")
                    self.root.update_idletasks()
                
                # Recognize speech using Google Speech Recognition
                text = self.recognizer.recognize_google(audio)
                
                # Show what was heard with visual feedback
                self.status_var.set(f"I heard: {text}")
                
                # Display a feedback popup that automatically disappears
                feedback = tk.Label(
                    self.root,
                    text=f"📢 \"{text}\"",
                    font=self.font_small,
                    fg=self.color_dark_text,
                    bg=self.color_light_gray,
                    padx=15,
                    pady=10,
                    borderwidth=1,
                    relief="solid"
                )
                feedback.place(relx=0.5, rely=0.5, anchor="center")
                self.root.after(2000, feedback.destroy)  # Remove after 2 seconds
                
                # Process with LLM in separate thread
                threading.Thread(target=lambda: self.process_voice_command(text)).start()
                
            except sr.WaitTimeoutError:
                if self.is_listening:
                    self.status_var.set("No speech detected. Please try again.")
            except sr.UnknownValueError:
                if self.is_listening:
                    self.status_var.set("Sorry, I didn't understand that.")
            except sr.RequestError:
                if self.is_listening:
                    self.status_var.set("Speech recognition service unavailable.")
            except Exception as e:
                if self.is_listening:
                    print(f"Speech recognition error: {e}")
                    self.status_var.set(f"Error: Speech recognition issue")
            
            # Small delay to prevent CPU overuse
            time.sleep(0.5)
    
    def process_voice_command(self, text):
        """Process voice commands with intelligent intent recognition"""
        # Lowercase for easier comparison
        text = text.lower()
        
        # Add to conversation history
        self.conversation_history.append({"role": "user", "content": text})
        
        try:
            # Generate response using Ollama or fallback
            if HAS_OLLAMA and self.ollama:
                response = self.generate_ollama_response(text, include_context=True)
            else:
                response = self.get_fallback_response(text)
            
            # Add assistant response to conversation history
            self.conversation_history.append({"role": "assistant", "content": response})
            
            # Speak the response
            self.speak(response)
            
            # Execute any actions based on user intent
            self.execute_voice_command(text)
            
        except Exception as e:
            print(f"Error processing voice command: {e}")
            print(traceback.format_exc())
            self.speak("I'm sorry, I'm having trouble understanding your request.")
    
    def execute_voice_command(self, command):
        """Execute appropriate actions based on recognized intent with improved detection"""
        # Normalize the command text for better matching
        command = command.lower().strip()
        
        # Define patterns for different intents
        guided_ordering_patterns = ["guide", "guided", "help me order", "step by step", "assist", "start ordering"]
        order_food_patterns = ["order food", "place order", "get food", "food delivery", "hungry", "want to eat"]
        track_patterns = ["track", "where", "delivery status", "food status", "order status"]
        past_order_patterns = ["past", "history", "previous", "old orders", "ordered before"]
        account_patterns = ["account", "profile", "my information", "my details", "payment", "address"]
        help_patterns = ["help", "support", "service", "assistance", "problem", "issue", "complaint"]
        back_patterns = ["back", "previous", "return", "main", "home", "start", "beginning"]
        
        try:
            # Check for guided ordering intent
            if any(pattern in command for pattern in guided_ordering_patterns):
                self.root.after(0, self.show_guided_ordering)
                
            # Check for ordering food intent
            elif any(pattern in command for pattern in order_food_patterns):
                self.root.after(0, self.show_order_screen)
            
            # Check for tracking intent
            elif any(pattern in command for pattern in track_patterns):
                self.root.after(0, self.show_tracking_screen)
            
            # Check for past orders intent
            elif any(pattern in command for pattern in past_order_patterns):
                self.root.after(0, self.show_past_orders)
            
            # Check for account intent
            elif any(pattern in command for pattern in account_patterns):
                self.root.after(0, self.show_account_screen)
            
            # Check for help intent
            elif any(pattern in command for pattern in help_patterns):
                self.root.after(0, self.show_customer_service)
            
            # Check for back intent
            elif any(pattern in command for pattern in back_patterns):
                self.root.after(0, self.create_main_screen)
        except Exception as e:
            print(f"Error executing voice command: {e}")
            # No action for errors
    
    def speak(self, text):
        """Text-to-speech function with error handling"""
        # Skip if TTS engine not available
        if not HAS_TTS or not self.engine:
            print(f"TTS not available. Would have said: {text}")
            return
            
        def speak_thread():
            try:
                self.engine.say(text)
                self.engine.runAndWait()
            except Exception as e:
                print(f"TTS Error: {e}")
        
        # Run in separate thread to avoid freezing the GUI
        threading.Thread(target=speak_thread).start()
    
    def generate_ollama_response(self, user_message, include_context=True):
        """Generate a response using Ollama with robust error handling"""
        if not HAS_OLLAMA or not self.ollama:
            # Fallback responses if Ollama is not available
            return self.get_fallback_response(user_message)
            
        try:
            # Create a system prompt for Uber Eats context
            system_prompt = """You are an AI assistant for Uber Eats, helping users order food, track deliveries, 
            and resolve customer service issues. Be friendly, concise, and helpful. Focus on providing 
            accurate information about food delivery services. Keep responses relatively short."""
            
            # Get information about the current screen to add context if requested
            context = ""
            if include_context:
                context = f"The user is currently on the {self.current_screen} screen of the Uber Eats app. "
                
                # Add any active order information
                active_orders = [order for order in self.user_info["recent_orders"] if order["status"] == "In Progress"]
                if active_orders:
                    order = active_orders[0]
                    context += f"They have an active order from {order['restaurant']} with items: {', '.join(order['items'])}. "
            
            # Create a visual indicator of processing
            try:
                processing_label = tk.Label(
                    self.root,
                    text="⏳ Processing...",
                    font=self.font_small,
                    fg=self.color_dark_text,
                    bg=self.color_light_gray,
                    padx=15,
                    pady=10,
                    borderwidth=1,
                    relief="solid"
                )
                
                # Only show the processing indicator for longer queries
                if len(user_message.split()) > 5:
                    processing_label.place(relx=0.5, rely=0.5, anchor="center")
                    self.root.update_idletasks()
            except Exception as e:
                print(f"Error showing processing indicator: {e}")
                processing_label = None
            
            # Call Ollama API with timeout protection
            try:
                response = self.ollama.chat(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"{context}\n\n{user_message}"}
                    ],
                    stream=False
                )
                
                # Remove the processing indicator
                if processing_label and len(user_message.split()) > 5:
                    processing_label.destroy()
                
                # Extract the response text
                if response and 'message' in response and 'content' in response['message']:
                    return response['message']['content']
                else:
                    return "I'm sorry, I wasn't able to generate a proper response. How else can I help you?"
                    
            except Exception as e:
                # Handle Ollama API errors
                print(f"Ollama API error: {e}")
                
                # Remove the processing indicator
                if processing_label and len(user_message.split()) > 5:
                    processing_label.destroy()
                
                # Use fallback responses
                return self.get_fallback_response(user_message)
            
        except Exception as e:
            print(f"Error with Ollama call: {e}")
            print(traceback.format_exc())
            return self.get_fallback_response(user_message)
    
    def get_fallback_response(self, user_message):
        """Provide contextual fallback responses"""
        user_message = user_message.lower()
        
        # Order status related queries
        if ("order" in user_message and "status" in user_message) or "where" in user_message and "food" in user_message:
            return self.get_order_status_response()
            
        # Food recommendation related queries
        elif "recommend" in user_message or "suggest" in user_message or "what should i" in user_message:
            return "Based on popular choices, I'd recommend trying the Burger Bistro's signature cheeseburger or Pizza Palace's pepperoni pizza. Both have excellent reviews and quick delivery times!"
            
        # Delivery time related queries
        elif "delivery" in user_message and ("time" in user_message or "how long" in user_message or "when" in user_message):
            return "Delivery times typically range from 20-45 minutes depending on your distance from the restaurant, current demand, and weather conditions. You'll see the estimated delivery time before confirming your order."
            
        # Help or guidance
        elif "help" in user_message or "how do i" in user_message or "guide" in user_message:
            return "I can help you order food, track deliveries, or answer questions about Uber Eats. You can say things like 'Order pizza', 'Track my delivery', or 'Show my past orders'."
            
        # Payment related
        elif "payment" in user_message or "pay" in user_message or "card" in user_message:
            return "You can manage your payment methods in the Account section. We accept most major credit cards, PayPal, and Apple Pay. Your payment information is securely stored and processed."
            
        # General greeting
        elif "hi" in user_message or "hello" in user_message or "hey" in user_message:
            return "Hello! How can I help you with Uber Eats today? I can help you order food, track a delivery, or answer questions about our service."
            
        # Default fallback
        else:
            return "I understand you're asking about that. Let me help you with this matter. Please note that I'm currently operating with limited capabilities. For more complex issues, you might want to try using the on-screen options or contact our customer service team."
    
    def get_order_status_response(self):
        """Generate response about order status with rich details if available"""
        # Check if user has any in-progress orders
        active_orders = [order for order in self.user_info["recent_orders"] if order["status"] == "In Progress"]
        
        if active_orders:
            order = active_orders[0]
            
            # Generate estimated delivery time
            now = datetime.now()
            delivery_time = now + timedelta(minutes=random.randint(10, 25))
            eta_time = delivery_time.strftime("%I:%M %p")
            
            # Generate a more detailed response
            response = f"Your order from {order['restaurant']} is on the way! "
            response += f"You ordered {', '.join(order['items'])}. "
            response += f"The estimated delivery time is {eta_time}, about {(delivery_time - now).seconds // 60} minutes from now. "
            
            # Add random details to make it more realistic
            details = [
                "The driver is currently picking up your order.",
                "Your food is being prepared and should be ready for pickup soon.",
                "The restaurant has confirmed your order and is preparing it now.",
                "Your driver will be on their way shortly after picking up your food."
            ]
            response += random.choice(details)
            
            return response
        else:
            return "I don't see any active orders in your account right now. Would you like to place a new order or check your order history?"

# Run the application with comprehensive error handling
if __name__ == "__main__":
    try:
        # Set up the main application window
        print("Starting Uber Eats Voice Assistant application...")
        root = tk.Tk()
        
        # Center the window on screen
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        window_width = 400
        window_height = 700
        x_position = (screen_width - window_width) // 2
        y_position = (screen_height - window_height) // 2
        root.geometry(f"{window_width}x{window_height}+{x_position}+{y_position}")
        
        # Initialize the application
        print("Initializing application...")
        app = UberEatsIVR(root)
        
        # Display a welcome message
        print("Application started successfully!")
        
        # Start the main event loop
        root.mainloop()
        
    except Exception as e:
        # Handle any unexpected errors during startup
        error_message = f"Error starting application: {e}\n\n{traceback.format_exc()}"
        print(error_message)
        
        try:
            # Try to show a graphical error message
            messagebox.showerror("Application Error", 
                               f"An error occurred while starting the application:\n\n{e}\n\n" +
                               "Please make sure all required dependencies are installed.")
        except:
            # If that fails, just print to console
            print("Could not display error dialog. See error details above.")
            
        # Keep console open
        input("Press Enter to close...")