#!/usr/bin/env python3
"""
Meshtastic AI Bot
Listens for messages starting with "!" and responds using OpenAI's GPT model
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import meshtastic
import meshtastic.serial_interface
from pubsub import pub
import threading
import serial.tools.list_ports
import time
import json
import openai
from datetime import datetime
import re

class MeshtasticAIBot:
    def __init__(self, master):
        self.master = master
        master.title("Meshtastic AI Bot")
        master.geometry("800x700")
        master.minsize(700, 600)
        
        # Configure the grid to expand properly
        master.columnconfigure(0, weight=1)
        master.rowconfigure(0, weight=1)

        # Set theme colors
        self.bg_color = "#f0f4f8"
        self.accent_color = "#3498db"
        self.master.configure(bg=self.bg_color)
        
        # Create a style
        self.style = ttk.Style()
        self.style.configure("TFrame", background=self.bg_color)
        self.style.configure("TLabel", background=self.bg_color, font=("Arial", 10))
        self.style.configure("TButton", font=("Arial", 10, "bold"))
        self.style.configure("Header.TLabel", font=("Arial", 14, "bold"))
        
        # Meshtastic connection
        self.interface = None
        self.is_connected = False
        
        # OpenAI settings
        self.openai_client = None
        self.ai_enabled = False
        self.command_prefix = "!"
        self.max_response_length = 200  # Meshtastic text message limit
        
        # Bot settings
        self.bot_active = False
        self.processed_messages = set()  # To avoid processing the same message twice
        
        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self.master, padding="20", style="TFrame")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        main_frame.columnconfigure(0, weight=1)
        
        # Header
        header_label = ttk.Label(main_frame, text="Meshtastic AI Bot", style="Header.TLabel")
        header_label.grid(row=0, column=0, pady=(0, 20))
        
        # Connection Settings Frame
        settings_frame = ttk.LabelFrame(main_frame, text="Connection Settings", padding="10")
        settings_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        settings_frame.columnconfigure(1, weight=1)
        
        # COM Port with refresh button
        port_frame = ttk.Frame(settings_frame)
        port_frame.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        port_frame.columnconfigure(0, weight=1)
        
        ttk.Label(settings_frame, text="COM Port:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.com_ports = self.get_available_ports()
        self.com_port = ttk.Combobox(port_frame, values=self.com_ports, width=40)
        if self.com_ports:
            self.com_port.set(self.com_ports[0])
        self.com_port.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        refresh_button = ttk.Button(port_frame, text="⟳", width=3, command=self.refresh_ports)
        refresh_button.grid(row=0, column=1, padx=(5, 0))
        
        # Connect Button
        self.connect_button = ttk.Button(settings_frame, text="Connect", command=self.toggle_connection)
        self.connect_button.grid(row=0, column=2, padx=5, pady=5)
        
        # AI Settings Frame
        ai_frame = ttk.LabelFrame(main_frame, text="AI Settings", padding="10")
        ai_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        ai_frame.columnconfigure(1, weight=1)
        
        # OpenAI API Key
        ttk.Label(ai_frame, text="OpenAI API Key:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.api_key_var = tk.StringVar()
        self.api_key_entry = ttk.Entry(ai_frame, textvariable=self.api_key_var, show="*", width=50)
        self.api_key_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        # Command Prefix
        ttk.Label(ai_frame, text="Command Prefix:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.prefix_var = tk.StringVar(value="!")
        self.prefix_entry = ttk.Entry(ai_frame, textvariable=self.prefix_var, width=10)
        self.prefix_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Max Response Length
        ttk.Label(ai_frame, text="Max Response Length:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.max_length_var = tk.StringVar(value="200")
        self.max_length_entry = ttk.Entry(ai_frame, textvariable=self.max_length_var, width=10)
        self.max_length_entry.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        # AI Enable Button
        self.ai_button = ttk.Button(ai_frame, text="Enable AI", command=self.toggle_ai)
        self.ai_button.grid(row=3, column=0, columnspan=2, pady=10)
        
        # Bot Controls Frame
        bot_frame = ttk.LabelFrame(main_frame, text="Bot Controls", padding="10")
        bot_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Bot Status
        self.bot_status_var = tk.StringVar(value="Bot Inactive")
        self.bot_status_label = ttk.Label(bot_frame, textvariable=self.bot_status_var, font=("Arial", 12, "bold"))
        self.bot_status_label.grid(row=0, column=0, padx=5, pady=5)
        
        # Start/Stop Bot Button
        self.bot_button = ttk.Button(bot_frame, text="Start Bot", command=self.toggle_bot, width=15)
        self.bot_button.grid(row=0, column=1, padx=5, pady=5)
        
        # Test Button
        self.test_button = ttk.Button(bot_frame, text="Send Test Message", command=self.send_test_message, width=20)
        self.test_button.grid(row=0, column=2, padx=5, pady=5)
        
        # Messages Frame
        messages_frame = ttk.LabelFrame(main_frame, text="Message Log", padding="10")
        messages_frame.grid(row=4, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        messages_frame.rowconfigure(0, weight=1)
        messages_frame.columnconfigure(0, weight=1)
        
        # Log Display
        self.log_display = scrolledtext.ScrolledText(messages_frame, width=80, height=15, wrap=tk.WORD)
        self.log_display.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        
        # Status Bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=5, column=0, sticky=(tk.W, tk.E))
        
        # Configure main frame to expand
        main_frame.rowconfigure(4, weight=1)

    def get_available_ports(self):
        """Get a list of available COM ports"""
        return [port.device for port in serial.tools.list_ports.comports()]

    def refresh_ports(self):
        """Refresh the list of available COM ports"""
        self.com_ports = self.get_available_ports()
        self.com_port['values'] = self.com_ports
        if self.com_ports:
            self.com_port.set(self.com_ports[0])
        self.log("COM ports refreshed")

    def log(self, message):
        """Add a timestamped message to the log display"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.log_display.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_display.see(tk.END)

    def toggle_connection(self):
        """Toggle connection to Meshtastic device"""
        if not self.is_connected:
            self.connect_to_device()
        else:
            self.disconnect_from_device()

    def connect_to_device(self):
        """Connect to Meshtastic device"""
        if not self.com_port.get():
            messagebox.showerror("Error", "COM Port is required")
            return
            
        try:
            self.log(f"Connecting to Meshtastic device on {self.com_port.get()}...")
            self.interface = meshtastic.serial_interface.SerialInterface(devPath=self.com_port.get())
            self.log("Connected to Meshtastic device successfully")
            
            # Subscribe to receive messages
            pub.subscribe(self.on_receive, "meshtastic.receive")
            self.log("Subscribed to Meshtastic messages")
            
            # Get device info
            myinfo = self.interface.myInfo
            if myinfo:
                self.log(f"Connected to node: {myinfo.my_node_num}")
                
            self.is_connected = True
            self.connect_button.config(text="Disconnect")
            self.status_var.set("Connected")
            
        except Exception as e:
            self.log(f"Error connecting to Meshtastic device: {str(e)}")
            messagebox.showerror("Connection Error", f"Failed to connect to Meshtastic device: {str(e)}")

    def disconnect_from_device(self):
        """Disconnect from Meshtastic device"""
        if self.interface:
            try:
                self.interface.close()
                self.log("Meshtastic interface closed")
            except Exception as e:
                self.log(f"Error closing interface: {str(e)}")
            finally:
                self.interface = None
                
        self.is_connected = False
        self.connect_button.config(text="Connect")
        self.status_var.set("Disconnected")
        
        # Stop bot if it's running
        if self.bot_active:
            self.toggle_bot()

    def toggle_ai(self):
        """Toggle AI functionality"""
        if not self.ai_enabled:
            self.enable_ai()
        else:
            self.disable_ai()

    def enable_ai(self):
        """Enable AI functionality"""
        api_key = self.api_key_var.get().strip()
        if not api_key:
            messagebox.showerror("Error", "OpenAI API Key is required")
            return
            
        try:
            # Initialize OpenAI client
            self.openai_client = openai.OpenAI(api_key=api_key)
            
            # Test the API key with a simple request
            self.log("Testing OpenAI API connection...")
            test_response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10
            )
            
            self.ai_enabled = True
            self.ai_button.config(text="Disable AI")
            self.log("AI functionality enabled successfully")
            
            # Update settings
            self.command_prefix = self.prefix_var.get() or "!"
            try:
                self.max_response_length = int(self.max_length_var.get()) or 200
            except ValueError:
                self.max_response_length = 200
                self.max_length_var.set("200")
            
        except Exception as e:
            self.log(f"Error enabling AI: {str(e)}")
            messagebox.showerror("AI Error", f"Failed to enable AI: {str(e)}")

    def disable_ai(self):
        """Disable AI functionality"""
        self.ai_enabled = False
        self.openai_client = None
        self.ai_button.config(text="Enable AI")
        self.log("AI functionality disabled")
        
        # Stop bot if it's running
        if self.bot_active:
            self.toggle_bot()

    def toggle_bot(self):
        """Toggle bot active state"""
        if not self.bot_active:
            self.start_bot()
        else:
            self.stop_bot()

    def start_bot(self):
        """Start the AI bot"""
        if not self.is_connected:
            messagebox.showerror("Error", "Must be connected to Meshtastic device")
            return
            
        if not self.ai_enabled:
            messagebox.showerror("Error", "AI must be enabled")
            return
            
        self.bot_active = True
        self.bot_button.config(text="Stop Bot")
        self.bot_status_var.set("Bot Active")
        self.log(f"AI Bot started - listening for messages starting with '{self.command_prefix}'")

    def stop_bot(self):
        """Stop the AI bot"""
        self.bot_active = False
        self.bot_button.config(text="Start Bot")
        self.bot_status_var.set("Bot Inactive")
        self.log("AI Bot stopped")

    def on_receive(self, packet, interface):
        """Handle received messages from the mesh network"""
        try:
            from_id = packet.get('fromId', 'unknown')
            packet_id = packet.get('id', 'unknown')
            
            # Skip if we've already processed this message
            if packet_id in self.processed_messages:
                return
            self.processed_messages.add(packet_id)
            
            # Only process text messages when bot is active
            if (self.bot_active and 
                packet.get('decoded', {}).get('portnum') == 'TEXT_MESSAGE_APP'):
                
                message = packet.get('decoded', {}).get('text', '')
                self.log(f"Received message from {from_id}: {message}")
                
                # Check if message starts with command prefix
                if message.startswith(self.command_prefix):
                    query = message[len(self.command_prefix):].strip()
                    if query:
                        self.log(f"Processing AI query: '{query}'")
                        # Process in separate thread to avoid blocking
                        threading.Thread(
                            target=self.process_ai_query, 
                            args=(query, from_id), 
                            daemon=True
                        ).start()
                    else:
                        self.log("Empty query after command prefix")
            
        except Exception as e:
            self.log(f"Error processing received packet: {str(e)}")

    def process_ai_query(self, query, from_id):
        """Process an AI query and send response"""
        try:
            self.log(f"Sending query to OpenAI: '{query}'")
            
            # Create the AI prompt with length constraint
            system_prompt = f"""You are a helpful assistant responding via Meshtastic radio network. 
Your response MUST be under {self.max_response_length} characters. Be concise and helpful.
If the query requires a long answer, provide the most important information first."""
            
            # Get response from OpenAI
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
                max_tokens=int(self.max_response_length / 2),  # Rough estimate for token limit
                temperature=0.7
            )
            
            ai_response = response.choices[0].message.content.strip()
            
            # Ensure response is within character limit
            if len(ai_response) > self.max_response_length:
                ai_response = ai_response[:self.max_response_length-3] + "..."
            
            self.log(f"AI Response ({len(ai_response)} chars): {ai_response}")
            
            # Send response back to the mesh network
            self.send_text_message(ai_response)
            
        except Exception as e:
            error_msg = f"AI Error: {str(e)}"
            self.log(error_msg)
            # Send error message back to network
            if len(error_msg) <= self.max_response_length:
                self.send_text_message(error_msg)
            else:
                self.send_text_message("AI Error: Unable to process request")

    def send_text_message(self, message):
        """Send a text message to the mesh network"""
        try:
            if not self.is_connected or not self.interface:
                self.log("Cannot send message - not connected to Meshtastic device")
                return
                
            self.log(f"Sending message: {message}")
            self.interface.sendText(message, destinationId=meshtastic.BROADCAST_ADDR)
            self.log("Message sent successfully")
            
        except Exception as e:
            self.log(f"Error sending message: {str(e)}")

    def send_test_message(self):
        """Send a test message to verify connectivity"""
        if not self.is_connected:
            messagebox.showerror("Error", "Not connected to Meshtastic device")
            return
            
        test_message = f"Test message from AI Bot at {datetime.now().strftime('%H:%M:%S')}"
        self.send_text_message(test_message)

def main():
    root = tk.Tk()
    app = MeshtasticAIBot(root)
    
    # Handle window closing
    def on_closing():
        if app.is_connected:
            app.disconnect_from_device()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()
