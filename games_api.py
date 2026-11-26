# games_api.py
import html
import random

import requests


# ---- Cartoon (Rick and Morty) API ----
def fetch_cartoon_images(count=8):
    """Fetches a list of random cartoon character image URLs from Rick and Morty API."""
    # Pick a random page (there are 42 pages of characters)
    page = random.randint(1, 42)
    url = f"https://rickandmortyapi.com/api/character/?page={page}"

    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json().get("results", [])

    if len(data) < count:
        raise ValueError("Not enough characters found.")

    # Randomly select the required number of characters
    selected = random.sample(data, count)
    return [char["image"] for char in selected]


# ---- Pokemon API ----
POKEAPI_URL = "https://pokeapi.co/api/v2/pokemon/"


def fetch_random_pokemon():
    # We limit to Gen 1 (1-151) so the names are recognizable
    random_id = random.randint(1, 151)
    response = requests.get(f"{POKEAPI_URL}{random_id}", timeout=10)
    response.raise_for_status()
    data = response.json()

    name = data["name"].capitalize()
    image_url = data["sprites"]["other"]["official-artwork"]["front_default"]

    # Fetch the image bytes
    img_response = requests.get(image_url, timeout=10)
    img_response.raise_for_status()
    image_data = img_response.content

    return name, image_data


def fetch_random_names(amount=3):
    """Fetches a few random wrong answers."""
    names = set()
    while len(names) < amount:
        random_id = random.randint(1, 151)
        response = requests.get(f"{POKEAPI_URL}{random_id}", timeout=5)
        if response.status_code == 200:
            names.add(response.json()["name"].capitalize())
    return list(names)


# ---- Trivia API ----
TRIVIA_URL = "https://opentdb.com/api.php"


def fetch_questions(amount=5, difficulty="medium"):
    params = {"amount": amount, "type": "multiple", "difficulty": difficulty}
    response = requests.get(TRIVIA_URL, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()
    if data["response_code"] != 0:
        raise ValueError("Trivia API returned an error.")
    # Unescape HTML entities that the API returns
    for q in data["results"]:
        q["question"] = html.unescape(q["question"])
        q["correct_answer"] = html.unescape(q["correct_answer"])
        q["incorrect_answers"] = [html.unescape(a) for a in q["incorrect_answers"]]
    return data["results"]
