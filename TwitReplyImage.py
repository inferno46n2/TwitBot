import openai
import time
from datetime import datetime, timezone
from requests_oauthlib import OAuth1Session
from config import CONSUMER_KEY, CONSUMER_SECRET, ACCESS_TOKEN, ACCESS_SECRET, OPENAI_API_KEY
import subprocess
import os
import json
import re
import requests
import traceback
import logging
from tenacity import retry, wait_exponential

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_replied_to():
    file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'replied_to.json')
    print(f"Loading from: {os.path.abspath(file_path)}")
    try:
        with open(file_path, 'r') as f:
            data = f.read()
            return set(json.loads(data)) if data else set()
    except (FileNotFoundError, json.JSONDecodeError):
        return set()

def save_replied_to(replied_to):
    print("save_replied_to function called")
    print(f"Content of replied_to before saving: {replied_to}")
    try:
        # Get the directory of the script
        script_dir = os.path.dirname(os.path.realpath(__file__))
        # Construct the path of the file
        file_path = os.path.join(script_dir, 'replied_to.json')
        with open(file_path, 'w') as f:
            json.dump(list(replied_to), f)
            f.flush()  # Ensure the changes are written to the file
            os.fsync(f.fileno())  # Ensure the changes are written to the disk
        print("Successfully saved to replied_to.json")
        print(f"Absolute path of the file: {os.path.abspath(file_path)}")
        print(f"Content of replied_to after saving: {replied_to}")  # Print the content of replied_to after saving
    except Exception as e:
        print(f"An error occurred while saving to replied_to.json: {e}")


OPENAI_API_KEY = "Enter your OpenAI API Key here"
openai.api_key = OPENAI_API_KEY

if not ACCESS_TOKEN or not ACCESS_SECRET:
    # Get request token
    request_token_url = "https://api.twitter.com/oauth/request_token?oauth_callback=oob&x_auth_access_type=write"
    oauth = OAuth1Session(CONSUMER_KEY, client_secret=CONSUMER_SECRET)

    fetch_response = oauth.fetch_request_token(request_token_url)
    resource_owner_key = fetch_response.get("oauth_token")
    resource_owner_secret = fetch_response.get("oauth_token_secret")

    # Get access token
    base_authorization_url = "https://api.twitter.com/oauth/authorize"
    authorization_url = oauth.authorization_url(base_authorization_url)
    print("Please go here and authorize: %s" % authorization_url)
    verifier = input("Paste the PIN here: ")

    access_token_url = "https://api.twitter.com/oauth/access_token"
    oauth = OAuth1Session(
        CONSUMER_KEY,
        client_secret=CONSUMER_SECRET,
        resource_owner_key=resource_owner_key,
        resource_owner_secret=resource_owner_secret,
        verifier=verifier,
    )
    oauth_tokens = oauth.fetch_access_token(access_token_url)

    access_token = oauth_tokens["oauth_token"]
    access_token_secret = oauth_tokens["oauth_token_secret"]

    # Save the access tokens to config.py
    with open("config.py", "a") as config_file:
        config_file.write(f'\nACCESS_TOKEN = "{access_token}"')
        config_file.write(f'\nACCESS_SECRET = "{access_token_secret}"')

    # Reload the updated config.py with the new access tokens
    from importlib import reload
    import config
    reload(config)
    from config import ACCESS_TOKEN, ACCESS_SECRET

oauth = OAuth1Session(
    CONSUMER_KEY,
    client_secret=CONSUMER_SECRET,
    resource_owner_key=ACCESS_TOKEN,
    resource_owner_secret=ACCESS_SECRET,
)
print(f"OAuth session established: {oauth}")

# replace censored words in reply
def uncensor_text(text):
    text = text.replace("sh*t", "shit")
    text = text.replace("f*ck", "fuck")
    text = text.replace("f*cking", "fucking")
    text = text.replace("d*ck", "dick")
    text = text.replace("c*nt", "cunt")
    # Add more replacements here as needed
    return text

