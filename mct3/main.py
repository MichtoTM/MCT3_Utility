import click
import os
import hashlib
import lzma

import requests
import time
from pathlib import Path

@click.group()
def cli():
    """MCT3 Utilitary Tool for cmd and powershell."""
    pass

from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, APIC, USLT, ID3NoHeaderError
from mutagen.flac import FLAC, Picture

# === METADATA ===
@cli.group()
def metadata():
    """Read MP3 or FLAC metadata."""
    pass


@metadata.command("read")
@click.argument("audio_file")
def read_metadata(audio_file):
    """Display metadata information from an audio file."""
    if not os.path.isfile(audio_file):
        click.echo(click.style("File not found.", fg="red"))
        return

    ext = os.path.splitext(audio_file)[1].lower()

    try:
        if ext == ".mp3":
            audio = ID3(audio_file)
        elif ext == ".flac":
            audio = FLAC(audio_file)
        else:
            click.echo(click.style("Unsupported format. Only MP3 and FLAC are supported.", fg="red"))
            return
    except Exception as e:
        click.echo(click.style(f"Error reading file: {e}", fg="red"))
        return

    click.echo(click.style(f"\nMetadata for {os.path.basename(audio_file)}:\n", bold=True))

    # General tags
    if ext == ".mp3":
        for tag in ["TIT2", "TPE1", "TALB", "TDRC", "TCON", "TRCK"]:
            if tag in audio:
                click.echo(f"{tag}: {audio[tag].text[0]}")
        comments = [frame.text for frame in audio.getall("COMM")]
        if comments:
            click.echo(f"Comments: {' | '.join(comments)}")
    elif ext == ".flac":
        for key, value in audio.tags.items():
            click.echo(f"{key}: {', '.join(value)}")

    # Lyrics
    if ext == ".mp3":
        lyrics = [frame.text for frame in audio.getall("USLT")]
        if lyrics:
            click.echo("\nLyrics:\n" + lyrics[0])
        else:
            click.echo(click.style("No lyrics found.", fg="yellow"))
    elif ext == ".flac":
        if "lyrics" in audio.tags:
            click.echo("\nLyrics:\n" + audio.tags["lyrics"][0])
        else:
            click.echo(click.style("No lyrics found.", fg="yellow"))

    # Cover image
    has_cover = False
    if ext == ".mp3":
        if audio.getall("APIC"):
            has_cover = True
    elif ext == ".flac":
        if audio.pictures:
            has_cover = True

    click.echo(f"\nCover art: {'found' if has_cover else 'not found'}")


# === COVER ===
@cli.group()
def cover():
    """Add or remove cover art from a music file."""
    pass


@cover.command("add")
@click.argument("audio_file")
@click.option("--image", required=True, help="Path to the image (.jpg or .png).")
def add_cover(audio_file, image):
    """Attach a cover image to an MP3 or FLAC file."""
    if not os.path.isfile(audio_file) or not os.path.isfile(image):
        click.echo(click.style("Audio or image file not found.", fg="red"))
        return

    ext = os.path.splitext(audio_file)[1].lower()
    img_ext = os.path.splitext(image)[1].lower()

    mime = (
        "image/jpeg" if img_ext in [".jpg", ".jpeg"]
        else "image/png" if img_ext == ".png"
        else None
    )
    if not mime:
        click.echo(click.style("Unsupported image format.", fg="red"))
        return

    try:
        if ext == ".mp3":
            try:
                audio = ID3(audio_file)
            except ID3NoHeaderError:
                audio = ID3()
            with open(image, "rb") as img_data:
                audio.add(APIC(encoding=3, mime=mime, type=3, desc="Cover", data=img_data.read()))
            audio.save(audio_file)
        elif ext == ".flac":
            audio = FLAC(audio_file)
            pic = Picture()
            pic.type = 3
            pic.mime = mime
            with open(image, "rb") as img_data:
                pic.data = img_data.read()
            audio.add_picture(pic)
            audio.save()
        else:
            click.echo(click.style("Unsupported format. Only MP3 and FLAC are supported.", fg="red"))
            return

        click.echo(click.style("Cover art added successfully.", fg="green"))
    except Exception as e:
        click.echo(click.style(f"Error adding cover: {e}", fg="red"))


