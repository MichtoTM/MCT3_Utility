import click
import eyed3
import os
import hashlib
import lzma

import requests
import time
import json
from pathlib import Path

@click.group()
def cli():
    """MCT3 Utilitary Tool for cmd and powershell."""
    pass

# === METADATA ===
@cli.group()
def metadata():
    """Read MP3 metadata."""
    pass

@metadata.command("read")
@click.argument("audio_file")
def read_metadata(audio_file):
    audio = eyed3.load(audio_file)
    if audio.tag is None:
        click.echo(click.style("No metadata found."),fg='yellow')
        return

    click.echo(f"Titre : {audio.tag.title}")
    click.echo(f"Artiste : {audio.tag.artist}")
    click.echo(f"Album : {audio.tag.album}")
    click.echo(f"Année : {audio.tag.getBestDate()}")
    click.echo(f"Genre : {audio.tag.genre.name if audio.tag.genre else 'Inconnu'}")
    click.echo(f"Numéro de piste : {audio.tag.track_num}\n")  # Modification ici pour ajouter le saut de ligne
    click.echo("Commentaires :", nl=False)
    for c in audio.tag.comments:
        click.echo(f" {c.text}")

    if audio.tag.lyrics:
        for lyric in audio.tag.lyrics:
            click.echo(f"\nParoles :\n{lyric.text}")
    else:
        click.echo(click.style("No lyrics found."),fg='yellow')

    if audio.tag.images:
        click.echo(f"Nombre d'images : {len(audio.tag.images)}")
    else:
        click.echo(click.style("Aucune image de pochette."),fg='yellow')

# === COVER ===
@cli.group()
def cover():
    """Add or remove a MP3 cover."""
    pass

@cover.command("add")
@click.argument("audio_file")
@click.option("--image", required=True, help="Image à ajouter (.jpg/.png)")
def add_cover(audio_file, image):
    if not os.path.isfile(audio_file) or not os.path.isfile(image):
        click.echo(click.style("Fichier audio ou image introuvable.", fg="red"))
        return

    ext = os.path.splitext(image)[1].lower()
    mime = "image/jpeg" if ext in [".jpg", ".jpeg"] else "image/png" if ext == ".png" else None

    if not mime:
        click.echo(click.style("Format d'image non supporté.", fg="red"))
        return

    audio = eyed3.load(audio_file)
    if not audio:
        click.echo(click.style("Fichier audio non valide.", fg="red"))
        return

    if audio.tag is None:
        audio.initTag()

    with open(image, "rb") as img:
        audio.tag.images.set(3, img.read(), mime, u"cover")

    audio.tag.save()
    click.echo(click.style("Pochette ajoutée avec succès.", fg="green"))

@cover.command("remove")
@click.argument("audio_file")
def remove_cover(audio_file):
    if not os.path.isfile(audio_file):
        click.echo(click.style("Fihier introuvable.", fg="red"))
        return
    try:
        # Charger le fichier MP3
        audio = eyed3.load(audio_file)

        # Vérifier si le fichier a des tags
        if audio.tag is None:
            click.echo("Aucune métadonnée trouvée.")
            return

        # Supprimer toutes les images de couverture
        if audio.tag.images:
            for img in audio.tag.images:
                audio.tag.images.remove(img.description)  # Supprime chaque image par sa description
            audio.tag.save()
            click.echo(click.style("Pochette supprimée.", fg="green"))
        else:
            click.echo(click.style("Aucune pochette à supprimer.", fg="yellow"))
    except Exception as e:
        click.echo(click.style(f"Erreur lors de la suppression de la pochette : {e}",fg="red"))
# === LYRICS ===
@cli.group()
def lyrics():
    """Add or remove MP3 lyrics."""
    pass

@lyrics.command("add")
@click.argument("audio_file")
@click.option("--lyrics", required=True, help="Fichier .txt ou .lrc à ajouter")
def add_lyrics(audio_file, lyrics):
    if not os.path.isfile(audio_file) or not os.path.isfile(lyrics):
        click.echo(click.style("Fichier audio ou paroles introuvable.",fg="red"))
        return

    try:
        with open(lyrics, "r", encoding="utf-8") as f:
            lyrics_text = f.read()
    except Exception as e:
        click.echo(click.style(f"Erreur lors de la lecture des paroles : {e}",fg="red"))
        return

    audio = eyed3.load(audio_file)
    if not audio:
        click.echo(click.style("Fichier audio non valide.",fg="red"))
        return

    if audio.tag is None:
        audio.initTag()

    audio.tag.lyrics.set(lyrics_text)
    audio.tag.save()
    click.echo(click.style("Paroles ajoutées avec succès.",fg="green"))

@lyrics.command("remove")
@click.argument("audio_file")
def remove_lyrics(audio_file):
    if not os.path.isfile(audio_file):
        click.echo(click.style("Fichier introuvable.", fg="red"))
        return

    audio = eyed3.load(audio_file)
    if not audio or audio.tag is None or not audio.tag.lyrics:
        click.echo(click.style("Aucune parole à supprimer.", fg="yellow"))
        return

    # Suppression explicite de chaque objet lyrics par sa description (même vide)
    for lyric in list(audio.tag.lyrics):
        desc = lyric.description if lyric.description else ""
        audio.tag.lyrics.remove(desc)

    audio.tag.save()
    click.echo(click.style("Paroles supprimées.", fg="green"))


# === VTSCAN ===

@cli.command("vtscan")
@click.argument("file", type=click.Path(exists=True))


def virus_total_scan(file):
    """Analyser un fichier avec VirusTotal"""    
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
def hash_file(file, algo):
    """Calculer le hash d'un fichier en utilisant un algorithme choisi."""
    algo = algo or 'sha256'  # sha256 par défaut
    h = hashlib.new(algo)

    with open(file, 'rb') as f:
        chunk = f.read(8192)
        while chunk:
            h.update(chunk)
            chunk = f.read(8192)

    click.echo(click.style(f"{algo.upper()} : {h.hexdigest()}", fg="green"))


# === STCFOLD ===
@cli.command("stcfold")
def stcfold():
    """Lister tous les fichiers du répertoire"""
    current_dir = os.getcwd()
       
    def walk(path, level=0):
        entries = sorted(os.listdir(path))
        for entry in entries:
            full_path = os.path.join(path, entry)
            indent = "  " * level
            if os.path.isdir(full_path):
                click.echo(f"{indent}{click.style(entry + '/', fg='white', bold=True)}")
                walk(full_path, level + 1)
            else:
                click.echo(f"{indent}{click.style(entry, fg='green')}")

        if not entries:
            click.echo(click.style('Aucun fichier ou dossier trouvé.', fg='yellow'))

        click.echo(click.style(f"La commande exécutée dans \"{current_dir}\" s'est terminée correctement.", fg="green", bold=True))
    

    walk(current_dir)

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
    """Assemble les segments compressés LZMA et vérifie leur intégrité avec un SHA256"""

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
    """Calculer la distance entre deux points 3D."""
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
    """Répéter une chaîne de caractères."""
    result = (char + separator) * range
    if not last:
        result = result.rstrip(separator) 
    
    click.echo(click.style(result, fg="green"))


@cli.command("version")
@click.option("--debug", is_flag=True, help="Afficher les messages d'erreur détaillés.")
def version(debug):
    """Afficher la version de MCT."""
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


# === LANCEMENT ===
if __name__ == "__main__":
    cli()