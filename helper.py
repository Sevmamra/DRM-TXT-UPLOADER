import os
import subprocess
import mmap
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from io import BytesIO
import logging
import subprocess
import datetime
import asyncio
import os
import requests
import time
from p_bar import progress_bar
import aiohttp
import aiofiles
import tgcrypto
import concurrent.futures
from pyrogram.types import Message
from pyrogram import Client, filters
from pathlib import Path  
import re
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from base64 import b64decode

# Same AES Key aur IV jo encryption ke liye use kiya tha
KEY = b'^#^#&@*HDU@&@*()'   
IV = b'^@%#&*NSHUE&$*#)'   

# Decryption function
def dec_url(enc_url):
    enc_url = enc_url.replace("helper://", "")  # "helper://" prefix hatao
    cipher = AES.new(KEY, AES.MODE_CBC, IV)
    decrypted = unpad(cipher.decrypt(b64decode(enc_url)), AES.block_size)
    return decrypted.decode('utf-8')

# Function to split name & Encrypted URL properly
def split_name_enc_url(line):
    match = re.search(r"(helper://\S+)", line)  # Find `helper://` ke baad ka encrypted URL
    if match:
        name = line[:match.start()].strip().rstrip(":")  # Encrypted URL se pehle ka text
        enc_url = match.group(1).strip()  # Sirf Encrypted URL
        return name, enc_url
    return line.strip(), None  # Agar encrypted URL nahi mila, to pura line name maan lo

# Function to decrypt file URLs
def decrypt_file_txt(input_file):
    output_file = "decrypted_" + input_file  # Output file ka naam

    # Ensure the directory exists
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open(input_file, "r", encoding="utf-8") as f, open(output_file, "w", encoding="utf-8") as out:
        for line in f:
            name, enc_url = split_name_enc_url(line)  # Sahi tarike se name aur encrypted URL split karo
            if enc_url:
                dec = dec_url(enc_url)  # Decrypt URL
                out.write(f"{name}: {dec}\n")  # Ek hi `:` likho
            else:
                out.write(line.strip() + "\n")  # Agar encrypted URL nahi mila to line jaisa hai waisa likho

    return output_file   # Decrypted file ka naam return karega
   
def duration(filename):   
    result = subprocess.run(["ffprobe", "-v", "error", "-show_entries",   
                             "format=duration", "-of",   
                             "default=noprint_wrappers=1:nokey=1", filename],   
        stdout=subprocess.PIPE,   
        stderr=subprocess.STDOUT)   
    return float(result.stdout)
   
def get_mps_and_keys(api_url):
    response = requests.get(api_url)
    response_json = response.json()
    mpd = response_json.get('MPD')
    keys = response_json.get('KEYS')
    return mpd, keys
   
def exec(cmd):   
        process = subprocess.run(cmd, stdout=subprocess.PIPE,stderr=subprocess.PIPE)   
        output = process.stdout.decode()   
        print(output)   
        return output   
        #err = process.stdout.decode()   
def pull_run(work, cmds):   
    with concurrent.futures.ThreadPoolExecutor(max_workers=work) as executor:   
        print("Waiting for tasks to complete")   
        fut = executor.map(exec,cmds)   
async def aio(url,name):   
    k = f'{name}.pdf'   
    async with aiohttp.ClientSession() as session:   
        async with session.get(url) as resp:   
            if resp.status == 200:   
                f = await aiofiles.open(k, mode='wb')   
                await f.write(await resp.read())   
                await f.close()   
    return k   
   
   
async def download(url,name):   
    ka = f'{name}.pdf'   
    async with aiohttp.ClientSession() as session:   
        async with session.get(url) as resp:   
            if resp.status == 200:   
                f = await aiofiles.open(ka, mode='wb')   
                await f.write(await resp.read())   
                await f.close()   
    return ka   
   
async def pdf_download(url, file_name, chunk_size=1024 * 10):
    if os.path.exists(file_name):
        os.remove(file_name)
    r = requests.get(url, allow_redirects=True, stream=True)
    with open(file_name, 'wb') as fd:
        for chunk in r.iter_content(chunk_size=chunk_size):
            if chunk:
                fd.write(chunk)
    return file_name   
   
