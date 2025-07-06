# eg_model.py
from __future__ import annotations
import uuid
from enum import Enum, auto
from typing import List, Optional, Set, Dict, Tuple

class PredicateType(Enum):
    """Enumeration for the type of a Predicate, following Dau's extensions."""
    RELATION = auto()
    FUNCTION = auto()
    CONSTANT = auto()

class Context:
    """Represents the Sheet of Assertion or a Cut, forming a tree structure."""
    def __init__(self, parent: Optional[Context] = None):
        self.id = str(uuid.uuid4())
        self.parent = parent
        self.children: List[Context] = []
        self.predicates: List[Predicate] = []

    def get_nesting_level(self) -> int:
        """Calculates depth. SA=0. Even is positive, odd is negative."""
        level = 0
        p = self.parent
        while p:
            level += 1
            p = p.parent
        return level

    def is_positive(self) -> bool:
        """A context is positive if it's evenly enclosed."""
        return self.get_nesting_level() % 2 == 0

    def is_negative(self) -> bool:
        """A context is negative if it's oddly enclosed."""
        return not self.is_positive()

class Ligature:
    """Represents a single, continuous Line of Identity."""
    def __init__(self):
        self.id = str(uuid.uuid4())
        self.hooks: Set[Hook] = set()

    def __repr__(self):
        return f"Ligature(id={self.id[:4]}..., hooks={len(self.hooks)})"

    def get_starting_context(self) -> Context:
        """
        Determines the outermost context where the ligature is quantified.
        This is the Least Common Ancestor (LCA) of all contexts its hooks appear in.
        """
        if not self.hooks:
            raise ValueError("Ligature has no hooks to determine a starting context.")

        paths = []
        for hook in self.hooks:
            path = []
            curr = hook.predicate.context
            while curr:
                path.append(curr)
                curr = curr.parent
            paths.append(path)
        
        if not paths:
             raise ValueError("Could not determine paths for ligature's hooks.")

        # The common ancestors are the intersection of all paths to the root.
        common_ancestors = set(paths[0])
        for other_path in paths[1:]:
            common_ancestors.intersection_update(set(other_path))
        
        if not common_ancestors:
             raise ValueError("Could not find a common ancestor for the ligature's hooks.")
        
        # The LCA is the one with the greatest nesting level (closest to the leaves).
        return max(common_ancestors, key=lambda c: c.get_nesting_level())

class Hook:
    """A connection point on a Predicate."""
    def __init__(self, predicate: Predicate, index: int):
        self.id = str(uuid.uuid4()) # Unique ID for each hook
        self.predicate = predicate
        self.index = index
        self.ligature: Optional[Ligature] = None

class Predicate:
    """Represents a Peirce 'spot': a relation, constant, or function."""
    def __init__(self, name: str, arity: int, p_type: PredicateType = PredicateType.RELATION):
        self.id = str(uuid.uuid4())
        self.name = name
        self.arity = arity
        self.type = p_type
        self.hooks: List[Hook] = [Hook(self, i) for i in range(arity)]
        self.context: Optional[Context] = None

class ExistentialGraph:
    """The top-level container for the graph."""
    def __init__(self):
        self.sheet_of_assertion = Context(parent=None)