@cover.command("remove")
@click.argument("audio_file")
def remove_cover(audio_file):
    """Remove cover art from an MP3 or FLAC file."""
    if not os.path.isfile(audio_file):
        click.echo(click.style("File not found.", fg="red"))
        return

    ext = os.path.splitext(audio_file)[1].lower()

    try:
        if ext == ".mp3":
            audio = ID3(audio_file)
            audio.delall("APIC")
            audio.save()
        elif ext == ".flac":
            audio = FLAC(audio_file)
            audio.clear_pictures()
            audio.save()
        else:
            click.echo(click.style("Unsupported format. Only MP3 and FLAC are supported.", fg="red"))
            return

        click.echo(click.style("Cover art removed successfully.", fg="green"))
    except Exception as e:
        click.echo(click.style(f"Error removing cover: {e}", fg="red"))


# === LYRICS ===
@cli.group()
def lyrics():
    """Add or remove lyrics from MP3 or FLAC files."""
    pass


@lyrics.command("add")
@click.argument("audio_file")
@click.option("--lyrics", required=True, help="Path to a .txt or .lrc file containing lyrics.")
def add_lyrics(audio_file, lyrics):
    """Attach lyrics text to an audio file."""
    if not os.path.isfile(audio_file) or not os.path.isfile(lyrics):
        click.echo(click.style("Audio or lyrics file not found.", fg="red"))
        return

    try:
        with open(lyrics, "r", encoding="utf-8") as f:
            lyrics_text = f.read()
    except Exception as e:
        click.echo(click.style(f"Error reading lyrics: {e}", fg="red"))
        return

    ext = os.path.splitext(audio_file)[1].lower()

    try:
        if ext == ".mp3":
            try:
                audio = ID3(audio_file)
            except ID3NoHeaderError:
                audio = ID3()
            audio.add(USLT(encoding=3, lang="eng", desc="Lyrics", text=lyrics_text))
            audio.save(audio_file)
        elif ext == ".flac":
            audio = FLAC(audio_file)
            audio["lyrics"] = lyrics_text
            audio.save()
        else:
            click.echo(click.style("Unsupported format. Only MP3 and FLAC are supported.", fg="red"))
            return

        click.echo(click.style("Lyrics added successfully.", fg="green"))
    except Exception as e:
        click.echo(click.style(f"Error adding lyrics: {e}", fg="red"))


@lyrics.command("remove")
@click.argument("audio_file")
def remove_lyrics(audio_file):
    """Remove lyrics from an MP3 or FLAC file."""
    if not os.path.isfile(audio_file):
        click.echo(click.style("File not found.", fg="red"))
        return

    ext = os.path.splitext(audio_file)[1].lower()

    try:
        if ext == ".mp3":
            audio = ID3(audio_file)
            audio.delall("USLT")
            audio.save()
        elif ext == ".flac":
            audio = FLAC(audio_file)
            if "lyrics" in audio:
                del audio["lyrics"]
            audio.save()
        else:
            click.echo(click.style("Unsupported format. Only MP3 and FLAC are supported.", fg="red"))
            return

        click.echo(click.style("Lyrics removed successfully.", fg="green"))
    except Exception as e:
        click.echo(click.style(f"Error removing lyrics: {e}", fg="red"))

# === VTSCAN ===

@cli.command("vtscan")
@click.argument("file", type=click.Path(exists=True))