def parse_vid_info(info):   
    info = info.strip()   
    info = info.split("\n")   
    new_info = []   
    temp = []   
    for i in info:   
        i = str(i)   
        if "[" not in i and '---' not in i:   
            while "  " in i:   
                i = i.replace("  ", " ")   
            i.strip()   
            i = i.split("|")[0].split(" ",2)   
            try:   
                if "RESOLUTION" not in i[2] and i[2] not in temp and "audio" not in i[2]:   
                    temp.append(i[2])   
                    new_info.append((i[0], i[2]))   
            except:   
                pass   
    return new_info   
   
   
def vid_info(info):   
    info = info.strip()   
    info = info.split("\n")   
    new_info = dict()   
    temp = []   
    for i in info:   
        i = str(i)   
        if "[" not in i and '---' not in i:   
            while "  " in i:   
                i = i.replace("  ", " ")   
            i.strip()   
            i = i.split("|")[0].split(" ",3)   
            try:   
                if "RESOLUTION" not in i[2] and i[2] not in temp and "audio" not in i[2]:   
                    temp.append(i[2])   
                       
                    # temp.update(f'{i[2]}')   
                    # new_info.append((i[2], i[0]))   
                    #  mp4,mkv etc ==== f"({i[1]})"    
                       
                    new_info.update({f'{i[2]}':f'{i[0]}'})   
   
            except:   
                pass   
    return new_info   
   
   
async def decrypt_and_merge_video(mpd_url, keys_string, output_path, output_name, quality="720"):
    try:
        output_path = Path(output_path)
        output_path.mkdir(parents=True, exist_ok=True)

        cmd1 = f'yt-dlp -f "bv[height<={quality}]+ba/b" -o "{output_path}/file.%(ext)s" --allow-unplayable-format --no-check-certificate --external-downloader aria2c "{mpd_url}"'
        print(f"Running command: {cmd1}")
        os.system(cmd1)
        
        avDir = list(output_path.iterdir())
        print(f"Downloaded files: {avDir}")
        print("Decrypting")

        video_decrypted = False
        audio_decrypted = False

        for data in avDir:
            if data.suffix == ".mp4" and not video_decrypted:
                cmd2 = f'mp4decrypt {keys_string} --show-progress "{data}" "{output_path}/video.mp4"'
                print(f"Running command: {cmd2}")
                os.system(cmd2)
                if (output_path / "video.mp4").exists():
                    video_decrypted = True
                data.unlink()
            elif data.suffix == ".m4a" and not audio_decrypted:
                cmd3 = f'mp4decrypt {keys_string} --show-progress "{data}" "{output_path}/audio.m4a"'
                print(f"Running command: {cmd3}")
                os.system(cmd3)
                if (output_path / "audio.m4a").exists():
                    audio_decrypted = True
                data.unlink()

        if not video_decrypted or not audio_decrypted:
            raise FileNotFoundError("Decryption failed: video or audio file not found.")

        cmd4 = f'ffmpeg -i "{output_path}/video.mp4" -i "{output_path}/audio.m4a" -c copy "{output_path}/{output_name}.mp4"'
        print(f"Running command: {cmd4}")
        os.system(cmd4)
        if (output_path / "video.mp4").exists():
            (output_path / "video.mp4").unlink()
        if (output_path / "audio.m4a").exists():
            (output_path / "audio.m4a").unlink()
        
        filename = output_path / f"{output_name}.mp4"

        if not filename.exists():
            raise FileNotFoundError("Merged video file not found.")

        cmd5 = f'ffmpeg -i "{filename}" 2>&1 | grep "Duration"'
        duration_info = os.popen(cmd5).read()
        print(f"Duration info: {duration_info}")

        return str(filename)

    except Exception as e:
        print(f"Error during decryption and merging: {str(e)}")
        raise
       
