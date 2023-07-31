from random import random, randint
from datetime import datetime
import random
import json
import re
import csv
from io import BytesIO
import os

import boto3
import requests
from bs4 import BeautifulSoup
from flask import (
    Flask,
    render_template,
    redirect,
    url_for,
    flash,
    request,
    jsonify,
    session,
)
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate
from flask_pymongo import PyMongo
from pymongo import MongoClient
from bson import ObjectId
from bson.errors import InvalidId
from werkzeug.security import generate_password_hash, check_password_hash
from wtforms import (
    FloatField,
    SubmitField,
    DateField,
    StringField,
    PasswordField,
    validators,
    RadioField,
)
from wtforms.validators import DataRequired, InputRequired
from dotenv import load_dotenv
import bcrypt
from boto3.resources import collection
import openai

# Initialize Flask app
app = Flask(__name__)

# Load environment variables from .env file
load_dotenv()

# Set up MongoDB connection
mongo_uri = f"mongodb://{os.getenv('MONGOUSER')}:{os.getenv('MONGOPASSWORD')}@{os.getenv('MONGOHOST')}:{os.getenv('MONGOPORT')}/{os.getenv('MONGODATABASE')}"
mongo_uri = (
    "mongodb://mongo:gVki9cxV2NTZkzCM4tOb@containers-us-west-57.railway.app:7203"
)
app.config["MONGO_URI"] = mongo_uri

client = MongoClient(mongo_uri)

# Access the database
db = client["database_name"]  # Replace 'database_name' with your actual database name

# Access the collection
collection = db["recipes"]


# Initialize CSRF protection
csrf = CSRFProtect(app)

mongo = PyMongo(app)


# OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

# Sample random ingredient function
def get_random_foods_from_csv(file_path):
    with open(file_path, "r") as csvfile:
        reader = csv.reader(csvfile)
        food_list = list(reader)
    num_items = random.randint(1, 10)
    random_foods = random.sample(food_list, num_items)
    return [food[0] for food in random_foods]

def get_image_from_title(title, size="512x512"):
    openai.api_key = os.getenv("OPENAI_API_KEY")
    image_response = openai.Image.create(prompt=title, size=size)
    image_url = image_response["data"][0]["url"]
    return image_url


def get_food_nutrition(food, quantity=100):
    # Fetch nutritional data for the specified quantity (default 100g)
    response = requests.get(
        fdc_base_url, params={"api_key": fdc_api_key, "query": food}
    )
    data = response.json()

    if "foods" in data and data["foods"]:
        # For simplicity, we'll just take the first result
        first_food = data["foods"][0]

        # Extract the basic nutritional data
        nutrition = {
            "description": first_food.get("description"),
            "energy": None,
            "protein": None,
            "fat": None,
            "carbs": None,
        }

        # Look for the relevant nutrients in the food's nutrient list
        for nutrient in first_food.get("foodNutrients", []):
            if nutrient.get("nutrientName") == "Energy":
                nutrition["energy"] = nutrient.get("value") * (
                    quantity / 100
                )  # Adjust the value based on the quantity
            elif nutrient.get("nutrientName") == "Protein":
                nutrition["protein"] = nutrient.get("value") * (quantity / 100)
            elif nutrient.get("nutrientName") == "Total lipid (fat)":
                nutrition["fat"] = nutrient.get("value") * (quantity / 100)
            elif nutrient.get("nutrientName") == "Carbohydrate, by difference":
                nutrition["carbs"] = nutrient.get("value") * (quantity / 100)

        return nutrition

    return None


def simplify_ingredient(ingredient):
    # Remove leading/trailing whitespace
    ingredient = ingredient.strip()

    # Remove anything in parentheses
    ingredient = re.sub(r"\([^)]*\)", "", ingredient)

    # Remove any quantities (1, 1/2, etc.)
    ingredient = re.sub(r"\d+\/\d+|\d+", "", ingredient)

    # Remove common measurements and preparation methods
    ingredient = re.sub(
        r"\b(cups?|tbsp|tsp|tablespoons?|teaspoons?|pounds?|lbs?|ounces?|oz?|grams?|g?|sliced|diced|chopped|cut|small|large|medium)\b",
        "",
        ingredient,
        flags=re.I,
    )

    # Extract the quantity of the ingredient using regex
    quantity_match = re.match(r"(\d+(?:\.\d+)?)", ingredient)
    if quantity_match:
        quantity = float(quantity_match.group(1))
        return ingredient.replace(quantity_match.group(1), "").strip(), quantity
    else:
        return ingredient.strip(), 1


