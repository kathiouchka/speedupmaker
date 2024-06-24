import subprocess
import re
import os
from lyrics_fetcher import fetch_and_save_lyrics
from pydub import AudioSegment
import glob
import argparse
import random
import json
import numpy as np
import ffmpeg
import textwrap
from pydub import AudioSegment
from PIL import Image, ImageFont, ImageDraw
from moviepy.editor import VideoFileClip, CompositeVideoClip, AudioFileClip, ImageClip
from moviepy.video.fx.all import resize
import traceback

# Constants
SPEED_FACTOR = 1.14
DURATION = 31
FONT_PATH = "../Montserrat-Bold.ttf"
VIDEO_BACKGROUND_DIR = "./video_background"
FILE_EXTENSIONS_TO_CLEAN = [".mp3", ".json"]
FRENCH_STOPWORDS = ["le", "la", "les", "un", "une", "des", "et", "à", "de", "en", "du", "pour", "pas", "que", "qui", "ne", "se", "sur", "ce", "dans", "au", "il", "elle", "par", "avec", "est", "son", "plus", "ses", "mais", "comme", "tout", "nous", "sa", "aussi", "leur", "fait", "être", "cette", "leur", "sans", "aux", "leurs", "si", "ont", "même", "ces", "été", "ainsi", "entre", "quelle", "deux", "sont", "peut", "eux", "après", "dont", "sous", "autres", "où", "leurs", "devant", "celui", "tous", "quelques", "être", "cela", "cet", "encore", "cette", "leurs", "cette", "parce", "autre", "pendant", "alors", "depuis", "avoir", "peu", "elle", "elles", "c'était", "avant", "ainsi", "encore", "chaque", "beaucoup", "où", "tel", "telle", "tels", "telles"]
# Word and line colors
WORD_COLORS = ["#FFD700", "#FF6347", "#32CD32"]
LINE_COLORS = ["#F5F5F5", "#EDEDED", "#E5E5E5", "#DCDCDC", "#D3D3D3", "#C8C8C8"]


def is_valid_word(word):
        return len(word) >= 3 and word.lower() not in FRENCH_STOPWORDS


# External Commands Module
def run_command(cmd, cmd_queue):
    try:
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = process.communicate()
        
        if process.returncode == 0:
            cmd_queue.put((cmd, output.decode("utf-8"), None))
        else:
            cmd_queue.put((cmd, None, error.decode("utf-8")))
    except Exception as e:
        cmd_queue.put((cmd, None, str(e)))


def speed_up_audio(filename, speed_factor, duration_ms):
    try:
        song = AudioSegment.from_file(filename)
        song_fast = song.speedup(playback_speed=speed_factor)

        # Extract a segment from the beginning to duration_ms
        trimmed_song = song_fast[:duration_ms]
        trimmed_song.export("song_speed_up.wav", format="wav")
    except Exception as e:
        print(f"Error during audio speed up: {e}")

def speed_up_lyrics(filename, speed_factor):
    try:
        with open(filename, 'r') as f:
            lyrics_data = json.load(f)

        if 'error' in lyrics_data and lyrics_data['error'] == True:
            print(lyrics_data)
            print('Lyrics not available for this track.')
            return False

        # Iterate through each sentence
        for sentence in lyrics_data:
            # Iterate through each word in the sentence
            for word_info in sentence['words']:
                new_start_time_ms = int(word_info['startTimeMs']) / speed_factor
                new_end_time_ms = int(word_info['endTimeMs']) / speed_factor
                word_info['startTimeMs'] = str(max(0, int(new_start_time_ms)))
                word_info['endTimeMs'] = str(max(0, int(new_end_time_ms)))
                word_info['words'] = re.sub(r'\(.*?\)', '', word_info['words'])  # remove all text between parentheses

        with open("/home/kathiou/sp3/lyrics_speed_up.json", 'w', encoding='utf-8') as f:
            json.dump(lyrics_data, f, ensure_ascii=False, indent=4)

        return True
    except Exception as e:
        print(f"Error during lyrics speed up: {e}")
        return False


# File Operations Module
def get_latest_file_with_extension(extension):
    try:
        list_of_files = glob.glob(f'./*{extension}')
        latest_file = max(list_of_files, key=os.path.getctime)
        return latest_file
    except Exception as e:
        print(f"Error getting the latest file with extension {extension}: {e}")
        return None

def remove_files_with_extension(extension):
    try:
        filelist = glob.glob(os.path.join(".", f"*{extension}"))
        for f in filelist:
            os.remove(f)
    except Exception as e:
        print(f"Error removing files with extension {extension}: {e}")

