# Meshtastic AI Bot

An AI-powered bot that connects to Meshtastic devices and responds to queries using OpenAI's GPT models.

## Features

- Connects to Meshtastic devices via serial/USB
- Listens for messages starting with a configurable prefix (default: "!")
- Sends queries to OpenAI's GPT-4o-mini model
- Automatically limits responses to Meshtastic's character limits
- Simple GUI for configuration and monitoring
- Real-time message logging

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Connect your Meshtastic device via USB

3. Run the application:
   ```bash
   python meshtastic_ai_bot.py
   ```

4. Configure the bot:
   - Select your COM port and click "Connect"
   - Enter your OpenAI API key
   - Click "Enable AI"
   - Click "Start Bot"

## Usage

Once the bot is running, anyone on the mesh network can send a message starting with "!" followed by their question:

- `!How do I fix a flat tire?`
- `!Tell me a joke`

The bot will respond with AI-generated answers under 200 characters (Meshtastic limit).

## Configuration

- **Command Prefix**: Change the trigger character (default: "!")
- **Max Response Length**: Adjust the character limit for responses (default: 200)
- **OpenAI Model**: Uses GPT-4o-mini for fast, cost-effective responses

## Requirements

- Meshtastic device with USB connection
- OpenAI API key
- Python 3.7+
