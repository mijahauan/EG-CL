# eg_renderer.py
from eg_model import ExistentialGraph, Context, Predicate, Ligature, Hook
from typing import Dict, Tuple

class Renderer:
    """
    Renders an ExistentialGraph object into an SVG string.
    """
    def __init__(self, graph: ExistentialGraph):
        self.graph = graph
        self.config = {
            "padding": 20,
            "cut_padding": 15,  # <-- ADD THIS LINE
            "predicate_padding_x": 10,
            "predicate_padding_y": 5,
            "font_size": 14,
            "font_family": "Arial",
            "stroke_width": 2,
            "cut_color": "black",
            "ligature_color": "black",
            "text_color": "black",
        }
        # This will store the calculated positions and dimensions of graph elements.
        self.layout: Dict[str, Dict[str, float]] = {}

    def _calculate_predicate_size(self, p: Predicate) -> Tuple[float, float]:
        """Estimates the size of a predicate based on its text."""
        # This is a simple approximation. A real GUI would use font metrics.
        char_width = self.config["font_size"] * 0.6
        width = len(p.name) * char_width + 2 * self.config["predicate_padding_x"]
        height = self.config["font_size"] + 2 * self.config["predicate_padding_y"]
        return width, height

    def _calculate_layout(self, context: Context = None):
        """
        Recursively calculates the layout for a given context.
        This version now also calculates positions for all predicate hooks.
        """
        if context is None:
            context = self.graph.sheet_of_assertion

        # === 1. Recursive call for children ===
        for child_cut in context.children:
            self._calculate_layout(child_cut)

        # === 2. Calculate sizes of direct contents (predicates) ===
        for p in context.predicates:
            p_width, p_height = self._calculate_predicate_size(p)
            self.layout[p.id] = {"width": p_width, "height": p_height}

        # === 3. Arrange contents and determine context size ===
        current_x = self.config["cut_padding"]
        max_y = 0
        
        # We collect all direct children (cuts and predicates) to arrange them
        direct_contents = context.predicates + context.children
        
        for item in direct_contents:
            item_layout = self.layout[item.id]
            item_layout["x"] = current_x
            item_layout["y"] = self.config["cut_padding"]
            current_x += item_layout["width"] + self.config["padding"]
            if item_layout["height"] > max_y:
                max_y = item_layout["height"]
        
        # Determine the final dimensions of this context
        content_width = current_x - self.config["padding"] + self.config["cut_padding"] if direct_contents else self.config["cut_padding"] * 2
        content_height = max_y + 2 * self.config["cut_padding"] if direct_contents else self.config["cut_padding"] * 2

        if context.parent is None:
            self.layout["canvas"] = {"width": content_width, "height": content_height}
        else:
            self.layout[context.id] = {"width": content_width, "height": content_height}
        
        # === 4. Calculate hook positions for predicates in this context ===
        for p in context.predicates:
            p_layout = self.layout[p.id]
            num_hooks = p.arity
            for i, hook in enumerate(p.hooks):
                # Space hooks evenly along the bottom of the predicate's bounding box
                hook_x = p_layout["x"] + (p_layout["width"] * (i + 1) / (num_hooks + 1))
                hook_y = p_layout["y"] + p_layout["height"]
                hook_id = f"hook_{p.id}_{i}"
                self.layout[hook_id] = {"x": hook_x, "y": hook_y}

    def _render_context(self, context: Context, offset_x: float = 0, offset_y: float = 0) -> str:
        """
        Recursively generates SVG strings for a context and its contents,
        applying the given x/y offset.
        """
        svg_parts = []
        context_id = context.id
        
        # Draw the cut itself, unless it's the Sheet of Assertion
        if context.parent is not None:
            layout = self.layout.get(context_id)
            if layout:
                is_odd = context.get_nesting_level() % 2 != 0
                fill_color = "lightgray" if is_odd else "white"
                
                svg_parts.append(
                    f'<rect x="{offset_x}" y="{offset_y}" width="{layout["width"]}" height="{layout["height"]}" '
                    f'rx="15" ry="15" fill="{fill_color}" stroke="{self.config["cut_color"]}" '
                    f'stroke-width="{self.config["stroke_width"]}"/>'
                )

        # Render predicates in the current context
        for p in context.predicates:
            layout = self.layout.get(p.id)
            if layout:
                text_x = offset_x + layout["x"] + self.config["predicate_padding_x"]
                text_y = offset_y + layout["y"] + self.config["font_size"]
                svg_parts.append(
                    f'<text x="{text_x}" y="{text_y}" font-family="{self.config["font_family"]}" '
                    f'font-size="{self.config["font_size"]}" fill="{self.config["text_color"]}">{p.name}</text>'
                )

        # Recursively render child contexts
        for child_cut in context.children:
            child_layout = self.layout.get(child_cut.id)
            if child_layout:
                # The child's position is relative to its parent context's content area
                child_offset_x = offset_x + child_layout["x"]
                child_offset_y = offset_y + child_layout["y"]
                svg_parts.append(self._render_context(child_cut, child_offset_x, child_offset_y))
        
        return "\n".join(svg_parts)

    def _get_all_ligatures(self) -> Dict[str, Ligature]:
        """Finds all unique ligatures in the graph."""
        ligatures: Dict[str, Ligature] = {}
        q: list[Context] = [self.graph.sheet_of_assertion]
        visited_contexts = set()
        while q:
            context = q.pop(0)
            if context.id in visited_contexts: continue
            visited_contexts.add(context.id)
            for p in context.predicates:
                for h in p.hooks:
                    if h.ligature and h.ligature.id not in ligatures:
                        ligatures[h.ligature.id] = h.ligature
            q.extend(context.children)
        return ligatures

    def to_svg(self) -> str:
        """Generates the complete SVG string for the entire graph."""
        self._calculate_layout()

        canvas_dims = self.layout.get("canvas", {"width": 100, "height": 100})
        width = canvas_dims["width"]
        height = canvas_dims["height"]
        
        # Render contexts and predicates first
        soa_svg = self._render_context(self.graph.sheet_of_assertion, 0, 0)
        
        # === NEW: Render Ligatures ===
        ligature_svg_parts = []
        all_ligatures = self._get_all_ligatures()

        for lig_id, ligature in all_ligatures.items():
            points = []
            
            # This needs to be improved to find the absolute coordinates
            # For now, this is a placeholder demonstrating the idea
            # A full implementation requires passing offsets down through the recursion
            # or calculating absolute coordinates in the layout phase.
            
            # Let's do a simplified absolute coordinate calculation here
            for hook in ligature.hooks:
                hook_layout_id = f"hook_{hook.predicate.id}_{hook.index}"
                hook_pos = self.layout.get(hook_layout_id)
                
                # Find absolute position of the predicate
                current_context = hook.predicate.context
                abs_x, abs_y = 0, 0
                
                # This is a simplification; a better way is to store absolute coords in layout
                path_to_root = []
                temp_ctx = current_context
                while temp_ctx is not None:
                    path_to_root.insert(0, temp_ctx)
                    temp_ctx = temp_ctx.parent

                for i in range(len(path_to_root) - 1):
                    parent_ctx_layout = self.layout.get(path_to_root[i+1].id)
                    if parent_ctx_layout:
                        abs_x += parent_ctx_layout.get('x', 0)
                        abs_y += parent_ctx_layout.get('y', 0)
                
                if hook_pos:
                    points.append( (hook_pos['x'] + abs_x, hook_pos['y'] + abs_y) )
            
            if len(points) > 1:
                # Create a path 'd' attribute string from the points
                path_data = "M " + " L ".join([f"{x},{y}" for x, y in points])
                ligature_svg_parts.append(
                    f'<path d="{path_data}" stroke="{self.config["ligature_color"]}" '
                    f'stroke-width="{self.config["stroke_width"]}" fill="none"/>'
                )

        ligature_svg = "\n".join(ligature_svg_parts)

        return f"""<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg" version="1.1">
    <rect width="100%" height="100%" fill="none" stroke="black" />
    {soa_svg}
    {ligature_svg}
</svg>"""