def cleanup_files(keep_files=None):
    if keep_files is None:
        keep_files = ["./full_script.py", "./lyrics_fetcher.py", "./final_output.mp4", FONT_PATH, VIDEO_BACKGROUND_DIR]
        
    try:
        all_files = glob.glob(os.path.join(".", "*"))
        for f in all_files:
            if f not in keep_files and os.path.isfile(f):
                os.remove(f)
    except Exception as e:
        print(f"Error during cleanup: {e}")


# Video Processing Module
def process_videos(path, total_duration):
    try:
        files = os.listdir(path)
        video_files = [file for file in files if file.endswith(".mp4")]
        random.shuffle(video_files)

        input_files = [ffmpeg.input(os.path.join(path, file)) for file in video_files]

        filtered_files = []

        for input_file in input_files:
            v = input_file.video
            v = v.filter('scale', 1280, 720)
            v = v.filter('setsar', '1')  # Set the SAR to 1
            v = v.filter_('fade', type='in', start_frame=0, nb_frames=30)
            filtered_files.append(v)

        v = ffmpeg.concat(*filtered_files, v=1, a=0).node
        v = v[0].filter('setpts', 'PTS/{}'.format(SPEED_FACTOR))

        out = ffmpeg.output(v, 'out.mp4', t=total_duration)
        out = out.overwrite_output()
        out.run()
    except Exception as e:
        print(f"Error processing videos: {e}")

# Video and Image Rendering Module
def draw_text_with_shadow(draw, pos, text, font, fill_color, shadow_color=(0, 0, 0, 188)):
    x, y = pos
    shadow_offsets = [
        (-2, -2), (0, -2), (2, -2),
        (-2, 0),            (2, 0),
        (-2, 2),  (0, 2),  (2, 2),
    ]
    
    for offset_x, offset_y in shadow_offsets:
        draw.text((x + offset_x, y + offset_y), text, font=font, fill=shadow_color)
    draw.text((x, y), text, font=font, fill=fill_color)

def draw_line(draw, sentence, words_info, font, y_text, current_time, color_index, line_color_index):
    line_words = sentence.split(" ")
    line_width = draw.textsize(sentence, font=font)[0]
    x_text = (1080 - line_width) / 2

    for word in line_words:
        if '♪' in word:
            word = word.replace('♪', '')

        is_highlighted = False
        for word_info in words_info:
            start_time = int(word_info['startTimeMs']) / 1000
            end_time = int(word_info['endTimeMs']) / 1000

            # Check if the word matches by text and if the current time falls within its start and end time
            if word.upper() == word_info['words'] and start_time <= current_time < end_time:
                is_highlighted = True
                break

        word_font = font
        fill_color = WORD_COLORS[color_index % len(WORD_COLORS)] if is_highlighted else LINE_COLORS[line_color_index % len(LINE_COLORS)]

        draw_text_with_shadow(draw, (x_text, y_text), word + " ", word_font, fill_color, "black")
        x_text += draw.textsize(word + " ", word_font)[0]

    
def create_lyrics_video(lyrics_file, video_file, audio_file, color_index):
    try:
        with open(lyrics_file) as f:
            lyric_data = json.load(f)

        line_color_index = 0

        video = VideoFileClip(video_file).fx(resize, newsize=(1080, 1920))
        audio = AudioFileClip(audio_file)
        video = video.set_audio(audio)
        video_duration = video.duration

        font_path = FONT_PATH
        img_clips = []

        for sentence_data in lyric_data:
            sentence = sentence_data['sentence']
            words_info = sentence_data['words']
            if not sentence.strip():
                continue

            font_size = random.randint(65, 95)
            font = ImageFont.truetype(font_path, font_size)
            wrap_lines = textwrap.wrap(sentence, width=15)

            for i, word_info in enumerate(words_info):
                word_start_s = int(word_info['startTimeMs']) / 1000
                #  Extend the word duration to the start of the next word, if there is a next word
                if i < len(words_info) - 1:
                    next_word_start_s = int(words_info[i + 1]['startTimeMs']) / 1000
                    word_end_s = next_word_start_s
                else:
                    word_end_s = int(word_info['endTimeMs']) / 1000

                word_duration = word_end_s - word_start_s

                image = Image.new('RGBA', (1080, 1920), (0, 0, 0, 0))
                draw = ImageDraw.Draw(image)
                y_text = (1920 - len(wrap_lines) * draw.textsize("Sample text", font=font)[1]) / 2

                for line in wrap_lines:
                    draw_line(draw, line, words_info, font, y_text, word_start_s, color_index, line_color_index)
                    y_text += draw.textsize(line, font=font)[1]

                img_clip = ImageClip(np.array(image), duration=word_duration).set_position('center').set_start(word_start_s)
                img_clips.append(img_clip)
            color_index += 1
            line_color_index += 1


        final_clip = CompositeVideoClip([video] + img_clips, size=video.size)
        final_clip.set_duration(video_duration).write_videofile('final_output.mp4', codec='libx264', threads=4)

    except Exception as e:
        print(f"Error creating lyrics video: {e}")
        traceback.print_exc()


