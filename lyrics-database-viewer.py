import tkinter as tk
from tkinter import messagebox
import sqlite3

class LyricsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Lyrics Viewer and Deleter")
        
        self.conn = sqlite3.connect('lyrics.db')
        self.cursor = self.conn.cursor()
        
        self.create_widgets()
        self.populate_song_list()
    
    def create_widgets(self):
        # Song list
        self.song_listbox = tk.Listbox(self.root)
        self.song_listbox.pack(fill=tk.BOTH, expand=True)
        self.song_listbox.bind('<<ListboxSelect>>', self.on_song_select)
        
        # Delete button
        self.delete_button = tk.Button(self.root, text="Delete Song", command=self.delete_song)
        self.delete_button.pack()
        
        # Lyrics text
        self.lyrics_text = tk.Text(self.root)
        self.lyrics_text.pack(fill=tk.BOTH, expand=True)
    
    def populate_song_list(self):
        self.cursor.execute("SELECT id, title FROM songs")
        songs = self.cursor.fetchall()
        for song in songs:
            self.song_listbox.insert(tk.END, f"{song[1]} (ID: {song[0]})")
    
    def on_song_select(self, event):
        selected_index = self.song_listbox.curselection()
        if selected_index:
            song_id = int(self.song_listbox.get(selected_index).split("ID: ")[1][:-1])
            self.show_lyrics(song_id)
    
    def show_lyrics(self, song_id):
        self.cursor.execute("SELECT text FROM lyrics_lines WHERE song_id=?", (song_id,))
        lyrics = self.cursor.fetchall()
        self.lyrics_text.delete(1.0, tk.END)
        for line in lyrics:
            self.lyrics_text.insert(tk.END, line[0] + "\n")
    
    def delete_song(self):
        selected_index = self.song_listbox.curselection()
        if selected_index:
            song_id = int(self.song_listbox.get(selected_index).split("ID: ")[1][:-1])
            self.cursor.execute("DELETE FROM songs WHERE id=?", (song_id,))
            self.cursor.execute("DELETE FROM lyrics_lines WHERE song_id=?", (song_id,))
            self.cursor.execute("DELETE FROM querys WHERE song_id=?", (song_id,))
            self.conn.commit()
            self.song_listbox.delete(selected_index)
            self.lyrics_text.delete(1.0, tk.END)
            messagebox.showinfo("Success", "Song and lyrics deleted successfully")
        else:
            messagebox.showwarning("Warning", "Please select a song to delete")

if __name__ == "__main__":
    root = tk.Tk()
    app = LyricsApp(root)
    root.mainloop()
