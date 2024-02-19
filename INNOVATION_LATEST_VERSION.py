#!/usr/bin/env python
# coding: utf-8

# <h1>Compression des données de l'audio avec le codage de HUFFMAN 

# In[1]:


import numpy as np
import wave as wv
import pydub as pd
import struct
import heapq
import pickle
import json
import pyaudio
import os
from pydub.playback import play
from pydub import AudioSegment
from codage import huffman_codage
from codage import huffman_decodage
import tkinter 
import tkinter.messagebox
from tkinter import ttk, filedialog
from tkinter.filedialog import askopenfile
import customtkinter
import pygame 
from tkinter import *
from threading import *
from tkdial import Dial
import os
import math


# In[2]:


def Audio_normalise(audio_name):
    audio = AudioSegment.from_file(audio_name)
    samples = audio.get_array_of_samples()
    signal_arr = np.array(samples)
    MIN = np.min(signal_arr)
    new_sig = [i + (-1) * MIN for i in signal_arr]
    MAX = max(new_sig)
    new_sig = (new_sig / MAX) * (2**8)
    new_sigrr = np.round(new_sig)
    #new_sigr =new_sigrr.astype(float)
    return new_sigrr,MAX,MIN


# In[3]:


def Audio_denormalise(new_sigr,MAX,MIN):
    data_int = np.array(new_sigr) / (2**8)
    data_int *=MAX
    data_int_org = [i+MIN for i in data_int]
    return np.array(data_int_org , np.int16)


# In[4]:


def huffman_decode(code_list, code_dict):
    inv_code_dict = {v: k for k, v in code_dict.items()}
    decoded_data = ""
    code = ""
    for bit in code_list:
        code += bit
        if code in inv_code_dict:
            decoded_data += str(inv_code_dict[code])
            code = ""
    return decoded_data.split(".")


# In[5]:


def compress_audio(input_file, output_file):
    # Ouvrir le fichier audio
    audio = AudioSegment.from_file(input_file)
    num_channels = audio.channels
    sample_width = audio.sample_width
    frame_rate = audio.frame_rate
    num_frames = len(audio)
    audio_data = audio.get_array_of_samples()
    
    aud_nor=Audio_normalise(input_file)
    # Normaliser les données audio 
    audio_data_normalized = aud_nor[0].tolist()
    
    # Calculate the audio data size in bytes
    audio_data_size = len(audio_data) * sample_width // 8
    
    # Compression Huffman
    huffman_code, huffman_dict = huffman_codage(audio_data_normalized)
    
    # Create the header data
    magic_number = b'IRM'
    sample_rate_bytes = np.array([frame_rate], dtype=np.int32).tobytes()
    bit_depth_bytes = np.array([sample_width], dtype=np.int32).tobytes()
    channel_count_bytes = np.array([num_channels], dtype=np.int32).tobytes()
    audio_data_size_bytes = np.array([audio_data_size], dtype=np.int32).tobytes()
    start_data=b'data'
    
    # Encode metadata as JSON
    metadata = {"huffman_dict": huffman_dict, "MAX": str(aud_nor[1]), "MIN":str(aud_nor[2])}
    metadata_str = json.dumps(metadata)
    metadata_bytes = metadata_str.encode("utf-8")
    dict_size = len(metadata_bytes)
    dict_size_bytes =  np.array([dict_size], dtype=np.int32).tobytes()
    
    # Convertir les codes de Huffman en binaire
    huffman_bits = "".join([huffman_dict[c] for c in audio_data_normalized])
    huffman_bits += "0"*(8 - len(huffman_bits) % 8)  # Ajouter des zéros pour compléter le dernier octet
    
    # Convertir les bits de Huffman en octets
    huffman_bytes = bytearray([int(huffman_bits[i:i+8], 2) for i in range(0, len(huffman_bits), 8)])
    
    # Sauvegarder les données compressées dans un fichier .irm
    with open(output_file , "wb") as f:
        f.write(magic_number)
        f.write(sample_rate_bytes)
        f.write(bit_depth_bytes)
        f.write(channel_count_bytes)
        f.write(audio_data_size_bytes)
        f.write(dict_size_bytes)
        f.write(metadata_bytes)
        f.write(start_data)
        f.write(huffman_bytes)
        f.close()


# In[6]:


