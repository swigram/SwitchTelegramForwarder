# SwitchTelegramForwarder

SwitchTelegramForwarder is a bot that streams messages from Telegram channels to Switch channels, allowing for seamless content synchronization between the two platforms.

## Features

- Stream messages from multiple Telegram channels to Switch channels
- Support for text, photos, documents, videos, audio, and stickers
- Inline keyboard button support
- Redis-based caching for efficient data management
- Command system for easy management of watched channels

## Setup Guide

Follow these steps to set up and run the SwitchTelegramForwarder:

1. **Clone the repository**

   ```
   git clone https://github.com/swigram/SwitchTelegramForwarder.git
   cd SwitchTelegramForwarder
   ```

2. **Set up a virtual environment (optional but recommended)**

   ```
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

3. **Install dependencies**

   ```
   pip install -r requirements.txt
   ```

4. **Set up your Telegram API credentials**

   - Go to https://my.telegram.org/ and log in with your Telegram account.
   - Click on "API development tools" and create a new application.
   - Note down your `API_ID` and `API_HASH`.

5. **Configure environment variables**

   Create a `.env` file in the project root and add the following:

   ```
   API_ID=your_api_id
   API_HASH=your_api_hash
   TG_BOT_TOKEN=your_telegram_bot_token
   SESSION=your_telethon_session_string
   REDISPASSWORD=your_redis_password
   REDIS_URL=your_redis_url
   REDISUSER=your_redis_username
   ```

   Replace the placeholders with your actual credentials.

6. **Generate a session string (if not using a bot token)**

   If you're using a user account instead of a bot, run the session generator script:

   ```
   python session_gen.py
   ```

   Follow the prompts to enter your phone number and the verification code.

7. **Run the bot**

   ```
   python bot.py
   ```

## Usage

Once the bot is running, you can use the following commands in your Switch channel:

- `/start`: Get help and information about the bot
- `/watch <telegram_channel_link>`: Start streaming messages from a Telegram channel
- `/list`: Get a list of Telegram channels currently being watched
- `/unwatch <telegram_channel_link>`: Stop streaming messages from a Telegram channel

## File Structure

- `bot.py`: Main bot script
- `FastTelethon.py`: Custom implementation for faster file transfers
- `var.py`: Variable configurations using environment variables
- `session_gen.py`: Script to generate Telethon session string
- `test.py`: Test script (if applicable)
- `.env`: Environment variables (not tracked by git)
- `.gitignore`: Specifies intentionally untracked files to ignore
- `requirements.txt`: List of Python dependencies

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the GNU General Public License v3.0. See the [LICENSE](https://github.com/swigram/SwitchTelegramForwarder/blob/main/LICENSE) file for details.

## Support

For support, issues, or feature requests, please file an issue on the GitHub repository.
