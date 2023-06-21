**Twitter Bot Using OpenAI GPT-3**
This project contains a Twitter bot that uses OpenAI's GPT-3.5 Turbo model to generate responses to tweets. The bot is designed to portray a specific character that is foul-mouthed, sarcastic, and sharp-witted. Please note that as this calls the OpenAI API, you will be charged per reply so you need an active credit card on your account. The charges were incredibly small at the time of writing.

**Features**
Fetches the latest tweets mentioning a specific user.
Generates a response for each mention using OpenAI's GPT-3 model.
Posts the response as a reply to the mention on Twitter.
Handles rate limits and other exceptions by backing off and retrying after a certain period of time.
Keeps track of which tweets it has already replied to avoid replying to the same tweet multiple times.

**Setup**
Clone this repository to your local machine.
Install the required dependencies by running pip install in cmd terminal. Check the imports at the top of the main script to see which dependencies are required.

**Usage**
The bot is designed to reply to tweets in a very specific manner, portraying a character that is foul-mouthed, sarcastic, and sharp-witted. The character's responses are generated using OpenAI's GPT-3 model. You can modify this within the script.

**Contributing and General Comments**
This entire bot was written with no prior knowledge to python. I used GPT 4 to write 100% of the script. This is the product of months of fiddling in GPT and doing my own research to improve it. I did  steer it in certain directions, research better ways to do things, etc... but the general layout and formating of the code is likely sloppy. Please use this as a starting point that could be easily modified by someone more proficient in proper code structure. Feel free to use this code as a template to whatever you are building, or to improve upon.

**License**
MIT
