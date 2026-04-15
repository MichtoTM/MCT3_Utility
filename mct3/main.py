import click
import os
import mimetypes
import base64
import lzma
import hashlib
import requests
import time
import math
import re
import psutil
import socket
import random
import string
import subprocess
from pathlib import Path
from mutagen import File
from mutagen.id3 import ID3, USLT, APIC
from mutagen.flac import Picture

# === FONCTIONS UTILITAIRES (AUDIO) ===

def get_audio(filepath):
    """Charge le fichier audio avec Mutagen et initialise les tags si absents."""
    if not os.path.isfile(filepath):
        click.echo(click.style(f"Fichier introuvable : {filepath}", fg="red"))
        return None
    try:
        audio = File(filepath)
        if audio is None:
            click.echo(click.style("Format audio non supporté ou invalide.", fg="red"))
            return None
        if getattr(audio, "tags", None) is None:
            audio.add_tags()
        return audio
    except Exception as e:
        click.echo(click.style(f"Erreur lors de la lecture : {e}", fg="red"))
        return None

def save_audio(audio, filepath, success_msg):
    """Sauvegarde le fichier audio et affiche un message de succès."""
    try:
        audio.save()
        click.echo(click.style(success_msg, fg="green"))
    except Exception as e:
        click.echo(click.style(f"Erreur lors de la sauvegarde : {e}", fg="red"))

# === CLI PRINCIPALE ===

@click.group()
def cli():
    """Outil utilitaire MCT3 pour cmd et powershell."""
    pass

# === METADATA ===

@cli.group()
def metadata():
    """Lire les métadonnées audio."""
    pass

@metadata.command("read")
@click.argument("audio_file")
def read_metadata(audio_file):
    """Affiche toutes les métadonnées d'un fichier audio sans doublons."""
    audio = get_audio(audio_file)
    if not audio: return

    click.echo(click.style(f"\n=== Métadonnées pour {os.path.basename(audio_file)} ===\n", bold=True))

    # Liste des clés de paroles à exclure de l'affichage général pour éviter les doublons
    lyrics_keys = ["lyrics", "LYRICS", "USLT"]

    # Tags généraux
    if audio.tags:
        for key, value in audio.tags.items():
            # On ignore les images brutes et les paroles dans cette boucle
            if (key != "metadata_block_picture" and 
                not isinstance(value, APIC) and 
                key.upper() not in [k.upper() for k in lyrics_keys]):
                
                val_str = ", ".join(map(str, value)) if isinstance(value, list) else str(value)
                click.echo(f"{key}: {val_str}")
    else:
        click.echo(click.style("Aucune métadonnée trouvée.", fg="yellow"))

    # Section Paroles dédiée
    click.echo(click.style("\n[Paroles]", bold=True))
    lyrics_found = False
    
    if isinstance(audio.tags, ID3):
        for frame in audio.tags.getall("USLT"):
            click.echo(frame.text)
            lyrics_found = True
    else:
        # Pour FLAC/OGG, on cherche 'lyrics' ou 'LYRICS'
        lyrics = audio.tags.get("lyrics") or audio.tags.get("LYRICS")
        if lyrics:
            click.echo(lyrics[0] if isinstance(lyrics, list) else lyrics)
            lyrics_found = True

    if not lyrics_found:
        click.echo(click.style("Aucune parole trouvée.", fg="yellow"))

    # Pochette (Cover)
    has_cover = False
    if isinstance(audio.tags, ID3):
        has_cover = bool(audio.tags.getall("APIC"))
    elif hasattr(audio, "pictures") and audio.pictures:
        has_cover = True
    elif "metadata_block_picture" in audio.tags:
        has_cover = True

    click.echo(f"\nPochette : {'Trouvée' if has_cover else 'Non trouvée'}")

# === COVER ===

@cli.group()
def cover():
    """Ajouter ou supprimer la pochette d'un fichier audio."""
    pass