def virus_total_scan(file):
    """Analyse a file with VirusTotal API."""    
    try:
        token_path = Path(__file__).parent / "token.txt"
        with open(token_path, "r", encoding="utf-8") as token_file:
            API_KEY = token_file.read().strip()
            if not API_KEY:
                raise ValueError("Clé API vide.")
    except Exception as e:
        click.echo(click.style(f"Erreur : impossible de lire la clé API → {e}", fg="red"))
        return

    HEADERS = {
        "x-apikey": API_KEY
    }

    filepath = Path(file)

    if not filepath.exists():
        click.echo(click.style("Fichier introuvable.", fg="red"))
        return

    try:
        with open(filepath, "rb") as f:
            files = {"file": (filepath.name, f)}
            click.echo("Envoi du fichier à VirusTotal...")
            response = requests.post("https://www.virustotal.com/api/v3/files", files=files, headers=HEADERS)
    except Exception as e:
        click.echo(click.style(f"Erreur pendant l'envoi : {e}", fg="red"))
        return

    if response.status_code != 200:
        click.echo(click.style(f"Erreur HTTP : {response.status_code} - {response.text}", fg="red"))
        return

    analysis_id = response.json()["data"]["id"]
    click.echo(f"Fichier envoyé. ID de l'analyse : {analysis_id}")
    click.echo("Analyse en cours...")

    wait_time = 0
    while True:
        analysis_resp = requests.get(f"https://www.virustotal.com/api/v3/analyses/{analysis_id}", headers=HEADERS)
        analysis_data = analysis_resp.json()
        status = analysis_data["data"]["attributes"]["status"]

        if status == "completed":
            stats = analysis_data["data"]["attributes"].get("stats", {})
            malicious = stats.get("malicious", 0)
            total = sum(stats.values())
            click.echo(click.style(f"\nAnalyse terminée : {malicious} détection(s) malveillante(s) sur {total} moteurs.", fg="green"))

            # Facultatif : afficher les moteurs ayant détecté quelque chose
            results = analysis_data["data"]["attributes"].get("results", {})
            for engine, result in results.items():
                if result.get("category") == "malicious":
                    click.echo(f"{engine} → {result.get('result', 'Détection')}")
            break
        else:
            time.sleep(3)
            wait_time += 3
            click.echo(f"\rEn attente... ({wait_time} s)", nl=False)

# === HASH ===
@cli.command("hash")
@click.argument("file", type=click.Path(exists=True))
@click.option('--sha1', 'algo', flag_value='sha1', help="Utiliser SHA1")
@click.option('--sha256', 'algo', flag_value='sha256', help="Utiliser SHA256 (défaut)")
@click.option('--sha512', 'algo', flag_value='sha512', help="Utiliser SHA512")
@click.option('--md5', 'algo', flag_value='md5', help="Utiliser MD5")
@click.option('--compare', type=str, help="Comparer avec un hash existant")
def hash_file(file, algo, compare):
    """Calculate and/or campare hashes."""
    algo = algo or 'sha256'  # sha256 par défaut
    h = hashlib.new(algo)

    with open(file, 'rb') as f:
        chunk = f.read(8192)
        while chunk:
            h.update(chunk)
            chunk = f.read(8192)
    
       
    if h.hexdigest() == compare:
        click.echo(click.style(f"{algo.upper()} : {h.hexdigest()}", fg="green"))
        click.echo(click.style(f"Hash similaires.", fg="green", bold=True))
    elif compare is not None:
        click.echo(click.style(f"Hash différents :", fg="red", bold=True))
        click.echo(click.style(f"Attendu : {compare}", fg="yellow"))
        click.echo(click.style(f"Obtenu  : {h.hexdigest()}", fg="yellow"))
    else:
        click.echo(click.style(f"{algo.upper()} : {h.hexdigest()}", fg="green"))


# === STCFOLD ===
@cli.command("stcfold")
@click.option("--depth", default=None, type=int, help="Maximum depth to display (e.g., 2).")
@click.option("--folders-only", is_flag=True, help="Show only folders (hide files).")
def stcfold(depth, folders_only):
    """Display directory contents as a tree structure."""
    current_dir = os.getcwd()
    base_name = os.path.basename(current_dir)

    def walk(path, prefix="", level=0):
        if depth is not None and level >= depth:
            return

        try:
            entries = sorted(os.listdir(path))
        except PermissionError:
            click.echo(f"{prefix}└── [Access denied]")
            return

        entries_count = len(entries)
        for index, entry in enumerate(entries):
            full_path = os.path.join(path, entry)
            connector = "└── " if index == entries_count - 1 else "├── "

            if os.path.isdir(full_path):
                click.echo(f"{prefix}{connector}{click.style('📁 ' + entry + '/', fg='white', bold=True)}")
                new_prefix = prefix + ("    " if index == entries_count - 1 else "│   ")
                walk(full_path, new_prefix, level + 1)
            elif not folders_only:
                click.echo(f"{prefix}{connector}{click.style(entry, fg='green')}")

    # Header
    click.echo(click.style(f"📁 {base_name}/", fg="white", bold=True))
    click.echo("│")

    # Walk directory
    walk(current_dir)

    # Footer
    click.echo()
    click.echo(click.style(f"Command executed successfully in \"{current_dir}\".", fg="green", bold=True))