def clean_word(word):
    """Function to clean and standardize words for matching."""
    # Retain hyphens but remove other non-word characters and convert to uppercase
    return re.sub(r'[^\w\s]+', '', word.replace('-', ' ')).upper()

def group_json_by_sentences(original_lyrics_text, json_file_path):
    with open(json_file_path, 'r', encoding='utf-8') as file:
        word_timestamps = json.load(file)

    original_sentences = original_lyrics_text.replace('-', ' ').split('\n')
    sentence_structure = []
    current_word_index = 0

    for sentence in original_sentences:
        sentence_data = {"sentence": sentence, "words": []}
        words_in_sentence = [clean_word(word) for word in sentence.split()]

        while current_word_index < len(word_timestamps) and len(sentence_data["words"]) < len(words_in_sentence):
            word_data = word_timestamps[current_word_index]
            clean_json_word = clean_word(word_data["words"])

            if words_in_sentence[len(sentence_data["words"])] == clean_json_word:
                sentence_data["words"].append(word_data)
                current_word_index += 1
            else:
                current_word_index += 1

        sentence_structure.append(sentence_data)

    return sentence_structure



# Function to run the alignment script using Singularity
def run_alignment(input_audio, input_lyrics, output_file):

    # Construct the command
    command = f"cd NUSAutoLyrixAlign && singularity exec kaldi.simg ./RunAlignment.sh {input_audio} {input_lyrics} {output_file}"

    # Execute the command
    try:
        subprocess.run(command, shell=True, check=True)
        print(f"Alignment completed. Output file: {output_file}")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred during alignment: {e}")

def cut_audio(file_name, start_time_ms, artist, title):
    print(f"Attempting to cut audio. Start time: {start_time_ms} ms")
    
    # Load the audio file
    audio = AudioSegment.from_mp3(file_name)

    # Cut the audio from the specified start time
    if start_time_ms > 0:
        audio_cut = audio[start_time_ms:]

        # Save the edited file
        cut_file_name = "song_cut.mp3"
        audio_cut.export(cut_file_name, format="mp3")
        print(f"Audio cut successfully. Saved as {cut_file_name}")
        return cut_file_name
    else:
        print("No cutting required. Using original file.")
        return file_name

def is_valid_spotify_url(url):
    # Regular expression for validating Spotify track URL
    pattern = r'https?://open\.spotify\.com/track/[a-zA-Z0-9]+'
    return re.match(pattern, url) is not None


def download_track(spotify_url):
    try:
        # New command with additional arguments
        command = ["spotdl", spotify_url, "--config"]
        
        # Run the command
        result = subprocess.run(command, check=True, stdout=subprocess.PIPE, text=True)
        output_lines = result.stdout.split('\n')

        # Set the file name to 'song.mp3'
        file_name = 'song.mp3'
        metadata = {}
        print(output_lines)

        for line in output_lines:
            if line.startswith("Downloaded"):
                parts = line.split('"')[1].split(" - ")
                if len(parts) >= 2:
                    metadata["artist"], metadata["title"] = parts[0], parts[1]

        print(f"Extracted metadata: {metadata}") 
        print(f"File_name: {file_name}") 
        return file_name, metadata

    except subprocess.CalledProcessError as e:
        print(f"An error occurred while downloading: {e}")
        return None, None

    return None, None



def save_lyrics(artist, title, lyrics):
    # Create lyrics directory if it doesn't exist
    os.makedirs("lyrics", exist_ok=True)

    # Define the file path
    file_path = os.path.join("lyrics", f"{artist} - {title}.txt")

    # Save lyrics to the file
    with open(file_path, "w", encoding="utf-8") as file:
        file.write(lyrics)

    return file_path

def read_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

def split_compound_words(word):
    # Split compound words based on common delimiters like hyphens
    # This function can be expanded to handle other types of compound words as needed
    return word.replace('-', ' ').split()

