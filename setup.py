from setuptools import setup, find_packages

setup(
    name="mct3",
    version="1.0.0",
    packages=find_packages(),  # Recherche tous les packages dans le répertoire
    install_requires=[
        "eyed3",  # Liste des dépendances
        "click",  # Bibliothèque pour gérer les commandes
    ],
    entry_points={
        'console_scripts': [
            'mct3=mct3.main:cli',  # Assurez-vous de bien indiquer le chemin correct de la fonction cli()
        ],
    },
)