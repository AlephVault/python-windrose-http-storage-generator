#!/usr/bin/env python3
import os
import shutil


def _make_docker_compose_file(project_path: str, mongodb_port: int = 27017, http_port: int = 8080,
                              express_port: int = 8081):
    """
    Dumps the whole docker-compose.yml file in the project directory.
    :param project_path: The path of the project.
    :param mongodb_port: The mongodb port to expose the container at.
    :param http_port: The http port to expose the container at.
    :param express_port: The mongo express port to expose the container at.
    """

    contents = f"""version: '3.7'
services:
  express:
    image: mongo-express:1.0.0-alpha
    restart: always
    env_file: .env
    ports:
      - {express_port}:8081
    expose:
      - {express_port}
  mongodb:
    image: mongo:6.0
    restart: always
    env_file: .env
    ports:
      - {mongodb_port}:27017
    expose:
      - {mongodb_port}
    volumes:
      - .tmp/mongo:/data/db
  http:
    build:
      context: ./server
    command: waitress-serve --listen=127.0.0.1:80 app:app
    restart: always
    env_file: .env
    ports:
      - {http_port}:80
    expose:
      - {http_port}
"""

    with open(os.path.join(project_path, "docker-compose.yml"), "w") as f:
        f.write(contents)


def _make_env_file(project_path: str, mongodb_user: str = "admin", mongodb_pass: str = "p455w0rd",
                   server_api_key: str = "sample-abcdef"):
    """
    Creates the envfile for the mongodb container.
    :param project_path: The path of the project.
    :param mongodb_port: The mongodb port to expose the container at.
    :param mongodb_user: The mongodb user.
    :param mongodb_pass: The mongodb password.
    :param server_api_key: The default api key available for a server.
    """

    contents = f"""# These environment variables stand for all the containers
MONGO_INITDB_ROOT_USERNAME={mongodb_user}
MONGO_INITDB_ROOT_PASSWORD={mongodb_pass}
DB_HOST=mongodb
DB_PORT=27017
DB_USER={mongodb_user}
DB_PASS={mongodb_pass}
ME_CONFIG_MONGODB_SERVER=mongodb
ME_CONFIG_MONGODB_PORT=27017
ME_CONFIG_MONGODB_ADMINUSERNAME={mongodb_user}
ME_CONFIG_MONGODB_ADMINPASSWORD={mongodb_pass}
SERVER_API_KEY={server_api_key}
"""

    with open(os.path.join(project_path, ".env"), "w") as f:
        f.write(contents)


def _make_requirements_file(project_path: str):
    """
    Creates the requirements.txt file.
    :param project_path: The path of the project.
    """

    contents = f"""# Place any requirements you need in this file.
alephvault-http-mongodb-storage==0.0.4
"""

    with open(os.path.join(project_path, "server", "requirements.txt"), "w") as f:
        f.write(contents)


def _make_dockerfile(project_path: str):
    """
    Creates the dockerfile.
    :param project_path: The path of the project.
    """

    contents = f"""FROM tecktron/python-waitress:python-3.7

COPY ./ /app
RUN pip install -r /app/requirements.txt
# The /app/app.py file will be the entrypoint for waitress serve.
"""

    with open(os.path.join(project_path, "server", "Dockerfile"), "w") as f:
        f.write(contents)


def _make_init_file(project_path: str):
    """
    Creates the __init__.py file.
    :param project_path: The path of the project.
    """

    with open(os.path.join(project_path, "server", "__init__.py"), "w") as f:
        f.write("")


def _make_console_startup_file(project_path: str):
    """
    Creates the http_storage_console file.
    :param project_path: The path of the project.
    """

    contents = f"""# These variables are initialized into the interpreter.
import os
from urllib.parse import quote_plus

from pymongo import MongoClient

host = os.environ["DB_HOST"].strip()
port = os.environ["DB_PORT"]
user = os.environ["DB_USER"].strip()
password = os.environ["DB_PASS"]
client = MongoClient("mongodb://%s:%s@%s:%s" % (quote_plus(user), quote_plus(password), host, port))
"""

    with open(os.path.join(project_path, "server", "http_storage_console.py"), "w") as f:
        f.write(contents)


def _make_console_shellscript_file(project_path: str):
    """
    Creates the console execution shellscript file.
    :param project_path: The path of the project.
    """

    contents = f"""#!/bin/bash
DIR="$(dirname "$0")"
(cd "$DIR" && docker-compose exec -ti -e PYTHONSTARTUP="/app/http_storage_console.py" http python)
"""

    with open(os.path.join(project_path, "server", "console.sh"), "w") as f:
        f.write(contents)


def _make_app_file(project_path: str, template: str):
    """
    Creates the app file, based on a template. This can occur in two ways:
    - default:{simple|multiple}.
    - A path to a file (absolute, or relative).
    :param project_path: The path of the project.
    :param template: The template to use.
    """

    if template == "default:simple":
        template = os.path.join(os.path.dirname(__file__), "templates", "simple-application-template.py")
    elif template == "default:multichar":
        template = os.path.join(os.path.dirname(__file__), "templates", "multichar-application-template.py")

    target = os.path.join(project_path, "server", "app.py")
    shutil.copy(template, target)


def generate_project(full_path: str, template: str,
                     mongodb_port: int = 27017, http_port: int = 8080, express_port: int = 8081,
                     mongodb_user: str = "admin", mongodb_pass: str = "p455w0rd",
                     server_api_key: str = "sample-abcdef"):
    """
    Generates the whole project, including the relevant Docker-related files.
    :param full_path: The full directory path.
    :param template: The template to use.
    :param mongodb_port: The mongodb port to expose the container at.
    :param http_port: The http port to expose the container at.
    :param express_port: The mongo express port to expose the container at.
    :param mongodb_user: The mongodb user.
    :param mongodb_pass: The mongodb password.
    :param server_api_key: The default api key available for a server.
    """

    # Create the whole directory path, if not exists.
    os.makedirs(full_path, exist_ok=True)

    # Require the directory to be empty beforehand.
    if len(os.listdir(full_path)) != 0:
        raise OSError("Directory not empty")

    # Create the server path.
    os.makedirs(os.path.join(full_path, "server"), exist_ok=True)

    # Create all the files.
    _make_docker_compose_file(full_path, mongodb_port, http_port, express_port)
    _make_env_file(full_path, mongodb_user, mongodb_pass, server_api_key)
    _make_dockerfile(full_path)
    _make_requirements_file(full_path)
    _make_init_file(full_path)
    _make_app_file(full_path, template)
    _make_console_startup_file(full_path)
    _make_console_shellscript_file(full_path)