# Generate Response functions
def generate_response(tweet_content):
    response = None
    max_attempts = 10  # Maximum number of attempts to generate a valid response
    attempts = 0  # Counter for the number of attempts

    while attempts < max_attempts:
        attempts += 1  # Increment the counter

        prompt = make_chat_prompt(tweet_content)
        print(f"Prompt: {prompt}")  # Print the prompt being used

        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=prompt,
                max_tokens=100,
            )
        except Exception as e:
            print(f"An error occurred: {e}")

        print(f"OpenAI response: {response}")
        text = response['choices'][0]['message']['content'].strip()

        # Uncensor the text
        text = uncensor_text(text)

        # Remove leading unwanted characters
        unwanted_start_chars = {".", "\n", "?", ",", "*", "&", "#", "@"}
        while len(text) > 0 and text[0] in unwanted_start_chars:
            text = text[1:]
        text = text.strip()

        # Remove Twitter hashtags
        text = re.sub(r'#\S+', '', text).strip()

        if len(text) > 0 and len(text) <= 280:  # Check if the response is within the character limit and not empty
            return text
        else:
            print("Generated response was empty or too long, retrying...")

    # If we've reached the maximum number of attempts, return a default message or skip the tweet
    print(f"Failed to generate a valid response after {max_attempts} attempts. Skipping tweet.")
    return None  # Return None to indicate that we should skip this tweet

#This function is to generate a short response so the reply tweet doesn't only contain an image. There is a theory that the algo negatively penalizes imgs only without tweet text content
def generate_short_response(response_text):
    short_prompt = [
        {"role": "system", "content": "You are a jaded, sarcastic, and witty assistant that summarizes information. Use vulgarity, use curse words, censor nothing. Do not replace curse word letters with *, write the full words."},
        {"role": "user", "content": f"Summarize the following text into a couple words but keep the content relveant and the jaded sarcastic mood. Reply only with your response and nothing else: '{response_text}'"}
    ]

    short_response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=short_prompt,
        max_tokens=50,
    )

    short_text = short_response['choices'][0]['message']['content'].strip()
    return short_text

#ChatGPT Prompt. The first part is where you outline the role of your reply. This uses the OpenAI Playground environment where you can give instructions on how ChatGPT should behave.
def make_chat_prompt(tweet_content):
    return [
        {"role": "system", "content": "Engage in a role-play scenario where you portray a foul mouthed, ruthless, sarcastic, and sharp-witted 'keyboard warrior'. This character constantly voices negative opinions believing they're smarter than everyone else. Your replies should be incredibly condescending in nature. Your language is peppered with colloquial terms like 'bruh', 'bro', and 'brah' and always full of vulgarity and curse words like 'fuck, 'shit, 'fucking', 'idiot. Ensure your responses are strictly limited to 280 characters, and only include your character's dialogue. Never start responses with phrases like 'Oh wow', 'Wow', 'Oh look'. Your audience is the crypto Twitter community, a group primarily under 30 that is fluent in social media lingo. Your goal is to entertain and engage them with your wit and humor. Your replies should be structure like this: First: Explain to the person why they are wrong. This should be contextually relevant to the content I provide you. Second: Always end with an insult that includes a curse word like 'fuck', 'fucking', 'idiot', 'piece of shit', 'dumbass'"},
        {"role": "user", "content": tweet_content}
    ]

last_tweet_id = 0 # Just a variable to keep track of the last tweet we replied to.
replied_to = load_replied_to()

# Initialize last_tweet_id to None
last_tweet_id = None

