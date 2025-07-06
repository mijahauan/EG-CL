# serialization.py
import json
from typing import Any, Dict
from eg_model import *
from session_model import *

## NEW ##
# This file contains all logic for saving (serializing) and loading
# (deserializing) the application state to and from JSON.

class EgClEncoder(json.JSONEncoder):
    """
    A custom JSON encoder that knows how to convert all custom objects
    from this project into a serializable dictionary format.
    """
    def default(self, obj: Any) -> Any:
        if isinstance(obj, (Folio, GameSession, ExistentialGraph, Node, Hyperedge)):
            # Add a __type__ key to identify the class during decoding
            d = {'__type__': obj.__class__.__name__}
            d.update(obj.__dict__)
            return d
        if isinstance(obj, Action):
            return {'__type__': 'Action', 'action_name': obj.action_name, 'parameters': obj.parameters}
        if isinstance(obj, GraphObjectType):
            return {'__type__': 'GraphObjectType', 'name': obj.name}
        return super().default(obj)

def decode_hook(dct: Dict[str, Any]) -> Any:
    """
    A custom JSON decoder hook that reconstructs our custom objects
    from the dictionary format created by the encoder.
    """
    if '__type__' not in dct:
        return dct

    type_name = dct.pop('__type__')
    
    if type_name == 'Folio':
        folio = Folio(dct['name'])
        folio.__dict__.update(dct)
        return folio
    if type_name == 'GameSession':
        session = GameSession()
        session.__dict__.update(dct)
        return session
    if type_name == 'Action':
        return Action(dct['action_name'], dct['parameters'])
    if type_name == 'ExistentialGraph':
        graph = ExistentialGraph()
        graph.__dict__.update(dct)
        return graph
    if type_name == 'Node':
        node = Node(dct['node_type'], dct['properties'])
        node.__dict__.update(dct)
        return node
    if type_name == 'Hyperedge':
        edge = Hyperedge(dct['edge_type'], dct['endpoints'])
        edge.__dict__.update(dct)
        return edge
    if type_name == 'GraphObjectType':
        return GraphObjectType[dct['name']]

    # If type is unknown, return the dict as is
    dct['__type__'] = type_name
    return dct

def save_folio(folio: Folio, filepath: str):
    """Saves a Folio object to a JSON file."""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(folio, f, cls=EgClEncoder, indent=2)

def load_folio(filepath: str) -> Folio:
    """Loads a Folio object from a JSON file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f, object_hook=decode_hook)