def reader_audio(input_file):
    # Open the compressed file
    with open(input_file, "rb") as f:
        # Read the header data
        magic_number = f.read(3)
        sample_rate_bytes = f.read(4)
        bit_depth_bytes = f.read(4)
        channel_count_bytes = f.read(4)
        audio_data_size_bytes = f.read(4)
        dict_size_bytes = f.read(4)
        metadata_bytes = f.read(int(np.frombuffer(dict_size_bytes,dtype=np.int32)))
        start_data = f.read(4)
        huffman_bytes = f.read()
        f.close()
    
    # Decode metadata from JSON
    metadata_str = metadata_bytes.decode("utf-8")
    metadata = json.loads(metadata_str)
    huffman_dict = metadata["huffman_dict"]
    MAX = int(metadata["MAX"])
    MIN= int(metadata["MIN"])
    # Convert the compressed audio data to bits
    huffman_bits = "".join([f"{byte:08b}" for byte in huffman_bytes])
    
    # Convert the bits to Huffman codes
    audio_data_normalized = huffman_decode(huffman_bits[:-2], huffman_dict)
    
    #return audio_data_normalized
    # Convert to normalized data 
    audio_data_normalised = [int(float(frm)) for frm in audio_data_normalized]
    
    # Convert to original data
    audio_data=Audio_denormalise(audio_data_normalised,MAX,MIN)
    
    #return audio_data
    
    # Convert the normalized data to binary data
    audio = bytearray(audio_data)
    
    audio_length = len(audio)
    # calculate the expected length of the audio data
    expected_length = audio_length + (audio_length % (np.frombuffer(channel_count_bytes, dtype=np.int32)[0] * np.frombuffer(bit_depth_bytes, dtype=np.int32)[0]))
    # pad the audio data with zeroes if necessary
    if audio_length < expected_length:
        audio += b'\x00' * (expected_length - audio_length)
    
    #return len(audio)
    # Create a temporary WAV file for playing the audio
    temp_file = "temp.wav"
    with wv.open(temp_file, "wb") as f:
        f.setnchannels(np.frombuffer(channel_count_bytes, dtype=np.int32)[0])
        f.setsampwidth(np.frombuffer(bit_depth_bytes, dtype=np.int32)[0])
        f.setframerate(np.frombuffer(sample_rate_bytes, dtype=np.int32)[0])
        f.writeframesraw(audio)
        f.close()
    #sound = AudioSegment(
    #        bytes(memoryview(audio).toreadonly()),
    #        frame_rate=np.frombuffer(sample_rate_bytes, dtype=np.int32)[0],
    #        channels=np.frombuffer(channel_count_bytes, dtype=np.int32)[0],
    #        sample_width=np.frombuffer(bit_depth_bytes, dtype=np.int32)[0]
    #    )
    #play(sound)
    


# In[7]:


customtkinter.set_appearance_mode("Dark")  # Modes: "System" (standard), "Dark", "Light"
customtkinter.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