#Function to scrape for mentions
def get_mentions(user='Insert your Twitter Handle Here', num_results=100, replied_to=None):
    # Load the replied_to set and get the latest tweet ID
    last_tweet_id = max(replied_to) if replied_to else None

    # Construct the snscrape command
    command = f"snscrape --jsonl --max-results {num_results} twitter-search '{user}'"
    command += "'"
    print(f"Running command: {command}")

    # Run the command and parse the tweets
    result = subprocess.run(command, stdout=subprocess.PIPE, shell=True, check=True)
    tweets = result.stdout.decode().split('\n')
    tweets = [json.loads(tweet) for tweet in tweets if tweet]  # Parse JSON for each tweet

    # Filter out tweets that are older than the last tweet we replied to
    if last_tweet_id is not None:
        tweets = [tweet for tweet in tweets if int(tweet['id']) > last_tweet_id]
    
    valid_tweets = []  # Create a new list to store valid tweets

    for tweet in tweets:
        reply_to = tweet["id"]
        #print(f"Tweet ID: {reply_to}")  # This will print the tweet ID

        try:
            parent_tweet_id = tweet['inReplyToTweetId']
            parent_tweet_command = f"snscrape --jsonl --max-results 1 twitter-tweet {parent_tweet_id}"
            parent_tweet_result = subprocess.run(parent_tweet_command, stdout=subprocess.PIPE, shell=True, check=True)
            parent_tweet = json.loads(parent_tweet_result.stdout.decode())
            if 'content' in parent_tweet:
                tweet['parent_tweet_content'] = parent_tweet['content']
            else:
                print(f"Parent tweet with ID {parent_tweet_id} does not have a 'content' field. It may have been deleted or is not publicly accessible.")
                tweet['parent_tweet_content'] = ''  # Set to empty string or a default message

            # Extract the username from the parent tweet
            if 'user' in parent_tweet and 'username' in parent_tweet['user']:
                tweet['parent_tweet_username'] = parent_tweet['user']['username']
            else:
                print(f"Parent tweet with ID {parent_tweet_id} does not have a 'user' or 'username' field. It may have been deleted or is not publicly accessible.")
                tweet['parent_tweet_username'] = ''  # Set to empty string or a default message

            # Check if the tweet is a reply to one of the bot's own tweets
            if tweet.get('inReplyToUser', {}).get('username', '').lower() == 'Insert your Twitter Handle Here':
                print("This tweet is a reply to one of the bot's own tweets. Skipping.")
                raise Exception("Skip tweet")

            # Check if the parent tweet is from the bot itself or if the bot is mentioned in the parent tweet
            if tweet['parent_tweet_username'].lower() == 'Insert your Twitter Handle Here' or re.search(r'\bInsert your Twitter Handle Here\b', tweet['parent_tweet_content'].lower()):
                print("The parent tweet is from the bot itself or the bot is mentioned in the parent tweet. Skipping.")
                raise Exception("Skip tweet")
            
            # Check if the tweet is authored by the bot itself
            if tweet.get('user', {}).get('username', '').lower() == 'Insert your Twitter Handle Here':
                print("This tweet is authored by the bot itself. Skipping.")
                continue

            valid_tweets.append(tweet)  # Add the tweet to the list of valid tweets

        except subprocess.CalledProcessError:
            print(f"Could not fetch parent tweet with ID {parent_tweet_id}. It may have been deleted or is not publicly accessible.")
            tweet['parent_tweet_content'] = ''  # Set to empty string or a default message
            continue  # Skip this mention and continue with the next one
        except Exception as e:
            if str(e) == "Skip tweet":
                continue  # Skip this tweet and continue with the next one
            else:
                raise  # If it's not our custom exception, raise it again

    # Print the list of valid tweets
    for tweet in valid_tweets:
        print(f"Valid Tweet ID: {tweet['id']}, Content: {tweet['content']}")

    return valid_tweets  # Return the list of valid tweets

