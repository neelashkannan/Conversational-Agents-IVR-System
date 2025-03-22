import tkinter as tk
from tkinter import messagebox

# This will print debugging information
print("Starting application...")

try:
    # Create the main window
    print("Creating root window...")
    root = tk.Tk()
    root.title("Simple Test Window")
    root.geometry("400x300")
    
    # Add a simple message
    print("Adding widgets...")
    label = tk.Label(root, text="Basic Tkinter Test", font=("Arial", 16))
    label.pack(pady=50)
    
    button = tk.Button(
        root, 
        text="Click Me", 
        command=lambda: messagebox.showinfo("Test", "Button clicked!")
    )
    button.pack(pady=20)
    
    # Show success message
    print("Setup complete, starting mainloop...")
    messagebox.showinfo("Test", "If you see this, Tkinter is working correctly!")
    
    # Start the main event loop
    root.mainloop()
    
except Exception as e:
    # Print error details
    print(f"ERROR: {e}")
    
    # Try to show an error dialog
    try:
        tk.Tk().withdraw()
        messagebox.showerror("Error", f"Application failed to start: {e}")
    except:
        print("Could not show error dialog")
    
    # Keep console open for error inspection
    input("Press Enter to close...")