def chat_completion(prompt, model="gpt-4", temperature=0):
    res = openai.ChatCompletion.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
    )
    return res["choices"][0]["message"]["content"]


def extract_h1(html_string):
    if not html_string:
        return None
    soup = BeautifulSoup(html_string, "html.parser")
    h1_tag = soup.find("h1")
    return h1_tag.text if h1_tag else None


def extract_ingredients_table(html_string):
    if not html_string:
        return []

    soup = BeautifulSoup(html_string, "html.parser")
    table_tag = soup.find_all("table")[
        0
    ]  # Assuming the first table is the ingredients table

    ingredients_data = []

    for row in table_tag.find_all("tr")[1:]:  # skip the header row
        columns = row.find_all("td")
        ingredient_data = {
            "ingredient": columns[0].text,
            "quantity": columns[1].text,
            "unit": columns[2].text,
            "calories": columns[3].text,
            "protein": columns[4].text,
            "carbohydrates": columns[5].text,
            "fat": columns[6].text,
        }
        ingredients_data.append(ingredient_data)

    return ingredients_data


app = Flask(__name__)

# Sample MongoDB connection
# client = pymongo.MongoClient(mongo_uri)
# collection = client["database_name"]["collection_name"]

# Sample random ingredient function


def get_random_foods_from_csv(file_path):
    with open(file_path, "r") as csvfile:
        reader = csv.reader(csvfile)
        food_list = list(reader)
    num_items = random.randint(1, 10)
    num_items = random.randint(1, 10)
    random_foods = random.sample(food_list, num_items)
    return [food[0] for food in random_foods]

# Sample route to generate recipe


