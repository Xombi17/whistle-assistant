import tkinter as tk
from jarvis.core import Assistant
from jarvis.gui import JarvisGUI

def main():
    root = tk.Tk()
    root.title("Jarvis")
    assistant = Assistant()
    JarvisGUI(root, assistant)
    root.mainloop()

if __name__ == "__main__":
    main()
