import os
import tweepy
import time
import emoji

# Load credentials from environment variables
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
BEARER_TOKEN = os.getenv("BEARER_TOKEN")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
ACCESS_TOKEN_SECRET = os.getenv("ACCESS_TOKEN_SECRET")

# Authenticate with Twitter API v2 using OAuth 2.0
client = tweepy.Client(
    bearer_token=BEARER_TOKEN,
    consumer_key=API_KEY,
    consumer_secret=API_SECRET,
    access_token=ACCESS_TOKEN,
    access_token_secret=ACCESS_TOKEN_SECRET,
    wait_on_rate_limit=True
)

def fetch_user_tweets(username, timeframe=None):
    """Fetch recent tweets from a user."""
    try:
        user = client.get_user(username=username)
        user_id = user.data.id
        tweets = client.get_users_tweets(id=user_id, max_results=50, tweet_fields=["text", "created_at"])

        if not tweets.data:
            return []

        # Filter tweets by timeframe (if specified)
        if timeframe:
            now = time.time()
            timeframe_map = {
                "daily": now - 86400,  # 24 hours
                "weekly": now - 604800,  # 7 days
                "monthly": now - 2592000,  # 30 days
                "yearly": now - 31536000,  # 365 days
            }
            start_time = timeframe_map.get(timeframe)

            if start_time:
                tweets = [tweet for tweet in tweets.data if tweet.created_at.timestamp() >= start_time]

        return tweets
    except tweepy.TweepyException as e:
        print(f"Error fetching tweets: {e}")
        return []

def analyze_tweets(tweets):
    """Analyze the tweets for emoji and hashtags."""
    emoji_count = {}
    hashtag_count = {}

    for tweet in tweets:
        for char in tweet.text:
            if char in emoji.EMOJI_DATA:
                emoji_count[char] = emoji_count.get(char, 0) + 1
        for word in tweet.text.split():
            if word.startswith("#"):
                hashtag_count[word] = hashtag_count.get(word, 0) + 1

    return emoji_count, hashtag_count

def generate_stats(username, emoji_count, hashtag_count, timeframe=None):
    """Generate a stats summary."""
    top_emoji = max(emoji_count, key=emoji_count.get, default="None")
    top_hashtag = max(hashtag_count, key=hashtag_count.get, default="None")
    timeframe_text = f"({timeframe.capitalize()})" if timeframe else ""

    return (
        f"📊 @{username}'s Twitter Stats {timeframe_text}:\n"
        f"🔝 Top Emoji: {top_emoji}\n"
        f"🔝 Top Hashtag: {top_hashtag}\n"
        f"🎉 Total Emojis: {sum(emoji_count.values())}\n"
        f"🏷️ Total Hashtags: {sum(hashtag_count.values())}"
    )

def reply_to_mentions():
    """Listen for mentions and reply with stats."""
    last_mention_id = None
    while True:
        try:
            mentions = client.get_users_mentions(
                id=client.get_me().data.id,
                since_id=last_mention_id,
                tweet_fields=["text", "author_id", "referenced_tweets"]
            )

            if mentions.data:
                for mention in reversed(mentions.data):
                    referenced_tweets = mention.referenced_tweets
                    original_username = None

                    if referenced_tweets and referenced_tweets[0].type == "replied_to":
                        original_tweet_id = referenced_tweets[0].id
                        original_tweet = client.get_tweet(id=original_tweet_id, tweet_fields=["author_id"])
                        original_username = client.get_user(id=original_tweet.data.author_id).data.username

                    # Determine username and timeframe
                    mention_text = mention.text.lower()
                    timeframe = None
                    username = client.get_user(id=mention.author_id).data.username

                    if "my stats" in mention_text:
                        pass  # Keep username as the mention author
                    elif "their stats" in mention_text and original_username:
                        username = original_username
                    else:
                        continue  # Skip if command is invalid

                    for period in ["daily", "weekly", "monthly", "yearly"]:
                        if period in mention_text:
                            timeframe = period
                            break

                    # Fetch and analyze tweets
                    tweets = fetch_user_tweets(username, timeframe)
                    if tweets:
                        emoji_count, hashtag_count = analyze_tweets(tweets)
                        stats = generate_stats(username, emoji_count, hashtag_count, timeframe)
                        client.create_tweet(text=stats, in_reply_to_tweet_id=mention.id)
                        print(f"Replied to @{username} with {timeframe} stats")
                    else:
                        print(f"No tweets found for @{username}")
                    
                    last_mention_id = mention.id

            time.sleep(30)  # Sleep to avoid rate limits

        except tweepy.TooManyRequests as e:
            reset_time = int(e.response.headers.get("x-rate-limit-reset", time.time() + 60))
            sleep_time = reset_time - int(time.time())
            print(f"Rate limit reached. Sleeping for {sleep_time} seconds.")
            time.sleep(sleep_time)
        except tweepy.TweepyException as e:
            print(f"Error: {e}")
            time.sleep(60)  # Wait before retrying

if __name__ == "__main__":
    reply_to_mentions()
