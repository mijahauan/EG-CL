# session_model.py
from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from typing import List, Dict, Any
from eg_model import ExistentialGraph

## NEW ##
# This file defines the high-level data structures for managing application
# state, including Folios, Game Sessions, and Action History.

@dataclass
class Action:
    """A structured record of a single transformation applied to a graph."""
    action_name: str
    parameters: Dict[str, Any]

@dataclass
class GameSession:
    """Manages the state and history for a single 'inning' or proof attempt."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    graph_id: str = "" # The ID of the ExistentialGraph this session applies to
    history: List[Action] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict) # For user, timestamp, notes, etc.

class Folio:
    """
    The top-level container for a user's project. It holds multiple graphs
    and game sessions, representing a complete knowledge base or a set of proofs.
    """
    def __init__(self, name: str = "Untitled Folio"):
        self.id = str(uuid.uuid4())
        self.name = name
        self.graphs: Dict[str, ExistentialGraph] = {}
        self.sessions: Dict[str, GameSession] = {}

    def new_graph(self, name: str) -> ExistentialGraph:
        """Creates a new, named Existential Graph within the folio."""
        if name in self.graphs:
            raise ValueError(f"A graph with the name '{name}' already exists in this folio.")
        graph = ExistentialGraph()
        self.graphs[name] = graph
        return graph