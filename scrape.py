#!/usr/bin/env python

from PIL import Image
import pytesseract
import re
import twitter
import urllib
import io
import spotipy
import spotipy.util as util
from datetime import datetime

MOST_RECENT_TWEET_FILENAME='.dls-scrape'


ARTIST_REGEX=r'(.+)\s+(?:\-|\xe2\x80\x94)'
SONG_REGEX=r'\"(.*?)\"'
def extract_playlist_from_image(image_filename):
    text = pytesseract.image_to_string(Image.open(image_filename))
    artists = re.findall(ARTIST_REGEX, text)
    for artist in artists:
      text = re.sub(ARTIST_REGEX, '', text)
    songs = [re.sub(r'\s+', ' ', song) for song in
            re.findall(SONG_REGEX, text, flags=re.DOTALL)]
    min_pairs_found = min(len(artists), len(songs))
    max_pairs_found = max(len(artists), len(songs))
    if min_pairs_found != max_pairs_found:
      print 'Warning: only %d out of %d correctly parsed' % (min_pairs_found, max_pairs_found)
    return zip(artists[0:min_pairs_found], songs[0:min_pairs_found])

def get_or_create_DLS_playlist(spotify_api):
    offset = 0
    while True:
        playlists = spotify_api.user_playlists(SPOTIFY_USERNAME, offset=offset)
        for playlist in playlists['items']:
            if playlist['name'] == PLAYLIST_NAME:
                return playlist['id']
        if playlists['next']:
            offset = int(re.search(r'offset=(\d+)', playlists['next']).group(1))
        else:
            break
    # public by default, TODO: let user decide
    new_playlist = spotify_api.user_playlist_create(SPOTIFY_USERNAME, PLAYLIST_NAME)
    return new_playlist['id']

def get_recent_tweets():
  try:
    with open(MOST_RECENT_TWEET_FILENAME) as f:
      timestamp = int(f.read()) + 24*60*60 # advance the time by one day
      most_recent_datetime = str(datetime.fromtimestamp(timestamp))
      most_recent_date = most_recent_datetime.split(' ')[0]
      tweets = twitter_api.GetSearch(raw_query='q=from%3AMichaelRyanRuiz%20%23DLSplaylist%20since%3A' + most_recent_date)
      tweets.reverse()
      return tweets
  except IOError:
    tweets = twitter_api.GetSearch(raw_query='q=from%3AMichaelRyanRuiz%20%23DLSplaylist')
    tweets.reverse()
    return tweets

# Twitter API credentials
TWITTER_CONSUMER_KEY='126lnc7qVG5Nl3mS8pSYDcKUJ'
TWITTER_CONSUMER_SECRET='ZqiGIqcFz3VWRhY6t12fi6dNkleOm1pm0OXAbC7sohocFcMceI'
TWITTER_ACCESS_TOKEN_KEY='309526026-pDPB9s5elGiL5jqSfZKu3c4zOZNo5x52yWt3i14r'
TWITTER_ACCESS_TOKEN_SECRET='P00IUknFcK0q71VuIT2a8svckLqh7XsJLMBnDMSPR7LAh'

#Spotify API scope
SPOTIFY_API_SCOPE='''
playlist-modify-public playlist-modify-private playlist-read-private playlist-read-collaborative
'''
SPOTIFY_USERNAME='fabuzaid21'
PLAYLIST_NAME='The Dan LeBatard Show #DLSplaylist'

if __name__ == "__main__":
  spotify_token = util.prompt_for_user_token(SPOTIFY_USERNAME, SPOTIFY_API_SCOPE)

  if spotify_token:
      spotify_api = spotipy.Spotify(auth=spotify_token)
      # create playlist for the user if they don't have one already
      dls_playlist_id = get_or_create_DLS_playlist(spotify_api)

      twitter_api = twitter.Api(consumer_key=TWITTER_CONSUMER_KEY,
              consumer_secret=TWITTER_CONSUMER_SECRET,
              access_token_key=TWITTER_ACCESS_TOKEN_KEY,
              access_token_secret=TWITTER_ACCESS_TOKEN_SECRET)

      tweets = get_recent_tweets()
      if len(tweets) == 0:
          print 'No tweets found -- check back tomorrow!'
      most_recent_timestamp = None
      for tweet in tweets:
          tweet_media = tweet.media
          if len(tweet_media) == 1 and tweet_media[0].type == 'photo':
              print 'Adding songs from %s' % tweet.created_at
              if not most_recent_timestamp or tweet.created_at_in_seconds > most_recent_timestamp:
                  most_recent_timestamp = tweet.created_at_in_seconds
              photo_url = tweet_media[0].media_url
              photo_bytes = urllib.urlopen(photo_url).read()
              track_ids = []

              for artist, song in extract_playlist_from_image(io.BytesIO(photo_bytes)):
                  # search for song on Spotify API
                  search_results = spotify_api.search('%s %s' % (artist, song), limit=1, type='track')
                  if len(search_results['tracks']['items']) == 1:
                      track_ids.append(search_results['tracks']['items'][0]['id'])
                  else:
                      print "Couldn't find %s-%s on Spotify" % (artist, song)

              # add songs that were found to the playlist
              spotify_api.user_playlist_add_tracks(SPOTIFY_USERNAME, dls_playlist_id, track_ids)

      if most_recent_timestamp:
          with open(MOST_RECENT_TWEET_FILENAME, 'w') as f:
              f.write(str(most_recent_timestamp))
