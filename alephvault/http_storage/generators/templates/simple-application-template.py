import os
import logging
from typing import Dict
from bson import ObjectId
from flask import request, make_response, jsonify
from pymongo import MongoClient
from alephvault.http_storage.flask_app import StorageApp
from alephvault.http_storage.types.method_handlers import MethodHandler, ItemMethodHandler


logging.basicConfig()
LOGGER = logging.getLogger("game-storage")
LOGGER.setLevel(logging.INFO)


class GetUserByLogin(MethodHandler):
    """
    The user's password is not validated here.
    """

    def __call__(self, client: MongoClient, resource: str, method: str, db: str, collection: str, filter: dict):
        login = request.args.get("login")
        if not login:
            return make_response(jsonify({"code": "missing-lookup"}), 400)
        filter = {**filter, "login": login}
        document = client[db][collection].find_one(filter)
        if document:
            return make_response(jsonify(document), 200)
        else:
            return make_response(jsonify({"code": "not-found"}), 404)


class GetMapsByScope(MethodHandler):
    """
    Get all the maps references inside a given scope.
    """

    def __call__(self, client: MongoClient, resource: str, method: str, db: str, collection: str, filter: dict):
        scope = request.args.get("scope")
        if scope:
            filter = {**filter, "key": scope}
        else:
            scope_id = request.args.get("id")
            if scope_id:
                filter = {**filter, "_id": ObjectId(scope_id)}
            else:
                return make_response(jsonify({"code": "missing-lookup"}), 400)
        document = client[db]['scopes'].find_one(filter)
        if document:
            result = list(client[db][collection].find({'_deleted': {}, 'scope_id': document['_id']},
                                                      ['index']))
            return make_response(jsonify(result), 200)
        else:
            return make_response(jsonify({"code": "not-found"}), 404)


class UpdateDrop(MethodHandler):
    """
    Updates part of the drop of a map. This update is done in linear slice.
    """

    def _replace(self, current_drop: list, from_idx: int, drops: list):
        """
        Ensures the current drop is updated with new drops.
        :param current_drop: The current drop(s) status.
        :param from_idx: The index to start updating from.
        :param drops: The drops to set.
        """

        current_drop_len = len(current_drop)
        to_idx = from_idx + len(drops)
        extra = to_idx - current_drop_len
        if extra > 0:
            current_drop.extend([[] for _ in range(extra)])
        current_drop[from_idx:to_idx] = drops

    def __call__(self, client: MongoClient, resource: str, method: str, db: str, collection: str, filter: dict):
        map_id = request.args.get("id")
        if map_id:
            filter = {**filter, "_id": ObjectId(map_id)}
        else:
            return make_response(jsonify({"code": "missing-lookup"}), 400)

        # Only allow JSON format.
        if not request.is_json:
            return make_response(jsonify({"code": "bad-format"}), 406)

        # Get the drops.
        drops = request.json.get("drops")
        if not isinstance(drops, list) or not all(isinstance(box, list) for box in drops):
            return make_response(jsonify({"code": "missing-or-invalid-drop"}), 400)

        # Get the index to apply the changes from.
        from_idx = request.json.get("from", 0)
        if not isinstance(from_idx, (int, float)) or from_idx < 0:
            return make_response(jsonify({"code": "bad-index"}), 400)
        from_idx = int(from_idx)

        # Get the map to change the drops.
        document = client[db][collection].find_one(filter)
        if document:
            # Get the drop, and update it.
            current_drop = document.get("drop", [])
            self._replace(current_drop, from_idx, [e or [] for e in drops])
            client[db][collection].update_one(filter, {"$set": {"drop": current_drop}})
            return make_response(jsonify({"code": "ok"}), 200)
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
    "display_name": {
        "type": "string",
        "required": True,
        "empty": False
    },
    "position": {
        "type": "dict",
        "required": True,
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

    - universe.accounts: the player accounts (and characters).
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
                "list_projection": ["login", "password", "display_name", "position"],
                "verbs": "*",
                "indexes": {
                    "unique-login": {
                        "unique": True,
                        "fields": "login"
                    },
                    "unique-nickname": {
                        "unique": True,
                        "fields": "display_name"
                    }
                },
                "methods": {
                    "by-login": {
                        "type": "view",
                        "handler": GetUserByLogin()
                    }
                }
            },
            "scopes": {
                "type": "list",
                "db": "universe",
                "collection": "scopes",
                "soft_delete": True,
                "schema": SCOPES,
                "list_projection": ["key", "template_key"],
                "verbs": "*",
                "indexes": {
                    "key": {
                        "unique": True,
                        "fields": "key"
                    }
                }
            },
            "maps": {
                "type": "list",
                "db": "universe",
                "collection": "maps",
                "soft_delete": True,
                "schema": MAPS,
                "list_projection": ["scope_id", "index"],
                "verbs": "*",
                "indexes": {
                    "unique-key": {
                        "unique": True,
                        "fields": ["scope_id", "index"]
                    }
                },
                "methods": {
                    "set-drop": {
                        "type": "operation",
                        "handler": UpdateDrop()
                    },
                    "by-scope": {
                        "type": "view",
                        "handler": GetMapsByScope()
                    }
                }
            }
        }
    }

    def _init_default_key(self, key: str):
        """
        A convenience utility to initialize an API key.
        :param key: The key to initialize.
        """

        LOGGER.info("Initializing default key...")
        self._client["auth-db"]["api-keys"].insert_one({"api-key": key})

    def _init_static_scopes(self, scopes: Dict[str, int]):
        """
        A convenience utility to initialize some static maps.
        :param scopes: The scopes keys to initialize, and their maps count.
        """

        LOGGER.info("Initializing scopes...")
        for scope, maps in scopes.items():
            LOGGER.info(f"Initializing scope {scope} and their {maps}...")
            scope_id = self._client["universe"]["scopes"].insert_one({
                "key": scope, "template_key": ""
            }).inserted_id
            self._client["universe"]["maps"].insert_many([
                {"scope_id": scope_id, "index": index, "drop": []}
                for index in range(max(0, maps))
            ])

    def __init__(self, import_name: str = __name__):
        super().__init__(self.SETTINGS, import_name=import_name)
        try:
            setup = self._client["lifecycle"]["setup"]
            result = setup.find_one()
            if not result:
                setup.insert_one({"done": True})
                self._init_default_key(os.environ['SERVER_API_KEY'])
                self._init_static_scopes({})
        except:
            pass


app = Application()


if __name__ == "__main__":
    app.run("0.0.0.0", 6666)
