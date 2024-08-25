import tweepy
import configparser
#Obsolete --> Twitter free API ⚠️
#Now use News API
def get_trending_topics(region):
    # Leer archivo de configuración
    config = configparser.ConfigParser()
    config.read('settings.config')

    # Obtener las credenciales de la API de Twitter desde el archivo de configuración
    API_KEY = config['TwitterAPI']['API_KEY']
    API_SECRET_KEY = config['TwitterAPI']['API_SECRET_KEY']
    ACCESS_TOKEN = config['TwitterAPI']['ACCESS_TOKEN']
    ACCESS_TOKEN_SECRET = config['TwitterAPI']['ACCESS_TOKEN_SECRET']

    # Autenticación con la API de Twitter
    auth = tweepy.OAuthHandler(API_KEY, API_SECRET_KEY)
    auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
    api = tweepy.API(auth)

    # Buscar el WOEID de la región especificada
    lugares = api.trends_available()
    woeid = None
    for lugar in lugares:
        if lugar['name'].lower() == region.lower():
            woeid = lugar['woeid']
            break
    
    if not woeid:
        print(f"Región '{region}' no encontrada.")
        return
    
    # Obtener las tendencias para la región
    tendencias = api.get_place_trends(woeid)
    for tendencia in tendencias[0]['trends']:
        print(f"#{tendencia['name']} - {tendencia['tweet_volume']} tweets")