import os
import logging
from flask import request, make_response, jsonify
from pymongo import MongoClient
from alephvault.http_storage.flask_app import StorageApp
from alephvault.http_storage.types.method_handlers import MethodHandler, ItemMethodHandler


logging.basicConfig()


class GetUserByLogin(MethodHandler):
    """
    The user's password is not validated here.
    """

    def __call__(self, client: MongoClient, resource: str, method: str, db: str, collection: str, filter: dict):
        login = request.args.get("login")
        filter = {**filter, "login": login}
        document = client[db][collection].find_one(filter)
        if document:
            return make_response(jsonify(document), 200)
        else:
            return make_response(jsonify({"code": "not-found"}), 404)


ACCOUNTS = {
    "login": {
        "type": "string",
        "required": True,
        "empty": False
    },
    "password": {
        "type": "string",
        "required": True,
        "empty": False
    },
    "position": {
        "type": "dict",
        "schema": {
            "scope": {
                # It must be a valid scope, but "" can be
                # understood as Limbo (if a player must
                # belong to such state).
                "type": "string",
                "required": True
            },
            "map": {
                # It must be a valid map. An index being
                # >= 0 is expected. Typically, the index
                # must be valid and, if the scope is "",
                # then it is ignored (suggested: 0).
                "type": "integer",
                "required": True,
                "min": 0
            },
            "x": {
                # The position must be valid inside the
                # map it belongs to. It may be ignored
                # if the scope is "".
                "type": "integer",
                "required": True,
                "min": 0,
                "max": 32767
            },
            "y": {
                # The position must be valid inside the
                # map it belongs to. It may be ignored
                # if the scope is "".
                "type": "integer",
                "required": True,
                "min": 0,
                "max": 32767
            },
        }
    }
}


CHARACTERS = {
    "account_id": {
        "type": "objectid",
        "required": True,
    },
    "index": {
        "type": "integer",
        "required": True,
        "min": 0
    },
    "display_name": {
        "type": "string",
        "required": True,
        "empty": False
    },
}


SCOPES = {
    "key": {
        "type": "string",
        "required": True,
        "empty": False
    },
    "template_key": {
        "type": "string",
        "required": True,
        "empty": False
    },
    "dynamic": {
        "type": "boolean",
        "required": True
    },
}


MAPS = {
    "scope_id": {
        "type": "objectid",
        "required": True
    },
    "index": {
        "type": "integer",
        "required": True,
        "min": 0
    },
    "drop": {
        # The layout is: map.drop[y * width + x] == stack([head, ...]).
        "type": "list",
        "schema": {
            "type": "list",
            "schema": {
                "type": "integer"
            }
        }
    }
}


class Application(StorageApp):
    """
    The main application. It comes out of the box with:

    - universe.accounts: the player accounts.
    - universe.characters: the player characters.
    - universe.scopes: the scopes.
    - universe.maps: the scopes' maps (and drops).
    """

    SETTINGS = {
        "debug": True,
        "auth": {
            "db": "auth-db",
            "collection": "api-keys"
        },
        "connection": {
            "host": os.environ['DB_HOST'],
            "port": int(os.environ['DB_PORT']),
            "user": os.environ['DB_USER'],
            "password": os.environ['DB_PASS']
        },
        "resources": {
            "accounts": {
                "type": "list",
                "db": "universe",
                "collection": "accounts",
                "soft_delete": True,
                "schema": ACCOUNTS,
                "projection": ["login", "password", "position"],
                "verbs": "*",
                "indexes": {
                    "unique-login": {
                        "unique": True,
                        "fields": "login"
                    },
                },
                "methods": {
                    "by-login": {
                        "type": "view",
                        "handler": GetUserByLogin()
                    }
                }
            },
            "characters": {
                "type": "list",
                "db": "universe",
                "collection": "characters",
                "soft_delete": True,
                "schema": CHARACTERS,
                "projection": ["display_name"],
                "verbs": "*",
                "indexes": {
                    "unique-nickname": {
                        "unique": True,
                        "fields": "display_name"
                    },
                    "unique-id": {
                        "unique": True,
                        "fields": ["account_id", "index"]
                    }
                },
            },
            "scopes": {
                "type": "list",
                "db": "universe",
                "collection": "scopes",
                "soft_delete": True,
                "schema": SCOPES,
                "projection": ["key", "template_key", "dynamic"],
                "verbs": "*",
                "indexes": {
                    "key": {
                        "unique": True,
                        "fields": "login"
                    }
                }
            },
            "maps": {
                "type": "list",
                "db": "universe",
                "collection": "maps",
                "soft_delete": True,
                "schema": MAPS,
                "projection": ["scope_id", "index", "drop"],
                "verbs": "*",
                "indexes": {
                    "key": {
                        "unique": True,
                        "fields": ["scope_id", "index"]
                    }
                }
            }
        }
    }

    def __init__(self, import_name: str = __name__):
        super().__init__(self.SETTINGS, import_name=import_name)
        try:
            setup = self._client["lifecycle"]["setup"]
            result = setup.find_one()
            if not result:
                setup.insert_one({"done": True})
                self._client["auth-db"]["api-keys"].insert_one({"api-key": os.environ['SERVER_API_KEY']})
        except:
            pass


app = Application()


if __name__ == "__main__":
    app.run("0.0.0.0", 6666)
