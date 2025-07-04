# eg_model.py
from __future__ import annotations
import uuid
from enum import Enum, auto
from typing import List, Optional, Set, Dict

class PredicateType(Enum):
    RELATION = auto()
    FUNCTION = auto()
    CONSTANT = auto()

class Context:
    def __init__(self, parent: Optional[Context] = None):
        self.id = str(uuid.uuid4())
        self.parent = parent
        self.children: List[Context] = []
        self.predicates: List[Predicate] = []

    def get_nesting_level(self) -> int:
        level = 0
        p = self.parent
        while p:
            level += 1
            p = p.parent
        return level

class Ligature:
    def __init__(self):
        self.id = str(uuid.uuid4())
        self.hooks: Set[Hook] = set()

    def get_starting_context(self) -> Context:
        """
        Determines the outermost context where the ligature is quantified.
        This is the Least Common Ancestor (LCA) of all contexts its hooks appear in.
        """
        if not self.hooks:
            raise ValueError("Ligature is not connected to any predicate.")

        # Get the path of ancestors for the first hook
        first_path = []
        curr = list(self.hooks)[0].predicate.context
        while curr:
            first_path.append(curr)
            curr = curr.parent
        
        common_ancestors = set(first_path)

        # Find the intersection of ancestor paths for all other hooks
        for hook in list(self.hooks)[1:]:
            path_to_check = set()
            curr = hook.predicate.context
            while curr:
                path_to_check.add(curr)
                curr = curr.parent
            common_ancestors.intersection_update(path_to_check)
        
        if not common_ancestors:
            # This case implies hooks are in completely separate graph trees,
            # which shouldn't happen. The ultimate common ancestor is the SoA.
             return list(self.hooks)[0].predicate.context # Fallback to shallowest hook's context parent
        
        # The LCA is the common ancestor with the highest nesting level.
        return max(common_ancestors, key=lambda c: c.get_nesting_level())


class Hook:
    def __init__(self, predicate: Predicate, index: int):
        self.predicate = predicate
        self.index = index
        self.ligature: Optional[Ligature] = None

class Predicate:
    def __init__(self, name: str, arity: int, p_type: PredicateType = PredicateType.RELATION):
        self.id = str(uuid.uuid4())
        self.name = name
        self.arity = arity
        self.type = p_type
        self.hooks: List[Hook] = [Hook(self, i) for i in range(arity)]
        self.context: Optional[Context] = None

class ExistentialGraph:
    def __init__(self):
        self.sheet_of_assertion = Context(parent=None)