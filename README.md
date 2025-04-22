# Twitter 2 WhatsApp Video Downloader Bot

A Python bot that automatically downloads videos from Twitter and sends them to WhatsApp users upon request. This bot monitors Twitter mentions, processes video requests, and delivers them directly to users' WhatsApp numbers.

## Features

- Automatic Twitter mention monitoring
- Video download and processing
- WhatsApp integration for direct delivery
- Health monitoring system
- Support for multiple video formats
- User authentication and tracking
- Error handling and logging

## Prerequisites

- Python 3.7+
- Chrome browser
- ChromeDriver
- WhatsApp Web access
- Twitter API credentials

## Installation

1. Clone the repository:
```bash
git clone https://github.com/OkoyaUsman/twitter-video-whatsapp.git
cd twitter-video-whatsapp
```

2. Install required dependencies:
```bash
pip install -r requirements.txt
```

3. Configure the environment:
- Create a `.env` file in the root directory
- Add your credentials (see Configuration section)

4. Set up ChromeDriver:
- Download ChromeDriver matching your Chrome version
- Place it in the specified path in the code

## Configuration

Create a `.env` file with the following variables:
```
TWITTER_AUTH_TOKEN=your_auth_token
TWITTER_CT0=your_ct0_token
```

## Usage

1. Start the bot:
```bash
python bot.py
```

2. The bot will:
- Initialize WhatsApp Web session
- Monitor Twitter mentions
- Process video requests
- Send videos to users' WhatsApp numbers

3. To request a video:
- Mention @whatsapp_save in a reply to a tweet containing a video
- The bot will automatically send the video to your registered WhatsApp number

## Contributing

We welcome contributions! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Support

For assistance, customization, or further help:
- Telegram: [@okoyausman](https://t.me/okoyausman)
- Create an issue in the repository

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Security

Please note that this bot requires sensitive credentials. Never commit your actual credentials to the repository. Use environment variables or a secure configuration management system.