# === SPLIT AND ASSEMBLY ===
@cli.command("split")
@click.argument("file", type=click.Path(exists=True))
@click.option("--size", default=10, show_default=True, help="Taille max d’un segment en Mo.")
def split_file(file, size):
    """Split a file in 10MO segments using LZMA"""
    #show the original hash
    algo = 'sha256'  # sha256 par défaut
    h = hashlib.new(algo)

    with open(file, 'rb') as f:
        chunk = f.read(8192)
        while chunk:
            h.update(chunk)
            chunk = f.read(8192)

    click.echo(click.style(f"{algo.upper()} : {h.hexdigest()}", fg="green"))
    
    #split the file
    CHUNK_SIZE = size * 1024 * 1024  # 10 MB
    base_name = os.path.basename(file)
    output_dir = f"{base_name}_splits"
    os.makedirs(output_dir, exist_ok=True)
    #save hah.txt ion the new folder
    with open(os.path.join(output_dir, "hash.txt"), "w") as f:
        f.write(h.hexdigest())

    with open(file, "rb") as f:
        index = 0
        while chunk := f.read(CHUNK_SIZE):
            compressed_chunk = lzma.compress(chunk)
            part_path = os.path.join(output_dir, f"{base_name}.part{index:03d}.xz")
            with open(part_path, "wb") as part:
                part.write(compressed_chunk)
            click.echo(f"Segment {index+1} créé : {part_path}")
            index += 1

    click.echo(click.style("Découpage terminé.", fg="green"))


@cli.command("assembly")
@click.option("--output", default=None, help="Nom du fichier de sortie (facultatif).")
@click.option("--skip", default=False, is_flag=True, help="Ignorer la vérification du hash.")
def assembly(output,skip):
    """Assembles LZMA compressed segments and verifies integrity/."""

    folder = os.getcwd()
    
    if skip:
        click.echo(click.style("Vérification du hash ignorée.", fg="yellow"))
        expected_hash = None
    
    elif not os.path.exists("hash.txt"):
        expected_hash = click.prompt("SHA256 attendu du fichier original", type=str)

    else:
        with open(os.path.join(folder, "hash.txt"), "r") as f:
            expected_hash = f.read()
    
    # Lister et trier les fichiers .xz
    part_files = sorted(
        [f for f in os.listdir(folder) if f.endswith(".xz")],
        key=lambda x: int(x.split(".part")[1].split(".")[0])
    )

    if not part_files:
        click.echo(click.style("Aucun segment .xz trouvé dans le dossier.", fg="red"))
        return

    # Deviner le nom du fichier de base à partir du premier segment
    base_name = part_files[0].split(".part")[0]
    output_name = output if output else base_name
    output_path = os.path.join(os.getcwd(), output_name)

    click.echo(f"Assemblage des segments vers : {output_path}")

    with open(output_path, "wb") as out_f:
        for part in part_files:
            part_path = os.path.join(folder, part)
            with lzma.open(part_path, "rb") as pf:
                while chunk := pf.read(8192):
                    out_f.write(chunk)

    if expected_hash is None:
        return
    
    else:
        # Calcul du hash SHA256
        h = hashlib.sha256()
        with open(output_path, 'rb') as f:
            while chunk := f.read(8192):
                h.update(chunk)
        result_hash = h.hexdigest()

        if result_hash == expected_hash.lower():
            click.echo(click.style("Fichier reconstruit avec succès. Intégrité vérifié.", fg="green", bold=True))
        else:
            click.echo(click.style("Le hash ne correspond pas. Fichier corrompu ?", fg="red", bold=True))
            click.echo(f"Attendu : {expected_hash.lower()}")
            click.echo(f"Obtenu  : {result_hash}")