@app.route("/generate_recipe")
def generate_recipe():
    s3 = boto3.client("s3")
    openai.api_key = os.getenv("OPENAI_API_KEY")

    if os.path.isfile("/app/data/food.csv"):
        random_ingredients = get_random_foods_from_csv("/app/data/food.csv")
    else:
        random_ingredients = get_random_foods_from_csv(
            "food.csv"
        )

    print(random_ingredients)

    # Step 1: Generate a random recipe using OpenAI chat_completion
    prompt = f"""
    Role: You are a dietitian that knows the nutritional contents of ingredients.
    Context: You are creating and experimental recipe with the following ingredients: {random_ingredients}.
    Task: Based on your expertise defined in your role. Give me a recipe. With this recipe, I want the title in an <h1> html tag. 
    With this recipe, I want also a table formatted as html with seven columns where each row in the table contains an ingredient from the main course.
    The first column in the table is the name of the ingredient.
    The second column of the table is the number of units of that ingredient needed for one person. The third column is the name of the unit
    that is used to measure the amount in the second column. The fourth column of the table is the number of calories in that ingredient.
    The fifth column of the table is the number of grams of protein in that ingredient.
    The sixth column of the table is the number of grams of carbohydrates in that ingredient.
    The seventh column of the table is the number of grams of fat in that ingredient.
    Then create a second table that contains one row, and four columns.
    The first column of the table should contain the total calories in the recipe.
    The second column of the table should contain the total grams of protein in the recipe.
    The third column of the table should contain the total grams of carbohydrates in the recipe.
    The fourth column of the table should contain the total grams of fat in the recipe.
    Do not give the recipe for preparing the main course.
    """
    recipe_response = chat_completion(prompt)
    print(recipe_response)

    # Extract the tables from the OpenAI response
    ingredients_data = extract_ingredients_table(recipe_response)

    # Step 2: Extract the recipe content from the OpenAI response
    # recipe_content = extract_recipe_content(recipe_response)
    # print(recipe_content)

    # Step 3: Extract the ingredients from the OpenAI response
    # Assuming ingredients are wrapped within a <ul></ul> HTML tag
    soup = BeautifulSoup(recipe_response, "html.parser")
    ul_tag = soup.find("ul")
    h1_tag = soup.find("h1")
    mystery_ingredients = [
        li.text for li in ul_tag.find_all("li")] if ul_tag else []

    # Extract the recipe title from the OpenAI response
    # Assuming the title is wrapped within a <h1></h1> HTML tag
    title = extract_h1(recipe_response)

    # Step 4: Simplify each ingredient and extract their quantities
    mystery_ingredients = [
        simplify_ingredient(ingredient) for ingredient in mystery_ingredients
    ]

    # Step 5: Convert ingredient quantities to a common unit (e.g., grams)
    converted_ingredients = []
    for ingredient in mystery_ingredients:
        # Here, you should fetch the conversion data for the ingredient and convert the quantity to grams
        # For example, if 'ingredient' is "apple" and 'quantity' is 2, you should look up the conversion data for an apple
        # and calculate the quantity in grams.
        # For simplicity, I'll assume you have a 'convert_to_grams' function that returns the quantity in grams
        converted_ingredients.append((ingredient))

    # Step 6: Get the nutritional data for each ingredient based on the converted quantities
    nutrition_data = {
        ingredient: get_food_nutrition(ingredient)
        for ingredient, quantity in converted_ingredients
    }

    # Step 7: Extract recipe content
    prompt = f"""
    Role: You are a creative chef that knows how to prepare delicious recipes from a given set of ingredients.
    Context: You are given the following ingredients: {ingredients_data}.
    Task: Based on your expertise defined in your role. Give me a recipe. 
    With this recipe, I want:
    - Title: the title in an <h1> html tag.
    - Description: a <p> html tag with a paragraph containing a detailed description of the dish, similar to what you might find on a restaurant menu.
    - Ingredients: an <h2> html tag containing the text 'Ingredients:', followed by un unordered list that contains the list of ingredients alphabetically.
    - Method: Below the ingredients list, I would like an <h2> html tag with the text: 'Instructions' followed by an ordered list where each item in the list consists of two parts:
        part 1: A short, and simple summary of what is being done in the instruction (For Example: Cook the pasta:). This should be inside an <h3> html tag.
        part 2: The unredacted instruction (For Example, if part 1 was something like 'Cook the pasta:' then the part 2 might be 'Once the pot of water is boiling,
                season with salt and add the pasta. Let cook, stirring occasionally, until the pasta is al dente, about 8 minutes. 
                A few minutes before the pasta is done cooking, reserve 1 1/4 cups of pasta water for the ragu.' This should be inside a <p> html tag.
       ***NOTE***
        Method part 2 is of vital importance and as such it should be written so that it is extra clear for the user. I would like any measurement to be in bold text, for example:
        <b>1 1/4 cups</b>, or <b>about 8 minutes</b>. I would also like words associated with heat to be red, and words associated with cold to be blue, for example:
        <p><span style="color: red">Boil</span> the water for <b>8 minutes</b>, then immediately <span style="color: blue">chill</span> with ice.</p>

    - About: Below the Method, I would like 'About' inside an <h6> html tag followed by a paragraph about why you believe this is a good recipe, and any cultural influence this recipe draws from. This should be in a <p> html tag."""
    recipe_content = chat_completion(prompt)

    # Step 8: Extract the different parts from the OpenAI response
    soup = BeautifulSoup(recipe_content, "html.parser")
    description = soup.find("p").text
    instructions = soup.find_all("li")
    instructions = [instruction.text for instruction in instructions]
    about = soup.find("h6").text

    # Step 8: Use OpenAI image creation model
    image_url = get_image_from_title(title)

    # Fetch the image from the URL and convert it to binary data
    response = requests.get(image_url)
    bucket_name = "kitchenai.recipes"
    title_for_url = title.replace(" ", " ")
    key = "recipe_images/" + title_for_url + ".jpg"
    s3.upload_fileobj(BytesIO(response.content), bucket_name, key)

    # Step 9: Store the recipe data in MongoDB
    recipe_data = {
        "title": title,
        "description": description,
        "ingredients": ingredients_data,
        "instructions": instructions,
        "about": about,
        "photo": f"https://s3.us-east-2.amazonaws.com/{bucket_name}/{key}",
    }

    # Step 10: Insert the recipe data into MongoDB (uncomment if you have MongoDB connection)
    recipe_id = collection.insert_one(recipe_data)
    print(f"Recipe inserted with ID: {recipe_id}")

    # Step 11: Return the data as JSON
    return jsonify(
        recipe_title=title,
        recipe_content=recipe_content,
        image_url=image_url,
        ingredients_data=ingredients_data,
    )


if __name__ == "__main__":
    app.run(debug=True)