@cover.command("add")
@click.argument("audio_file")
@click.option("--image", required=True, help="Chemin vers l'image (.jpg ou .png).")
def add_cover(audio_file, image):
    """Ajoute une image de pochette à un fichier audio."""
    audio = get_audio(audio_file)
    if not audio: return

    if not os.path.isfile(image):
        click.echo(click.style("Fichier image introuvable.", fg="red"))
        return

    mime_type, _ = mimetypes.guess_type(image)
    if not mime_type or not mime_type.startswith('image/'):
        click.echo(click.style("Format d'image non supporté.", fg="red"))
        return

    with open(image, "rb") as img_file:
        img_data = img_file.read()

    if isinstance(audio.tags, ID3):
        audio.tags.add(APIC(encoding=3, mime=mime_type, type=3, desc="Cover", data=img_data))
    elif hasattr(audio, "add_picture"): 
        pic = Picture()
        pic.type, pic.mime, pic.data = 3, mime_type, img_data
        audio.add_picture(pic)
    else:
        pic = Picture()
        pic.type, pic.mime, pic.data = 3, mime_type, img_data
        b64_pict = base64.b64encode(pic.write()).decode("ascii")
        audio.tags["metadata_block_picture"] = [b64_pict]

    save_audio(audio, audio_file, "Pochette ajoutée avec succès.")

@cover.command("remove")
@click.argument("audio_file")
def remove_cover(audio_file):
    """Supprime la pochette d'un fichier audio."""
    audio = get_audio(audio_file)
    if not audio: return

    if isinstance(audio.tags, ID3):
        audio.tags.delall("APIC")
    elif hasattr(audio, "clear_pictures"):
        audio.clear_pictures()
    else: 
        audio.tags.pop("metadata_block_picture", None)

    save_audio(audio, audio_file, "Pochette supprimée avec succès.")

# === LYRICS ===

@cli.group()
def lyrics():
    """Ajouter ou supprimer les paroles."""
    pass

@lyrics.command("add")
@click.argument("audio_file")
@click.option("--lyrics", "lyrics_file", required=True, help="Chemin vers le fichier contenant les paroles (.txt ou .lrc).")
def add_lyrics(audio_file, lyrics_file):
    """Associe des paroles textuelles à un fichier audio."""
    audio = get_audio(audio_file)
    if not audio: return

    try:
        with open(lyrics_file, "r", encoding="utf-8") as f:
            lyrics_text = f.read()
    except Exception as e:
        click.echo(click.style(f"Erreur de lecture du fichier texte : {e}", fg="red"))
        return

    if isinstance(audio.tags, ID3):
        audio.tags.add(USLT(encoding=3, lang="eng", desc="Lyrics", text=lyrics_text))
    else:
        audio.tags["lyrics"] = [lyrics_text]
    
    save_audio(audio, audio_file, "Paroles ajoutées avec succès.")

@lyrics.command("remove")
@click.argument("audio_file")
def remove_lyrics(audio_file):
    """Supprime les paroles d'un fichier audio."""
    audio = get_audio(audio_file)
    if not audio: return

    if isinstance(audio.tags, ID3):
        audio.tags.delall("USLT")
    else:
        audio.tags.pop("lyrics", None)
        audio.tags.pop("LYRICS", None)

    save_audio(audio, audio_file, "Paroles supprimées avec succès.")

# === VTSCAN ===