try:
    class App(customtkinter.CTk):
        def __init__(self):
            super().__init__()

            # configure window
            self.title("G5-Converter")
            self.geometry(f"{760}x{620}")
            self.resizable(False, False)
            self.file_path = tkinter.StringVar()
            self.file2_conv = tkinter.StringVar()
            self.output_file = tkinter.StringVar()
            self.org_size = tkinter.DoubleVar()
            self.comp_size = tkinter.DoubleVar()
            
            def open_directory():
                file_path= filedialog.askopenfile(filetypes=[('Audio Files', ('.wav','.mp3','.irm','.ogg'))])
                
                if file_path:
                    self.file_path.set(file_path.name)
                    self.entry1.delete(0, tkinter.END)  
                    self.entry1.insert(0, file_path.name)
            
            def play_audio():
                file_name = self.file_path.get()
                if file_name.endswith(".irm"):
                    pygame.mixer.init()
                    pygame.mixer.music.load("temp.wav")
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy():
                        song_len = pygame.mixer.Sound("temp.wav").get_length() *1000
                        for i in range(0, math.ceil(song_len)):
                            progressbar.set(pygame.mixer.music.get_pos()/  song_len)
                            progressbar.update()
                else:
                    pygame.mixer.init()
                    pygame.mixer.music.load(file_name)
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy():
                        song_len = pygame.mixer.Sound(file_name).get_length() *1000
                        for i in range(0, math.ceil(song_len)):
                            progressbar.set(pygame.mixer.music.get_pos()/  song_len)
                            progressbar.update()
                        
            def open_file():
                file_path= filedialog.askopenfile(filetypes=[('Wave & IRM Files', ('.wav','.m4a'))])
                if file_path:
                    self.file2_conv.set(file_path.name)
                    self.output_file.set(file_path.name[:-4]+"NN.irm")
                    self.entry.delete(0, tkinter.END)  
                    self.entry.insert(0, file_path.name)  

            def Continue():
                pygame.mixer.music.unpause()

            def Pause():
                pygame.mixer.music.pause()
                
            def vol(v):
                pygame.mixer.music.set_volume(v)
            
            def convert():
                compress_audio(str(self.file2_conv.get()), str(self.output_file.get()))
                reader_audio(str(self.output_file.get()))
                #print(self.file2_conv.get(),self.output_file.get())
                
            def evaluate():
                self.org_size.set(os.path.getsize(str(self.file2_conv.get())))
                self.comp_size.set(os.path.getsize(str(self.output_file.get())))
                #print(self.org_size.get(),self.comp_size.get())
                rate=1-self.comp_size.get()/self.org_size.get()
                dial1.set(rate*100)
                self.label3.configure(text="Bit depth :16 bits")        

            # configure grid layout (3x3)
            self.grid_rowconfigure((0,1, 2), weight=1)
            self.grid_columnconfigure(2, weight=0)
            self.grid_columnconfigure((0, 1), weight=1)

            # create Welcome Label to frame
            
            self.label_frame = customtkinter.CTkFrame(self,height=100)
            self.label_frame.grid(row=0, column=0, columnspan=3,padx=(20, 20), pady=(10, 0), sticky="nsew")
            
            self.label0 = customtkinter.CTkLabel(self.label_frame,text="WELCOME TO G5-converter, Start by choosing a file audio \nto play or to convert to the new format (.irm) ",font=("Arial",25),justify="center")
            self.label0.place(x=20,y=29)

            

            # create Entry and Button to tabview
            self.entry_button_frame = customtkinter.CTkTabview(self)
            self.entry_button_frame.grid(row=1, column=0, columnspan=3,padx=(20, 20), pady=(0, 0), sticky="nsew")
            self.entry_button_frame.add("G5-Converter")
            
            self.label = customtkinter.CTkLabel(self.entry_button_frame.tab("G5-Converter"),text="Choose file :")
            self.label.grid(row=0, column=0, padx=(50, 0), pady=(0, 20), sticky="nsew")

            self.entry = customtkinter.CTkEntry(self.entry_button_frame.tab("G5-Converter"),width=420, placeholder_text="File.ext")
            self.entry.grid(row=0, column=1, columnspan=3, padx=(20, 0), pady=(0, 20), sticky="nsew")

            self.main_button_1 = customtkinter.CTkButton(master=self.entry_button_frame.tab("G5-Converter"),text="Open",width=100, fg_color="transparent", border_width=2, text_color=("gray10", "#DCE4EE"), command=open_file)
            self.main_button_1.grid(row=0, column=4, padx=(20, 20), pady=(0, 20), sticky="nsew")

            self.radio_var = tkinter.IntVar(value=0)
            self.label_radio_group = customtkinter.CTkLabel(master=self.entry_button_frame.tab("G5-Converter"), text="Convert to :")
            self.label_radio_group.grid(row=1, column=0, columnspan=2, padx=20, pady=0, sticky="")
            self.radio_button_1 = customtkinter.CTkRadioButton(master=self.entry_button_frame.tab("G5-Converter"),text=".IRM", variable=self.radio_var, value=0)
            self.radio_button_1.grid(row=1, column=2, pady=25, padx=20, sticky="n")
            self.radio_button_2 = customtkinter.CTkRadioButton(master=self.entry_button_frame.tab("G5-Converter"),text=".OGG", variable=self.radio_var, value=1)
            self.radio_button_2.grid(row=1, column=3, pady=25, padx=20, sticky="n")
            self.radio_button_2.configure(state = tkinter.DISABLED)
            self.radio_button_3 = customtkinter.CTkRadioButton(master=self.entry_button_frame.tab("G5-Converter"),text=".MP3", variable=self.radio_var, value=2)
            self.radio_button_3.grid(row=1, column=4, pady=25, padx=20, sticky="n")
            self.radio_button_3.configure(state = tkinter.DISABLED)
            
            self.main_button_2 = customtkinter.CTkButton(master=self.entry_button_frame.tab("G5-Converter"),width=120,height=32,border_width=1, corner_radius=8,text="CONVERT",
                                                         fg_color="#0055B3", text_color=("gray10", "#DCE4EE"),
                                                         command=convert)
            self.main_button_2.grid(row=2, column=2,columnspan=2, padx=(20, 20), pady=(0, 20), sticky="nsew")






            # create player to frame
            self.player_frame = customtkinter.CTkTabview(self)
            self.player_frame.grid(row=2, column=0, columnspan=2,padx=(20, 10), pady=(5, 20), sticky="nsew")
            self.player_frame.add("G5-Player")
            
            self.label1 = customtkinter.CTkLabel(self.player_frame.tab("G5-Player"),text="Choose file :")
            self.label1.grid(row=0, column=0, padx=(50, 0), pady=(0, 20), sticky="nsew")

            self.entry1 = customtkinter.CTkEntry(self.player_frame.tab("G5-Player"),width=220, placeholder_text="Choose file to play")
            self.entry1.grid(row=0, column=1, columnspan=3, padx=(20, 0), pady=(0, 20), sticky="nsew")

            self.main_button_11 = customtkinter.CTkButton(master=self.player_frame.tab("G5-Player"),width=100,text="Open", fg_color="transparent", border_width=2, text_color=("gray10", "#DCE4EE"), command=open_directory)
            self.main_button_11.grid(row=0, column=4, padx=(20, 20), pady=(0, 20), sticky="nsew")
            
            play_button = customtkinter.CTkButton(master=self.player_frame,width=150,fg_color="#0062CC", text='PLAY', command=play_audio)
            play_button.place(relx=0.5, rely=0.55, anchor=tkinter.CENTER)

            skip_f = customtkinter.CTkButton(master=self.player_frame,width=100,fg_color="#006EE6", text='CONTINUE', command=Continue )
            skip_f.place(relx=0.9, rely=0.55, anchor=tkinter.E)

            skip_b = customtkinter.CTkButton(master=self.player_frame,width=100,fg_color="#003D80", text='PAUSE', command=Pause)
            skip_b.place(relx=0.1, rely=0.55, anchor=tkinter.W)
            
            progressbar = customtkinter.CTkProgressBar(master=self.player_frame, progress_color='#32a85a', width=450)
            progressbar.place(relx=0.5, rely=.72, anchor=tkinter.CENTER)
            progressbar.set(0)
    
            self.label22 = customtkinter.CTkLabel(self.player_frame.tab("G5-Player"),text="Volume :")
            self.label22.place(relx=0.1, rely=0.9, anchor=tkinter.W)
            
            slider = customtkinter.CTkSlider(master=self.player_frame, from_= 0, to=1, command=vol, width=210)
            slider.place(relx=0.5, rely=0.9,anchor=tkinter.CENTER)

            


            # create para to frame
            self.para_frame = customtkinter.CTkTabview(self,width=200)
            self.para_frame.grid(row=2, column=2,padx=(0, 20), pady=(10, 20), sticky="nsew")
            self.para_frame.add("G5-Evaluation")
            
            dial1 = Dial(self.para_frame.tab("G5-Evaluation"), color_gradient=("green", "cyan"), bg="gray17",
             text_color="white", text="Ratio: ", unit_length=10, radius=60)
            dial1.place(relx=0.5, rely=0.35,anchor=tkinter.CENTER)
            
            
            self.label3 = customtkinter.CTkLabel(self.para_frame.tab("G5-Evaluation"),text="Bit depth :")
            self.label3.place(relx=0.1, rely=0.8, anchor=tkinter.W)
            
            self.label33 = customtkinter.CTkButton(self.para_frame.tab("G5-Evaluation"),height=10,text="Evaluate",command=evaluate)
            self.label33.place(relx=0.1, rely=0.94, anchor=tkinter.W)
         

    if __name__ == "__main__":
        app = App()
        app.mainloop()
except KeyboardInterrupt:
    pass


# In[ ]:




