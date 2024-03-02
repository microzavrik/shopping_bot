### Telegram Bot using aiogram with SQLite3 Integration 🤖📦
<hr>
Welcome to the Telegram bot repository leveraging the aiogram library and SQLite3 for seamless database operations. This bot serves as a versatile communication tool between clients and administrators, offering a range of essential features.

## Bot Functionality:
#### Client-Side:
- Messaging: Clients can easily send messages to the administrator.
- Role Assignment: Clients can set their role within the bot.

#### Administrator-Side:
- Messaging: Administrators can send media/text messages to clients.
- User Information: Access detailed information about each user.
- Role Management: Set roles for users.
- Targeted Messaging: Send messages based on specific user criteria.
- Quick Responses: Create and utilize templates for frequently asked questions.

### Required libraries
```
pip install aiogram=2.* sqlite3
```

<hr>

## Usage:

Clone the Repository:

```
git clone https://github.com/sxaxq/shopping_bot
cd shopping_bot
```

#### Configuration:

Create a config.py file in the root directory.
Define your Telegram bot API token and any other required parameters in config.py.

```
python main.py
```

Customize roles, templates, and functionalities in the bot to tailor it to your specific use case. Facilitate efficient communication and management with this feature-rich Telegram bot! 🚀💬📊
