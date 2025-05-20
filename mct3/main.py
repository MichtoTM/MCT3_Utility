import click
import eyed3
import os
import hashlib

@click.group()
def cli():
    """MCT3 Utilitaire en lignes de commandes pour modifier les métadonnées MP3 et analyser des fichiers."""
    pass

# === METADATA ===
@cli.group()
def metadata():
    """Lire les métadonnées"""
    pass

@metadata.command("read")
@click.argument("audio_file")
def read_metadata(audio_file):
    audio = eyed3.load(audio_file)
    if audio.tag is None:
        click.echo("Aucune métadonnée trouvée.")
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
        click.echo("Aucune parole trouvée.")

    if audio.tag.images:
        click.echo(f"Nombre d'images : {len(audio.tag.images)}")
    else:
        click.echo("Aucune image de pochette.")

# === COVER ===
@cli.group()
def cover():
    """Ajouter ou supprimer une pochette"""
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
    """Ajouter ou supprimer des paroles"""
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
    import requests
    import time
    import json
    from pathlib import Path
    
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
            click.echo(click.style(f"Analyse terminée : {malicious} détection(s) malveillante(s) sur {total} moteurs.", fg="green"))

            # Facultatif : afficher les moteurs ayant détecté quelque chose
            results = analysis_data["data"]["attributes"].get("results", {})
            for engine, result in results.items():
                if result.get("category") == "malicious":
                    click.echo(f"{engine} → {result.get('result', 'Détection')}")
            break
        else:
            time.sleep(3)
            wait_time += 3
            click.echo(f"En attente... ({wait_time} s)", nl=False)

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


@cli.command("remote-cmd")
@click.option("--ip", required=True, help="Adresse IP ou domaine du PC distant (ex: 192.168.1.23)")
@click.option("--key", required=True, help="Clé secrète d'authentification")
@click.option("--shell", type=click.Choice(['cmd', 'powershell']), default='cmd', show_default=True, help="Shell à utiliser")
@click.option("--command", required=True, help="Commande à exécuter")
def remote_cmd(ip, key, shell, command):
    """Envoyer une commande à un PC distant via HTTP (serveur Flask)"""
    import requests

    url = f"http://{ip}:5000/run"
    params = {
        "key": key,
        "cmd": command,
        "shell": shell
    }

    click.echo(click.style(f"Envoi de la commande vers {ip}...", fg="cyan"))
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        output = data.get("output", "Aucune sortie")
        click.echo(click.style("Réponse du serveur :", fg="green"))
        click.echo(output)
    except requests.RequestException as e:
        click.echo(click.style(f"Erreur lors de la requête : {e}", fg="red"))
    except ValueError:
        click.echo(click.style("Réponse invalide (pas du JSON)", fg="red"))

# === LANCEMENT ===
if __name__ == "__main__":
    cli()