async def run(cmd):   
    proc = await asyncio.create_subprocess_shell(   
        cmd,   
        stdout=asyncio.subprocess.PIPE,   
        stderr=asyncio.subprocess.PIPE)   
   
    stdout, stderr = await proc.communicate()   
   
    print(f'[{cmd!r} exited with {proc.returncode}]')   
    if proc.returncode == 1:   
        return False   
    if stdout:   
        return f'[stdout]\n{stdout.decode()}'   
    if stderr:   
        return f'[stderr]\n{stderr.decode()}'   
   
       
       
       
def old_download(url, file_name, chunk_size = 1024 * 10):   
    if os.path.exists(file_name):   
        os.remove(file_name)   
    r = requests.get(url, allow_redirects=True, stream=True)   
    with open(file_name, 'wb') as fd:   
        for chunk in r.iter_content(chunk_size=chunk_size):   
            if chunk:   
                fd.write(chunk)   
    return file_name   
   
   
def human_readable_size(size, decimal_places=2):   
    for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB']:   
        if size < 1024.0 or unit == 'PB':   
            break   
        size /= 1024.0   
    return f"{size:.{decimal_places}f} {unit}"   
   
   
def time_name():   
    date = datetime.date.today()   
    now = datetime.datetime.now()   
    current_time = now.strftime("%H%M%S")   
    return f"{date} {current_time}.mp4"   
   
async def download_video(url,cmd, name):   
    download_cmd = f'{cmd} -R 25 --fragment-retries 25 --external-downloader aria2c --downloader-args "aria2c: -x 16 -j 32" --cookies cookies.txt'   
    global failed_counter   
    print(download_cmd)   
    logging.info(download_cmd)   
    k = subprocess.run(download_cmd, shell=True)   
    if "visionias" in cmd and k.returncode != 0 and failed_counter <= 10:   
        failed_counter += 1   
        await asyncio.sleep(1)   
        await download_video(url, cmd, name)   
    failed_counter = 0   
    try:   
        if os.path.isfile(name):   
            return name   
        elif os.path.isfile(f"{name}.webm"):   
            return f"{name}.webm"   
        name = name.split(".")[0]   
        if os.path.isfile(f"{name}.mkv"):   
            return f"{name}.mkv"   
        elif os.path.isfile(f"{name}.mp4"):   
            return f"{name}.mp4"   
        elif os.path.isfile(f"{name}.mp4.webm"):   
            return f"{name}.mp4.webm"   
   
        return name   
    except FileNotFoundError as exc:   
        return os.path.isfile.splitext[0] + "." + "mp4"   
   
async def send_doc(bot: Client, m: Message,cc,ka,cc1,prog,count,name):   
    reply = await m.reply_text(f"Uploading - `{name}`")   
    time.sleep(1)   
    start_time = time.time()   
    await m.reply_document(ka,caption=cc1)   
    count+=1   
    await reply.delete (True)   
    time.sleep(1)   
    os.remove(ka)   
    time.sleep(2)

def decrypt_file(file_path, key):  
    if not os.path.exists(file_path): 
        return False  

    with open(file_path, "r+b") as f:  
        num_bytes = min(28, os.path.getsize(file_path))  
        with mmap.mmap(f.fileno(), length=num_bytes, access=mmap.ACCESS_WRITE) as mmapped_file:  
            for i in range(num_bytes):  
                mmapped_file[i] ^= ord(key[i]) if i < len(key) else i 
    return True  

async def download_and_decrypt_video(url, cmd, name, key):  
    video_path = await download_video(url, cmd, name)  
    
    if video_path:  
        decrypted = decrypt_file(video_path, key)  
        if decrypted:  
            print(f"File {video_path} decrypted successfully.")  
            return video_path  
        else:  
            print(f"Failed to decrypt {video_path}.")  
            return None  

