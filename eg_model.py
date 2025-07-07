import uuid

class GraphObject:
    def __init__(self, obj_id=None):
        self.id = obj_id if obj_id else str(uuid.uuid4())

class Context(GraphObject):
    def __init__(self, obj_id=None, parent_id=None):
        super().__init__(obj_id)
        self.parent_id = parent_id
        self.children = set()

class Cut(Context):
    pass

class LineOfIdentity(GraphObject):
    def __init__(self, obj_id=None):
        super().__init__(obj_id)
        self.ligatures = set()

class Ligature(GraphObject):
    def __init__(self, line_of_identity_id, obj_id=None):
        super().__init__(obj_id)
        self.line_of_identity_id = line_of_identity_id
        self.attachments = set()
        self.traversed_cuts = set() # This attribute is needed for traversal logic

class Predicate(GraphObject):
    def __init__(self, label, hooks, obj_id=None, p_type='relation', is_functional=False):
        super().__init__(obj_id)
        self.label = label
        self.hooks = {i: None for i in range(1, hooks + 1)}
        self.p_type = p_type
        self.is_functional = is_functional

    @property
    def output_hook(self):
        if self.is_functional:
            return max(self.hooks.keys())
        return None

class GraphModel:
    def __init__(self):
        self.objects = {}
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