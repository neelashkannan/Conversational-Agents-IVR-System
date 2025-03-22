import sys
import platform
import importlib.util

# Keep window open
def pause():
    input("\nPress Enter to exit...")

# Print system info
print(f"Python version: {platform.python_version()}")
print(f"Platform: {platform.platform()}")

# Check for required packages
required_packages = [
    'tkinter',
    'PIL',
    'speech_recognition',
    'pyttsx3',
    'ollama'
]

print("\nChecking required packages:")

for package in required_packages:
    try:
        if package == 'tkinter':
            import tkinter
            print(f"✓ {package} (version: {tkinter.TkVersion})")
        else:
            spec = importlib.util.find_spec(package)
            if spec is not None:
                if package == 'PIL':
                    import PIL
                    print(f"✓ {package} (version: {PIL.__version__})")
                elif package == 'speech_recognition':
                    import speech_recognition
                    print(f"✓ {package} (version available)")
                elif package == 'pyttsx3':
                    import pyttsx3
                    print(f"✓ {package} (version available)")
                elif package == 'ollama':
                    try:
                        import ollama
                        print(f"✓ {package} (version available)")
                    except:
                        print(f"✗ {package} (importable but has issues)")
                else:
                    print(f"✓ {package} (importable)")
            else:
                print(f"✗ {package} (not found)")
    except Exception as e:
        print(f"✗ {package} (error: {e})")

# Try to open a basic Tkinter window
print("\nTrying to open a Tkinter window...")
try:
    import tkinter as tk
    root = tk.Tk()
    root.title("Environment Test")
    root.geometry("200x100")
    label = tk.Label(root, text="Tkinter works!")
    label.pack(pady=30)
    
    # Close after 3 seconds
    root.after(3000, root.destroy)
    root.mainloop()
    
    print("Tkinter window opened and closed successfully!")
except Exception as e:
    print(f"Failed to open Tkinter window: {e}")

# Keep console open
pause()