@cli.command("vtscan")
@click.argument("file", type=click.Path(exists=True))
def virus_total_scan(file):
    """Analyse un fichier avec l'API VirusTotal."""    
    try:
        token_path = Path(__file__).parent / "token.txt"
        with open(token_path, "r", encoding="utf-8") as token_file:
            API_KEY = token_file.read().strip()
            if not API_KEY:
                raise ValueError("Clé API vide.")
    except Exception as e:
        click.echo(click.style(f"Erreur : impossible de lire la clé API → {e}", fg="red"))
        return

    HEADERS = {"x-apikey": API_KEY}
    filepath = Path(file)

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
@click.option('--sha1', 'algo', flag_value='sha1', help="Utiliser l'algorithme SHA1.")
@click.option('--sha256', 'algo', flag_value='sha256', default=True, help="Utiliser l'algorithme SHA256 (par défaut).")
@click.option('--sha512', 'algo', flag_value='sha512', help="Utiliser l'algorithme SHA512.")
@click.option('--md5', 'algo', flag_value='md5', help="Utiliser l'algorithme MD5.")
@click.option('--compare', type=str, help="Comparer avec un hachage existant.")
def hash_file(file, algo, compare):
    """Calcule et/ou compare les hachages d'un fichier."""
    h = hashlib.new(algo)

    with open(file, 'rb') as f:
        chunk = f.read(8192)
        while chunk:
            h.update(chunk)
            chunk = f.read(8192)
    
    result_hash = h.hexdigest()
    
    if compare:
        if result_hash.lower() == compare.lower():
            click.echo(click.style(f"{algo.upper()} : {result_hash}", fg="green"))
            click.echo(click.style("Les hachages sont identiques.", fg="green", bold=True))
        else:
            click.echo(click.style("Les hachages sont différents :", fg="red", bold=True))
            click.echo(click.style(f"Attendu : {compare}", fg="yellow"))
            click.echo(click.style(f"Obtenu  : {result_hash}", fg="yellow"))
    else:
        click.echo(click.style(f"{algo.upper()} : {result_hash}", fg="green"))

# === STCFOLD ===
@cli.command("stcfold")
@click.option("--depth", default=None, type=int, help="Profondeur maximale à afficher (ex: 2).")
@click.option("--folders-only", is_flag=True, help="Afficher uniquement les dossiers (masquer les fichiers).")
def stcfold(depth, folders_only):
    """Affiche le contenu du répertoire sous forme d'arborescence."""
    current_dir = os.getcwd()
    base_name = os.path.basename(current_dir)

    def walk(path, prefix="", level=0):
        if depth is not None and level >= depth:
            return

        try:
            entries = sorted(os.listdir(path))
        except PermissionError:
            click.echo(f"{prefix}└── [Accès refusé]")
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

    click.echo(click.style(f"📁 {base_name}/", fg="white", bold=True))
    click.echo("│")
    walk(current_dir)
    
    click.echo()
    click.echo(click.style(f"Commande exécutée avec succès dans \"{current_dir}\".", fg="green", bold=True))

# === SPLIT AND ASSEMBLY (LZMA2) ===
@cli.command("split")
@click.argument("file", type=click.Path(exists=True))
@click.option("--size", default=10, show_default=True, help="Taille maximale d'un segment en Mo.")
def split_file(file, size):
    """Découpe un fichier en segments de 10 Mo compressés avec LZMA2."""
    h = hashlib.sha256()

    with open(file, 'rb') as f:
        while chunk := f.read(8192):
            h.update(chunk)

    original_hash = h.hexdigest()
    click.echo(click.style(f"SHA256 original : {original_hash}", fg="green"))
    
    CHUNK_SIZE = size * 1024 * 1024
    base_name = os.path.basename(file)
    output_dir = f"{base_name}_splits"
    os.makedirs(output_dir, exist_ok=True)
    
    with open(os.path.join(output_dir, "hash.txt"), "w") as f:
        f.write(original_hash)

    # Configuration explicite pour LZMA2
    lzma_filters = [{"id": lzma.FILTER_LZMA2, "preset": 9}]

    with open(file, "rb") as f:
        index = 0
        while chunk := f.read(CHUNK_SIZE):
            compressed_chunk = lzma.compress(chunk, format=lzma.FORMAT_XZ, filters=lzma_filters)
            part_path = os.path.join(output_dir, f"{base_name}.part{index:03d}.xz")
            with open(part_path, "wb") as part:
                part.write(compressed_chunk)
            click.echo(f"Segment {index+1} créé : {part_path}")
            index += 1

    click.echo(click.style("Découpage terminé.", fg="green"))