#Below is the main loop
@retry(wait=wait_exponential(multiplier=1, min=4, max=10))
def main_loop():
# Initialize last_tweet_id to the max id in replied_to, or 0 if replied_to is empty
    last_tweet_id = max(replied_to) if replied_to else 0
    backoff_time = 1  # Start with a short delay
    while True:
        new_tweets_found = False  # Set new_tweets_found to True whenever a new tweet is found
        try:
            # Fetch mentions using snscrape
            mentions = get_mentions("Insert your Twitter Handle Here", num_results=100, replied_to=replied_to)
            for tweet in mentions:
                reply_to = tweet["id"]
                # Check if we've already replied to this tweet
                if reply_to in replied_to:
                    print("Already replied to this tweet. Skipping.")
                    time.sleep(2)  # Add sleep before continuing
                    continue
                new_tweets_found = True  # Set new_tweets_found to True whenever a new tweet is found

                # Check if the tweet was on or after June 5, 2023. This was put in place as the account was old and I didn't want it to reply to things from years ago.
                tweet_timestamp = datetime.fromisoformat(tweet["date"].replace("Z", "+00:00"))
                cutoff_date = datetime(2023, 6, 5, tzinfo=timezone.utc)
                if tweet_timestamp < cutoff_date:
                    continue

                # Check if the tweet is authored by the bot itself. This was a solution I was working on to prevent the bot from getting stuck in a loop where it replied to itself.
                if tweet.get('user', {}).get('username', '').lower() == 'Insert your Twitter Handle Here':
                    print("This tweet is authored by the bot itself. Skipping.")
                    continue

                # Check if the parent tweet is from the bot itself. This was a solution I was working on to prevent the bot from getting stuck in a loop where it replied to itself.
                if tweet.get('parent_tweet_username', '').lower() == 'Insert your Twitter Handle Here':
                    print("This tweet is a reply to the bot's own tweet. Skipping.")
                    time.sleep(2)  # Add sleep before continuing
                    continue

                response = None

                try:
                    new_tweets_found = True  # Set new_tweets_found to True whenever a new tweet is found

                    # Get the content of the parent tweet
                    parent_tweet_content = tweet.get('parent_tweet_content', '')
                    response_text = generate_response(parent_tweet_content)
                    short_text = generate_short_response(response_text)
                    if response_text is None:
                        print("Skipping tweet due to failure to generate a valid response.")
                        continue  # Skip this tweet and continue with the next one
                    print("Generated response:", response_text)

                    # Generate the image with the response text
                    from ImageDraw3 import generate_image_with_text  # Import the function from image script
                    try:
                        image_path = generate_image_with_text(response_text)  # Call the function with the response text
                    except Exception as e:
                        print(f"An error occurred while generating the image: {e}")
                        continue  # Skip this tweet and continue with the next one

                    # Check if the image file exists
                    if not os.path.isfile(image_path):
                        print(f"The image file does not exist: {image_path}")
                        continue  # Skip this tweet and continue with the next one

                    # Upload the image to Twitter
                    with open(image_path, 'rb') as f:
                        files = {'media': f}
                        url = 'https://upload.twitter.com/1.1/media/upload.json'
                        
                        print(f"Type of requests.post: {type(requests.post)}") 
                        print(f"Type of oauth: {type(oauth)}")  
                        
                        response = oauth.post(url, files=files)
                        print(f"Image upload response status: {response.status_code}")
                        print(f"Image upload response text: {response.text}")
                        if response.status_code != 200:
                            print(f"An error occurred while uploading the image: {response.text}")
                            continue  # Skip this tweet and continue with the next one
                        media_id = response.json()['media_id_string']
                        print(f"Media ID: {media_id}")

                        # Post a tweet with the image using Twitter API v2
                        payload = {
                            "text": short_text,  # This is where that short reply we generated earlier gets added
                            "media": {
                                "media_ids": [media_id]
                            },
                            "reply": {
                                "in_reply_to_tweet_id": str(reply_to)
                            }
                        }

                        print(f"Payload for Twitter post: {payload}")

                        response = oauth.post("https://api.twitter.com/2/tweets", json=payload)

                        if response.status_code == 429:  # Rate limit exceeded
                            rate_limit_reset = int(response.headers.get('x-rate-limit-reset', 0))
                            sleep_time = max(rate_limit_reset - time.time(), 0)
                            print(f"Rate limit exceeded. Sleeping for {sleep_time} seconds.")
                            time.sleep(sleep_time)
                            continue

                        if response.status_code != 200 or "data" not in response.json():
                            print(f"An error occurred while posting the tweet: {response.text}")
                            continue  # Skip this tweet and continue with the next one

                        # Add the tweet ID to the replied_to set and save it to the .json file
                        replied_to.add(reply_to)
                        print(f"Added {reply_to} to replied_to set")
                        save_replied_to(replied_to)
                        print(f"Saved replied_to set to file: {replied_to}")

                    # Update last_tweet_id if this tweet is newer
                    last_tweet_id = max(last_tweet_id or 0, reply_to)
                    
                except TimeoutError:
                    logger.warning(f"TimeoutError occurred. Backing off for {backoff_time} seconds.")
                    time.sleep(backoff_time)
                    backoff_time *= 2  # Double the backoff_time
                    continue

        except Exception as e:
            traceback.print_exc()
            # If it's our custom exception, continue with the next tweet
            if str(e) == "Skip tweet":
                continue
            # If it's not our custom exception, log the exception and continue
            else:
                print(f"Exception occurred while processing tweet: {str(e)}")
                # Check if response is None
                if response is None:
                    print("An error occurred before the response variable could be assigned a value.")
                else:
                    print(f"Response: {response}")
                print("Waiting for 60 seconds before processing the next tweet...")
                time.sleep(60)  # Pause after each tweet processing to avoid rate limit
                continue

        # Save the replied_to set at the end of each loop iteration
        save_replied_to(replied_to)

        # If no new tweets were found, wait for 60 seconds before the next iteration.
        if not new_tweets_found:
            print("No new tweets found. Waiting for 60 seconds before checking again...")
            time.sleep(60)

        print(f"End of loop. Replied_to set: {replied_to}")
        print("End of loop. Sleeping for 60 seconds...")
        time.sleep(60)

if __name__ == "__main__":
    main_loop()