# === XYZ ===
@cli.command("xyz")
@click.argument("data1", type=str)
@click.argument("data2", type=str)

def xyz(data1, data2):
    """Calculate the distance between two 3D points."""
    import math
    import re

    def get_distance(data1, data2):
        data1 = re.split(r'[;,]', data1)
        data2 = re.split(r'[;,]', data2)

        if len(data1) == 3 and len(data2) == 3:
            x1, y1, z1 = float(data1[0]), float(data1[1]), float(data1[2])
            x2, y2, z2 = float(data2[0]), float(data2[1]), float(data2[2])

            distance = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2 + (z2 - z1) ** 2)
            return distance
        else:
            raise ValueError("Les données doivent contenir trois coordonnées.")

    try:
        distance = get_distance(data1, data2)
        click.echo(click.style(f"Distance : {distance:.4f}", fg="green"))
    except ValueError as e:
        click.echo(click.style(f"Erreur : {e}", fg="red"))

# === SPAM ===
@cli.command("emjspam")
@click.argument("char", type=str)
@click.argument("range", type=int)
@click.option("--separator", default="", help="Séparateur entre les caractères.")
@click.option("--last", is_flag=True, help="Conserver le dernier caractère.")

def emjspam(char, range, separator, last):
    """Repeat a string."""
    result = (char + separator) * range
    if not last:
        result = result.rstrip(separator) 
    
    click.echo(click.style(result, fg="green"))


@cli.command("version")
@click.option("--debug", is_flag=True, help="Afficher les messages d'erreur détaillés.")
def version(debug):
    """Shows MCT Version."""
    version_file = Path(__file__).parent / "version"
    version_str = None

    try:
        with open(version_file, "r", encoding="utf-8") as f:
            version_str = f.read().strip()
    except Exception as e:
        if debug:
            click.echo(click.style(f"Erreur lors de la lecture de la version : {e}", fg="red"))

    if version_str:
        click.echo(click.style(f"MCT Version: {version_str}", fg="blue"))
    else:
        click.echo(click.style(
            "Version non trouvée. Package probablement modifié ou corrompu, réinstallation recommandée.",
            fg="red"
        ))

# === FLAC TO MP3 ===
from pathlib import Path
import subprocess

@cli.command("flac2mp3")
@click.argument("source", required=False, type=click.Path(exists=True))
@click.option("--bitrate", default="320k", show_default=True, help="Bitrate du MP3 final")
@click.option("--recursive", is_flag=True, help="Parcourir les sous-dossiers")
def flac2mp3(source, bitrate, recursive):
    """
    Convert a FLAC into a MP3 using FFmpeg.
    """
    current_dir = Path.cwd()
    
    # Déterminer les fichiers à convertir
    if source:
        flac_files = [Path(source)]
    else:
        flac_files = list(current_dir.rglob("*.flac")) if recursive else list(current_dir.glob("*.flac"))

    if not flac_files:
        click.echo(click.style("Aucun fichier FLAC trouvé.", fg="yellow"))
        return

    click.echo(click.style(f"{len(flac_files)} fichier(s) FLAC à convertir.", fg="cyan"))

    for flac_path in flac_files:
        mp3_path = flac_path.with_suffix(".mp3")

        # Construction de la commande FFmpeg
        cmd = [
            "ffmpeg",
            "-y",                      # écrase sans demander
            "-i", str(flac_path),      # fichier source
            "-map", "0:a",             # map audio
            "-c:a", "libmp3lame",      # encodeur MP3
            "-b:a", bitrate,           # bitrate
            "-map", "0:v?",            # map video (pochette) si existante
            "-c:v", "copy",            # copie le flux image tel quel
            "-id3v2_version", "3",     # ID3v2.3
            "-write_id3v1", "1",       # écrit ID3v1
            str(mp3_path)
        ]

        # Exécution de FFmpeg
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            click.echo(click.style(f"Erreur lors de la conversion de {flac_path.name} :", fg="red"))
            click.echo(result.stderr)
        else:
            click.echo(click.style(f"✓ {flac_path.name} converti avec succès.", fg="green"))

    click.echo(click.style("Conversion terminée.", fg="cyan"))

# === LANCEMENT ===
if __name__ == "__main__":
    cli()