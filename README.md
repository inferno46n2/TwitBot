Twitter Bot Using OpenAI GPT-3

This project contains a Twitter bot that uses OpenAI's GPT-3 model to generate responses to tweets. The bot is designed to portray a specific character that is foul-mouthed, sarcastic, and sharp-witted.

Features
Fetches the latest tweets mentioning a specific user.
Generates a response for each mention using OpenAI's GPT-3 model.
Posts the response as a reply to the mention on Twitter.
Handles rate limits and other exceptions by backing off and retrying after a certain period of time.
Keeps track of which tweets it has already replied to avoid replying to the same tweet multiple times.

Setup
Clone this repository to your local machine.
Install the required dependencies by running pip install in cmd terminal. Check the imports at the top of the main script to see which dependencies are required.

Usage
The bot is designed to reply to tweets in a very specific manner, portraying a character that is foul-mouthed, sarcastic, and sharp-witted. The character's responses are generated using OpenAI's GPT-3 model. You can modify this within the script.

Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

License
MIT
