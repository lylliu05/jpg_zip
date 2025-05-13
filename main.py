import tkinter as tk
from ui import ImageCompressorUI

def main():
    root = tk.Tk()
    app = ImageCompressorUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()    