@cli.command("assembly")
@click.option("--output", default=None, help="Nom du fichier de sortie (facultatif).")
@click.option("--skip", default=False, is_flag=True, help="Ignorer la vérification du hachage.")
def assembly(output, skip):
    """Assemble des segments compressés LZMA2 et vérifie leur intégrité."""
    folder = os.getcwd()
    
    if skip:
        click.echo(click.style("Vérification du hachage ignorée.", fg="yellow"))
        expected_hash = None
    elif not os.path.exists("hash.txt"):
        expected_hash = click.prompt("Hachage SHA256 attendu du fichier original", type=str)
    else:
        with open(os.path.join(folder, "hash.txt"), "r") as f:
            expected_hash = f.read().strip()
    
    part_files = sorted(
        [f for f in os.listdir(folder) if f.endswith(".xz") and ".part" in f],
        key=lambda x: int(x.split(".part")[1].split(".")[0])
    )

    if not part_files:
        click.echo(click.style("Aucun segment .xz trouvé dans le dossier actuel.", fg="red"))
        return

    base_name = part_files[0].split(".part")[0]
    output_name = output if output else base_name
    output_path = os.path.join(folder, output_name)

    click.echo(f"Assemblage des segments vers : {output_path}")

    # Configuration explicite de lecture LZMA2
    lzma_filters = [{"id": lzma.FILTER_LZMA2}]

    with open(output_path, "wb") as out_f:
        for part in part_files:
            part_path = os.path.join(folder, part)
            with lzma.open(part_path, "rb", format=lzma.FORMAT_XZ, filters=lzma_filters) as pf:
                while chunk := pf.read(8192):
                    out_f.write(chunk)

    if expected_hash:
        h = hashlib.sha256()
        with open(output_path, 'rb') as f:
            while chunk := f.read(8192):
                h.update(chunk)
        result_hash = h.hexdigest()

        if result_hash == expected_hash.lower():
            click.echo(click.style("Fichier reconstruit avec succès. Intégrité vérifiée.", fg="green", bold=True))
        else:
            click.echo(click.style("Le hachage ne correspond pas. Fichier potentiellement corrompu.", fg="red", bold=True))
            click.echo(f"Attendu : {expected_hash.lower()}")
            click.echo(f"Obtenu  : {result_hash}")

# === XYZ ===
@cli.command("xyz")
@click.argument("data1", type=str)
@click.argument("data2", type=str)
def xyz(data1, data2):
    """Calcule la distance entre deux points 3D (format X,Y,Z ou X;Y;Z)."""
    def get_distance(p1, p2):
        p1 = re.split(r'[;,]', p1)
        p2 = re.split(r'[;,]', p2)

        if len(p1) == 3 and len(p2) == 3:
            x1, y1, z1 = float(p1[0]), float(p1[1]), float(p1[2])
            x2, y2, z2 = float(p2[0]), float(p2[1]), float(p2[2])
            return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2 + (z2 - z1) ** 2)
        else:
            raise ValueError("Les données doivent contenir exactement trois coordonnées.")

    try:
        distance = get_distance(data1, data2)
        click.echo(click.style(f"Distance : {distance:.4f}", fg="green"))
    except ValueError as e:
        click.echo(click.style(f"Erreur : {e}", fg="red"))

# === SPAM ===
@cli.command("emjspam")
@click.argument("char", type=str)
@click.argument("repeat_count", type=int)
@click.option("--separator", default="", help="Séparateur entre les caractères.")
@click.option("--last", is_flag=True, help="Conserver le séparateur à la fin de la chaîne.")
def emjspam(char, repeat_count, separator, last):
    """Répète une chaîne de caractères ou un emoji N fois."""
    result = (char + separator) * repeat_count
    if not last and separator:
        result = result.rstrip(separator) 
    click.echo(click.style(result, fg="green"))

