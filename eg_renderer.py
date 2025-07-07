import svgwrite
from eg_model import GraphModel, Cut, Predicate

class Renderer:
    def __init__(self, graph: GraphModel):
        self.graph = graph
        self.dwg = svgwrite.Drawing(profile='tiny')
        self.positions = {}  # Cache positions to avoid re-computation

    def render(self):
        self._calculate_positions(self.graph.sheet_of_assertion, 0, 0)
        self._draw_graph()
        return self.dwg.tostring()

    def _calculate_positions(self, context, x_offset, y_offset):
        # Dummy layout algorithm: just tile children
        x, y = x_offset, y_offset
        for child_id in context.children:
            self.positions[child_id] = (x, y)
            child = self.graph.get_object(child_id)
            if isinstance(child, Cut):
                self._calculate_positions(child, x + 10, y + 10)
            x += 100 

    def _draw_graph(self):
        for obj_id, obj in self.graph.objects.items():
            pos = self.positions.get(obj_id)
            if pos:
                if isinstance(obj, Cut):
                    self.dwg.add(self.dwg.rect(insert=pos, size=(80, 80), fill='none', stroke='black'))
                elif isinstance(obj, Predicate):
                    self.dwg.add(self.dwg.text(obj.label, insert=pos))