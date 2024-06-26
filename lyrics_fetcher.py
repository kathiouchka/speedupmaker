import os
import re
import lyricsgenius
import unicodedata

def save_lyrics_to_file(lyrics, song_name, artist_name):
    folder_path = 'lyrics'
    os.makedirs(folder_path, exist_ok=True)
    filename = "scrapedlyrics.txt"
    file_path = os.path.join(folder_path, filename)

    lyrics = preprocess_lyrics(lyrics)
    with open(file_path, 'w') as file:
        file.write(lyrics)
    print(f"Lyrics saved to {file_path}")

def preprocess_lyrics(lyrics):
    # Normalize and clean up the lyrics
    lyrics = unicodedata.normalize('NFKD', lyrics).encode('ascii', 'ignore').decode('ascii')
    lyrics = lyrics.lower()
    lyrics = re.sub(r'\([^)]*\)', '', lyrics)  # Remove parentheses
    lyrics = re.sub(r'\[[^\]]*\]', '', lyrics)  # Remove brackets
    lyrics = re.sub(r'Embed.*$', '', lyrics, flags=re.MULTILINE)
    lyrics = lyrics.replace(',', '').replace(':', '').replace("'", "")

    # Find the starting point of the lyrics
    start_index = find_start_index(lyrics)
    return lyrics[start_index:].strip()

def find_start_index(lyrics):
    patterns = [r'\[couplet\s+\d+.*?\]', r'\[verse\s+\d+.*?\]', r'\[couplet\s+unique.*?\]']
    for pattern in patterns:
        match = re.search(pattern, lyrics, re.IGNORECASE)
        if match:
            return match.start()
    print("No specific section label found. Using entire lyrics.")
    return 0

def fetch_lyrics(song_name, artist_name, access_token):
    genius = lyricsgenius.Genius(access_token)
    try:
        song = genius.search_song(song_name, artist_name)
        return song
    except Exception as e:
        print(f"Error fetching lyrics: {e}")
        return None

def fetch_and_save_lyrics(song_name, artist_name):
    access_token = os.getenv('GENIUS_ACCESS_TOKEN')
    if not access_token:
        print("Genius API token not found.")
        return

    print(f"Fetching lyrics for {song_name} by {artist_name} with token: {access_token}")
    song = fetch_lyrics(song_name, artist_name, access_token)
    if song:
        print(f"Lyrics found for {song_name} by {artist_name}")
        save_lyrics_to_file(song.lyrics, song_name, artist_name)
    else:
        print(f"Lyrics not found for {song_name} by {artist_name}.")

