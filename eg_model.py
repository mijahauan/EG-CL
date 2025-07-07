import uuid

class GraphObject:
    """Base class for all objects in the graph."""
    def __init__(self, obj_id=None):
        self.id = obj_id if obj_id else str(uuid.uuid4())

class Context(GraphObject):
    """Represents a context, which can be the sheet of assertion or a cut."""
    def __init__(self, obj_id=None, parent_id=None):
        super().__init__(obj_id)
        self.parent_id = parent_id
        self.children = set()  # Set of child object IDs

class Cut(Context):
    """Represents a cut, which is a type of context."""
    def __init__(self, obj_id=None, parent_id=None):
        super().__init__(obj_id, parent_id)

class Predicate(GraphObject):
    """Represents a predicate with a label and hooks for ligatures."""
    def __init__(self, label, hooks, obj_id=None, p_type='relation', is_functional=False):
        super().__init__(obj_id)
        self.label = label
        self.hooks = {i: None for i in range(1, hooks + 1)}  # hook_index -> ligature_id
        self.p_type = p_type  # 'relation', 'constant'
        self.is_functional = is_functional
        if self.is_functional and hooks < 1:
            raise ValueError("Functional predicates must have at least one hook (for the output).")

    @property
    def output_hook(self):
        """For functional predicates, the last hook is the output by convention."""
        if self.is_functional:
            return max(self.hooks.keys())
        return None

class Ligature(GraphObject):
    """Represents a ligature connecting multiple predicate hooks."""
    def __init__(self, obj_id=None):
        super().__init__(obj_id)
        self.connections = set()  # Set of (predicate_id, hook_index) tuples
        self.traversed_cuts = set() # Set of Cut IDs this ligature passes through

class GraphModel:
    """A generalized property hypergraph model for Existential Graphs."""
    def __init__(self):
        self.objects = {}  # id -> object
        self.sheet_of_assertion = Context(obj_id='SA')
        self.add_object(self.sheet_of_assertion)

    def add_object(self, obj):
        if obj.id in self.objects:
            raise ValueError(f"Object with id {obj.id} already exists.")
        self.objects[obj.id] = obj

    def get_object(self, obj_id):
        return self.objects.get(obj_id)

    def remove_object(self, obj_id):
        if obj_id in self.objects:
            del self.objects[obj_id]

    def get_context(self, obj_id):
        obj = self.get_object(obj_id)
        if isinstance(obj, Context):
            return obj
        return None