async def download_and_decrypt_pdf(url, name, key):  
    download_cmd = f'yt-dlp -o "{name}.pdf" "{url}" -R 25 --fragment-retries 25'  
    try:  
        subprocess.run(download_cmd, shell=True, check=True)  
        print(f"Downloaded PDF: {name}.pdf")  
    except subprocess.CalledProcessError as e:  
        print(f"Error during download: {e}")  
        return False  
    
    file_path = f"{name}.pdf"  
    if not os.path.exists(file_path):  
        print(f"The file {file_path} does not exist.")  
        return False  

    try:  
        with open(file_path, "r+b") as f: 
            num_bytes = min(28, os.path.getsize(file_path))  
            with mmap.mmap(f.fileno(), length=num_bytes, access=mmap.ACCESS_WRITE) as mmapped_file:  
                for i in range(num_bytes):  
                    mmapped_file[i] ^= ord(key[i]) if i < len(key) else i  

        print(f"Decryption completed for {file_path}.") 
        return file_path 
    except Exception as e:  
        print(f"Error during decryption: {e}")  
        return False

   

#-----------------------Emoji handler------------------------------------

EMOJIS = ["🔥", "💥", "👨‍❤️‍💋‍👨", "👱🏻", "👻", "⚡", "💫", "🐟", "🦅", "🌹", "🦋"]
emoji_counter = 0  # Initialize a global counter

def get_next_emoji():
    global emoji_counter
    emoji = EMOJIS[emoji_counter]
    emoji_counter = (emoji_counter + 1) % len(EMOJIS)
    return emoji


async def send_vid(bot: Client, m: Message,cc,filename,thumb,name,prog):   
       
    emoji = get_next_emoji()
    subprocess.run(f'ffmpeg -i "{filename}" -ss 00:00:02 -vframes 1 "{filename}.jpg"', shell=True)   
    await prog.delete (True)   
    reply = await m.reply_text(f"🚀🚀𝗨𝗣𝗟𝗢𝗔𝗗𝗜𝗡𝗚🚀🚀🚀** » `{name}`\n\n🤖𝗕𝗢𝗧 𝗠𝗔𝗗𝗘 𝗕𝗬 ➤ 𝐂𝐀 𝐈𝐧𝐭𝐞𝐫 𝐗")   
    try:   
        if thumb == "no":   
            thumbnail = f"{filename}.jpg"   
        else:   
            thumbnail = thumb   
    except Exception as e:   
        await m.reply_text(str(e))   
   
    dur = int(duration(filename))
    processing_msg = await m.reply_text(emoji) 
   
    start_time = time.time()   
   
    try:   
        await m.reply_video(filename,caption=cc, supports_streaming=True,height=720,width=1280,thumb=thumbnail,duration=dur, progress=progress_bar,progress_args=(reply,start_time))   
    except Exception:   
        await m.reply_document(filename,caption=cc, progress=progress_bar,progress_args=(reply,start_time))   
    os.remove(filename)   
   
    os.remove(f"{filename}.jpg")
    await processing_msg.delete(True)
    await reply.delete (True) 


async def watermark_pdf(file_path, watermark_text):
    def create_watermark(text):
        """Create a PDF watermark using ReportLab."""
        packet = BytesIO()
        can = canvas.Canvas(packet, pagesize=letter)

        # Page dimensions
        width, height = letter

        # Set font, size, and color
        can.setFont("Helvetica", 40)
        can.setFillColorRGB(0.6, 0.6, 0.6, alpha=0.5)  # Semi-transparent gray

        # Rotate canvas and draw text in center
        can.saveState()
        can.translate(width / 2, height / 2)
        can.rotate(45)

        # Split text into lines
        lines = text.split('\n')
        line_height = 50  # Adjust line spacing
        for i, line in enumerate(lines):
            text_width = can.stringWidth(line, "Helvetica", 40)
            can.drawString(-text_width / 2, -i * line_height, line)

        can.restoreState()
        can.save()
        packet.seek(0)
        return PdfReader(packet)

    # Create watermark PDF
    watermark = create_watermark(watermark_text)
    reader = PdfReader(file_path)
    writer = PdfWriter()

    # Add watermark to each page
    for page_num in range(len(reader.pages)):
        page = reader.pages[page_num]
        watermark_page = watermark.pages[0]
        page.merge_page(watermark_page)
        writer.add_page(page)

    # Output file
    new_file_path = file_path.replace(".pdf", "_.pdf")
    with open(new_file_path, 'wb') as out_file:
        writer.write(out_file)

    # Delete the original file
    os.remove(file_path)

    return new_file_path
       
   
