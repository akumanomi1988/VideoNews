import tweepy
import config

def get_trends():
    auth = tweepy.OAuthHandler(config.TWITTER_CONSUMER_KEY, config.TWITTER_CONSUMER_SECRET)
    auth.set_access_token(config.TWITTER_ACCESS_TOKEN, config.TWITTER_ACCESS_TOKEN_SECRET)
    twitter_api = tweepy.API(auth)
    trends = twitter_api.get_place_trends(id=1)  # WOEID 1 para tendencias globales
    return [trend["name"] for trend in trends[0]["trends"]]