def process_texts_for_json(original_text, aligned_text):
    # Split the original text into words, handling compound words
    original_words = []
    for word in original_text.split():
        original_words.extend(split_compound_words(word))

    # Print each word from original_words for debugging
    # print("Original Words:", original_words)

    # Split the aligned text into lines and then into words and timestamps
    aligned_lines = aligned_text.split('\n')
    processed_lines = []

    original_index = 0  # Index to keep track of position in the original text

    for line in aligned_lines:
        parts = line.split()
        if len(parts) == 3:  # Check if the line has three parts (start time, end time, word)
            start_time, end_time, word = parts

            # Convert time from seconds to milliseconds
            start_time_ms = str(int(float(start_time) * 1000))
            end_time_ms = str(int(float(end_time) * 1000))

            if word == 'BREATH*':
                # Replace 'BREATH*' with the correct word from the original text in all caps
                if original_index < len(original_words):
                    word = original_words[original_index].upper()
                    original_index += 1
            else:
                # If not 'BREATH*', just increase the index
                original_index += 1
            
            # print("Processed Word:", word)

            # Append the processed line to the result
            processed_lines.append({
                "startTimeMs": start_time_ms,
                "words": word,
                "endTimeMs": end_time_ms
            })

    return processed_lines

# Function to save the output to a JSON file
def save_to_json(data, filename):
    import json
    with open(filename, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

def main():
    try:
        parser = argparse.ArgumentParser(description="Script to process videos and lyrics")
        parser.add_argument('--delete', action='store_true', help='Delete all generated files')
        parser.add_argument('--process_videos', action='store_true', help='Process videos only')
        parser.add_argument('--create_lyrics_video', action='store_true', help='Process videos only')
        args = parser.parse_args()

        if args.process_videos:
            process_videos('./video_background', 60)  # Assuming default path and duration
            return
        if args.create_lyrics_video:
            color_index = random.randint(0, len(WORD_COLORS) - 1)
            create_lyrics_video('/home/kathiou/sp3/lyrics_speed_up.json', 'out.mp4', 'song_speed_up.wav', color_index)
            return
        if args.delete:
            cleanup_files()
            print("All generated files have been deleted.")
            return
        url = input("Enter a Spotify URL: ")
        duration_seconds = random.choice([DURATION])
        start_time_seconds = int(input("Enter the desired start time in seconds: "))
        start_time_ms = start_time_seconds * 1000

        if is_valid_spotify_url(url):
            downloaded_file, metadata = download_track(url)
            if downloaded_file:
                print(f"Downloaded file: {downloaded_file}")
                print(metadata)
                if metadata:
                    print("Lyrics exist, fetching and saving lyrics...")
                    fetch_and_save_lyrics(metadata["title"], metadata["artist"])
                    input("Review the fetched lyrics and press Enter to continue...")
                else:
                    print("No metadata found.")
        else:
            print("Invalid Spotify URL")
            return
        if downloaded_file:
            # Cut the audio if required
            cut_file_name = cut_audio(downloaded_file, start_time_ms, metadata["artist"], metadata["title"])
            print(f"Processed file: {cut_file_name}")
            cut_file_name = f"../song_cut.mp3".replace(" ", "_")
            lyrics_file = f"../lyrics/scrapedlyrics.txt".replace(" ", "_")
            lyrics_file_2 = f"lyrics/scrapedlyrics.txt".replace(" ", "_")
            aligned_file = f"../lyrics_aligned.txt".replace(" ", "_")
            aligned_file_2 = f"lyrics_aligned.txt".replace(" ", "_")

            # Run the alignment script
            run_alignment(cut_file_name, lyrics_file, aligned_file)
            processed_lines = process_texts_for_json(read_file(lyrics_file_2), read_file(aligned_file_2))
            #  Save the output to "lyrics.json"
            save_to_json(processed_lines, "lyrics.json")
            sentence_based_json = group_json_by_sentences(read_file(lyrics_file_2), "lyrics.json")
            save_to_json(sentence_based_json, "sentence_based_lyrics.json")
        else:
            print("No download")
            return

        filename_lyrics = "/home/kathiou/sp3/sentence_based_lyrics.json"
        filename_lyrics_speed_up = "/home/kathiou/sp3/lyrics_speed_up.json"

        lyrics_available = speed_up_lyrics(filename_lyrics, SPEED_FACTOR)

        if not lyrics_available:
            for ext in FILE_EXTENSIONS_TO_CLEAN:
                print("NO LYRICS WALLAH FDP")
                # remove_files_with_extension(ext)
            return

        filename_audio = get_latest_file_with_extension(".mp3")
        speed_up_audio(filename_audio, SPEED_FACTOR, duration_seconds * 1000)
        process_videos(VIDEO_BACKGROUND_DIR, duration_seconds)
        color_index = random.randint(0, len(WORD_COLORS) - 1)
        create_lyrics_video(filename_lyrics_speed_up, 'out.mp4', 'song_speed_up.wav', color_index)
        # cleanup_files()
    except Exception as e:
        print(f"Error in main function: {e}")

if __name__ == "__main__":
    main()
