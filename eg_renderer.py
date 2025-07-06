# eg_renderer.py
from eg_model import ExistentialGraph, Context, Predicate, Ligature, Hook
from typing import Dict, Tuple, List, Union

class Renderer:
    """
    Renders an ExistentialGraph object into an SVG string using a robust,
    bottom-up layout algorithm.
    """
    def __init__(self, graph: ExistentialGraph):
        self.graph = graph
        self.config = {
            "padding": 15,
            "cut_padding": 20,
            "predicate_padding_x": 10,
            "predicate_padding_y": 5,
            "font_size": 16,
            "font_family": "Arial, Helvetica, sans-serif",
            "stroke_width": 2,
            "cut_color": "black",
            "ligature_color": "black",
            "text_color": "black",
        }
        # layout stores calculated dimensions and RELATIVE positions
        self.layout: Dict[str, Dict[str, float]] = {}

    def _calculate_predicate_size(self, p: Predicate) -> Tuple[float, float]:
        """Estimates the size of a predicate based on its text."""
        char_width = self.config["font_size"] * 0.6
        width = len(p.name) * char_width + 2 * self.config["predicate_padding_x"]
        height = self.config["font_size"] + 2 * self.config["predicate_padding_y"]
        return width, height

    ## REWRITTEN ##
    def _calculate_layout(self, context: Context = None):
        """
        Calculates the layout for the entire graph using a recursive, bottom-up approach.
        1. Recursively calculates layout for all children, determining their dimensions.
        2. Arranges the contents (predicates and child cuts) of the current context.
        3. Calculates and stores the dimensions of the current context based on its contents.
        """
        if context is None:
            context = self.graph.sheet_of_assertion

        # === 1. Recursive call for all children (Bottom-Up) ===
        # This ensures we know the dimensions of children before arranging them.
        for child_cut in context.children:
            self._calculate_layout(child_cut)

        # === 2. Calculate sizes of direct predicates in this context ===
        for p in context.predicates:
            p_width, p_height = self._calculate_predicate_size(p)
            self.layout[p.id] = {"width": p_width, "height": p_height}

        # === 3. Arrange contents (predicates and child cuts) horizontally ===
        current_x = self.config["cut_padding"]
        max_y = 0
        
        # We collect all direct children to arrange them
        direct_contents: List[Union[Predicate, Context]] = context.predicates + context.children
        
        for item in direct_contents:
            item_layout = self.layout[item.id]
            # Store the item's position RELATIVE to the current context
            item_layout["x"] = current_x
            item_layout["y"] = self.config["cut_padding"]
            
            current_x += item_layout["width"] + self.config["padding"]
            if item_layout["height"] > max_y:
                max_y = item_layout["height"]
        
        # === 4. Determine the final dimensions of THIS context ===
        # Width is the final position of the last item + padding
        content_width = (current_x - self.config["padding"] if direct_contents else 0) + self.config["cut_padding"]
        # Height is the max height of any item + padding
        content_height = max_y + (2 * self.config["cut_padding"]) if direct_contents else 40

        if context.parent is None:
            # For the top-level canvas, add extra padding
            self.layout["canvas"] = {
                "width": content_width + self.config["padding"], 
                "height": content_height + self.config["padding"]
            }
        else:
            self.layout[context.id] = {"width": content_width, "height": content_height}
        
    ## REWRITTEN ##
    def _render_context(self, context: Context, offset_x: float, offset_y: float) -> str:
        """
        Recursively generates SVG strings for a context and its contents,
        using parent offsets to calculate absolute positions.
        """
        svg_parts = []
        
        # Draw the cut itself (unless it's the Sheet of Assertion)
        if context.parent is not None:
            layout = self.layout.get(context.id, {})
            is_odd = context.get_nesting_level() % 2 != 0
            fill_color = "lightgray" if is_odd else "white"
            
            svg_parts.append(
                f'<rect x="{offset_x}" y="{offset_y}" width="{layout.get("width", 0)}" height="{layout.get("height", 0)}" '
                f'rx="15" ry="15" fill="{fill_color}" stroke="{self.config["cut_color"]}" '
                f'stroke-width="{self.config["stroke_width"]}"/>'
            )

        # Render predicates in the current context
        for p in context.predicates:
            layout = self.layout.get(p.id, {})
            # Absolute position = parent offset + predicate's relative position
            abs_x = offset_x + layout.get("x", 0)
            abs_y = offset_y + layout.get("y", 0)
            
            text_x = abs_x + self.config["predicate_padding_x"]
            text_y = abs_y + self.config["font_size"] + self.config["predicate_padding_y"]
            svg_parts.append(
                f'<text x="{text_x}" y="{text_y}" font-family="{self.config["font_family"]}" '
                f'font-size="{self.config["font_size"]}" fill="{self.config["text_color"]}">{p.name}</text>'
            )

        # Recursively render child contexts
        for child_cut in context.children:
            child_layout = self.layout.get(child_cut.id, {})
            # The child's new offset is its parent's offset plus its own relative position
            child_offset_x = offset_x + child_layout.get("x", 0)
            child_offset_y = offset_y + child_layout.get("y", 0)
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
    
    ## REWRITTEN ##
    def _render_ligatures(self) -> str:
        """
        Calculates absolute hook positions and renders all ligatures as SVG paths.
        This must be called AFTER the main layout calculation is complete.
        """
        ligature_svg_parts = []
        all_ligatures = self._get_all_ligatures()
        
        # First, calculate and store the absolute position of ALL elements
        abs_positions = {}
        q = [(self.graph.sheet_of_assertion, self.config["padding"], self.config["padding"])]
        
        while q:
            context, parent_abs_x, parent_abs_y = q.pop(0)
            
            for item in context.predicates + context.children:
                item_layout = self.layout.get(item.id, {})
                item_abs_x = parent_abs_x + item_layout.get("x", 0)
                item_abs_y = parent_abs_y + item_layout.get("y", 0)
                abs_positions[item.id] = (item_abs_x, item_abs_y)
                
                if isinstance(item, Context):
                    q.append((item, item_abs_x, item_abs_y))

        # Now, render the ligatures using the calculated absolute positions
        for lig in all_ligatures.values():
            points = []
            if len(lig.hooks) < 2: continue
            
            for hook in lig.hooks:
                p = hook.predicate
                p_layout = self.layout.get(p.id, {})
                p_abs_pos = abs_positions.get(p.id, (0, 0))
                
                # Hook position is relative to the predicate's top-left corner
                num_hooks = p.arity
                hook_rel_x = (p_layout.get("width", 0) * (hook.index + 1) / (num_hooks + 1))
                hook_rel_y = p_layout.get("height", 0)
                
                # Absolute hook position = predicate's absolute position + hook's relative position
                points.append((p_abs_pos[0] + hook_rel_x, p_abs_pos[1] + hook_rel_y))
            
            path_data = "M " + " L ".join([f"{x:.2f},{y:.2f}" for x, y in points])
            ligature_svg_parts.append(
                f'<path d="{path_data}" stroke="{self.config["ligature_color"]}" '
                f'stroke-width="{self.config["stroke_width"]}" fill="none" stroke-linecap="round"/>'
            )
            
        return "\n".join(ligature_svg_parts)

    def to_svg(self) -> str:
        """Generates the complete SVG string for the entire graph."""
        # Clear previous layout and recalculate everything
        self.layout.clear()
        self._calculate_layout()

        canvas_dims = self.layout.get("canvas", {"width": 100, "height": 100})
        width = canvas_dims.get("width", 100)
        height = canvas_dims.get("height", 100)
        
        # Render contexts and predicates recursively
        canvas_padding = self.config["padding"]
        soa_svg = self._render_context(self.graph.sheet_of_assertion, canvas_padding, canvas_padding)
        
        # Render ligatures now that all absolute positions can be determined
        ligature_svg = self._render_ligatures()

        return f"""<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg" version="1.1">
    <rect width="100%" height="100%" fill="white" />
    <g transform="translate(0, 0)">
    {soa_svg}
    {ligature_svg}
    </g>
</svg>"""