# === LIST PORTS ===
@cli.command("checkports")
@click.argument("process_name")
def list_ports(process_name):
    """Liste tous les ports utilisés par un processus donné."""
    found = False
    for proc in psutil.process_iter(["name", "pid"]):
        try:
            if proc.info["name"] and process_name.lower() in proc.info["name"].lower():
                found = True
                click.echo(click.style(f"Processus : {proc.info['name']} (PID {proc.info['pid']})", fg="cyan"))
                connections = proc.net_connections(kind="inet")
                if not connections:
                    click.echo(click.style("  Aucune connexion active.", fg="yellow"))
                for conn in connections:
                    proto = "TCP" if conn.type == socket.SOCK_STREAM else "UDP"
                    laddr = f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else "-"
                    raddr = f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else "-"
                    click.echo(click.style(f"  {proto} → Local : {laddr}, Distant : {raddr}, Statut : {conn.status}", fg="green"))
                click.echo("-" * 40)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    if not found:
        click.echo(click.style(f"Aucun processus correspondant à '{process_name}' n'a été trouvé.", fg="yellow"))

#=== VERSION ===
@cli.command("version")
@click.option("--debug", is_flag=True, help="Afficher les messages d'erreur détaillés.")
def version(debug):
    """Affiche la version de MCT."""
    version_file = Path(__file__).parent / "version"
    version_str = None

    try:
        with open(version_file, "r", encoding="utf-8") as f:
            version_str = f.read().strip()
    except Exception as e:
        if debug:
            click.echo(click.style(f"Erreur lors de la lecture de la version : {e}", fg="red"))

    if version_str:
        click.echo(click.style(f"Version MCT : {version_str}", fg="blue"))
    else:
        click.echo(click.style(
            "Version non trouvée. Package probablement modifié ou corrompu, réinstallation recommandée.",
            fg="red"
        ))

# === FLAC TO MP3 ===
@cli.command("flac2mp3")
@click.argument("source", required=False, type=click.Path(exists=True))
@click.option("--bitrate", default="320k", show_default=True, help="Bitrate du MP3 final.")
@click.option("--recursive", is_flag=True, help="Parcourir également les sous-dossiers.")
def flac2mp3(source, bitrate, recursive):
    """Convertit des fichiers FLAC en MP3 à l'aide de FFmpeg."""
    current_dir = Path.cwd()
    
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
        cmd = [
            "ffmpeg", "-y", "-i", str(flac_path),
            "-map", "0:a", "-c:a", "libmp3lame", "-b:a", bitrate,
            "-map", "0:v?", "-c:v", "copy",
            "-map_metadata", "0", "-map_chapters", "0",
            "-id3v2_version", "3", "-write_id3v1", "1",
            str(mp3_path)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            click.echo(click.style(f"Erreur lors de la conversion de {flac_path.name} :", fg="red"))
            click.echo(result.stderr)
        else:
            click.echo(click.style(f"✓ {flac_path.name} converti avec succès.", fg="green"))

    click.echo(click.style("Conversion terminée.", fg="cyan"))

# ==== PASSWORDGEN ===
@cli.command("passgen")
@click.option("--length", default=12, help="Longueur du mot de passe.")
@click.option("--no-specials", is_flag=True, help="Exclure les caractères spéciaux.")
@click.option("--no-numbers", is_flag=True, help="Exclure les nombres.")
@click.option("--no-uppercase", is_flag=True, help="Exclure les lettres majuscules.")
@click.option("--no-lowercase", is_flag=True, help="Exclure les lettres minuscules.")
def passgen(length, no_specials, no_numbers, no_uppercase, no_lowercase):
    """Génère un mot de passe sécurisé et aléatoire."""
    pool = ""
    if not no_lowercase: pool += string.ascii_lowercase
    if not no_uppercase: pool += string.ascii_uppercase
    if not no_numbers: pool += string.digits
    if not no_specials: pool += "/*-+._@éè&!:%$?é;,"

    if not pool:
        click.echo(click.style("Erreur : Tous les types de caractères ont été exclus.", fg="red"))
        return

    password = "".join(random.choices(pool, k=length))
    click.echo(click.style(f"Mot de passe généré : {password}", fg="green", bold=True))

# === MC SEED GENERATOR ==
@cli.command("seedgen")
def seedgen():
    """Génère une seed aléatoire pour la génération de monde Minecraft."""
    seed = random.randint(-2**63, 2**63-1)
    click.echo(click.style(f"Seed Minecraft générée : {seed}", fg="green", bold=True))
    
# === LANCEMENT ===
if __name__ == "__main__":
    cli()