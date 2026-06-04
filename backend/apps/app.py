from flask import Flask
from apps import route

def create_app():
    flaskapp = Flask(
        __name__,
        template_folder="../../frontend/templates",
        static_folder="../../frontend/static",
    )
    route.register_routes(flaskapp)
    return flaskapp