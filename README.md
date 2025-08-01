# NexusCore Telegram Bot

NexusCore is a comprehensive Telegram bot platform for managing multiple accounts, parsing data, and performing automated actions in Telegram.

## Features

- **Account Management**: Add and manage multiple Telegram accounts
- **Parsing**: Extract members, writers, and commenters from Telegram groups and channels
- **Inviting**: Automatically invite users to your groups and channels
- **Comment Liking**: Automatically like comments on posts
- **Task Management**: Track progress and results of all operations

## System Architecture

NexusCore is built on a modern, scalable architecture with the following components:

- **Bot Interface**: Telegram bot UI for user interaction
- **API Layer**: FastAPI backend for handling operations
- **Worker System**: Background task processing
- **Database**: PostgreSQL for data storage
- **Task Queue**: Redis for job scheduling and distribution

## Requirements

- Python 3.8+
- Docker and Docker Compose
- PostgreSQL
- Redis

## Installation

### Using Docker (Recommended)

1. Clone the repository:
```bash
git clone https://github.com/yourusername/nexuscore.git
cd nexuscore
```

2. Create a `.env` file in the root directory with the following content:
```
BOT_TOKEN=your_telegram_bot_token
DB_PASSWORD=your_postgres_password
SECRET_KEY=your_secret_key
ENCRYPTION_KEY=your_encryption_key
```

3. Start the services:
```bash
docker-compose -f docker/docker-compose.yml up -d
```

### Manual Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/nexuscore.git
cd nexuscore
```

2. Create a virtual environment and install dependencies:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
export BOT_TOKEN=your_telegram_bot_token
export DATABASE_URL=postgresql://user:password@localhost/nexuscore
export REDIS_URL=redis://localhost:6379/0
export SECRET_KEY=your_secret_key
export ENCRYPTION_KEY=your_encryption_key
```

4. Start the services:
```bash
# Terminal 1: Start API
cd app
uvicorn api.main:app --reload

# Terminal 2: Start Bot
python -m app.bot.main

# Terminal 3: Start Worker
python -m app.worker.main
```

## Usage

1. Start a chat with your bot on Telegram
2. Add your Telegram accounts using the `/accounts` command
3. Use the various menu options for parsing, inviting, and liking operations

## Account Management

To use the bot effectively, you'll need to add at least one Telegram account. Each account requires:

- Phone number
- API ID (get from my.telegram.org)
- API Hash (get from my.telegram.org)

The bot will help you manage usage limits and cooldown periods to protect your accounts from being banned.

## Monitoring

The system includes Prometheus and Grafana for monitoring:

- Access Prometheus at http://localhost:9090
- Access Grafana at http://localhost:3000

## License

This project is licensed under the MIT License - see the LICENSE file for details.