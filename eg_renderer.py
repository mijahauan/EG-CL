# eg_renderer.py
from eg_model import *
from typing import Dict, Tuple, List, Union

## REWRITTEN ##
# Renderer now works with the general-purpose Node/Hyperedge model.

class Renderer:
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
        self.layout: Dict[str, Dict[str, float]] = {}

    def _calculate_predicate_size(self, node: Node) -> Tuple[float, float]:
        name = node.properties.get("name", "")
        char_width = self.config["font_size"] * 0.6
        width = len(name) * char_width + 2 * self.config["predicate_padding_x"]
        height = self.config["font_size"] + 2 * self.config["predicate_padding_y"]
        return width, height

    def _calculate_layout(self, node_id: str):
        node = self.graph.get_object(node_id)
        if node.node_type != GraphObjectType.CUT: return

        # 1. Recursive call for all children (Bottom-Up)
        for content_id in node.contents:
            content_obj = self.graph.get_object(content_id)
            if isinstance(content_obj, Node) and content_obj.node_type == GraphObjectType.CUT:
                self._calculate_layout(content_id)
            elif isinstance(content_obj, Node) and content_obj.node_type == GraphObjectType.PREDICATE:
                p_width, p_height = self._calculate_predicate_size(content_obj)
                self.layout[content_id] = {"width": p_width, "height": p_height}

        # 2. Arrange contents of the current cut
        current_x = self.config["cut_padding"]
        max_y = 0
        for content_id in node.contents:
            if content_id not in self.layout:
                # This could happen for Hyperedges, which have no intrinsic size
                continue
            item_layout = self.layout[content_id]
            item_layout["x"] = current_x
            item_layout["y"] = self.config["cut_padding"]
            current_x += item_layout["width"] + self.config["padding"]
            if item_layout["height"] > max_y: max_y = item_layout["height"]
        
        # 3. Determine the final dimensions of THIS cut
        content_width = (current_x - self.config["padding"] if node.contents else 0) + self.config["cut_padding"]
        content_height = max_y + (2 * self.config["cut_padding"]) if node.contents else 40
        self.layout[node_id] = {"width": content_width, "height": content_height}

    def _render_node(self, node_id: str, offset_x: float, offset_y: float) -> List[str]:
        svg_parts = []
        node = self.graph.get_object(node_id)
        node_layout = self.layout.get(node.id, {})
        
        abs_x = offset_x + node_layout.get("x", 0)
        abs_y = offset_y + node_layout.get("y", 0)

        if node.node_type == GraphObjectType.CUT:
            if self.graph.get_parent(node.id): # Don't draw rect for SOA
                is_odd = self.graph.get_nesting_level(node.id) % 2 != 0
                fill_color = "lightgray" if is_odd else "white"
                svg_parts.append(
                    f'<rect x="{abs_x}" y="{abs_y}" width="{node_layout.get("width", 0)}" height="{node_layout.get("height", 0)}" '
                    f'rx="15" ry="15" fill="{fill_color}" stroke="{self.config["cut_color"]}" stroke-width="{self.config["stroke_width"]}"/>'
                )
            # Render contents
            for content_id in node.contents:
                svg_parts.extend(self._render_node(content_id, abs_x, abs_y))
        
        elif node.node_type == GraphObjectType.PREDICATE:
            text_x = abs_x + self.config["predicate_padding_x"]
            text_y = abs_y + self.config["font_size"] + self.config["predicate_padding_y"]
            svg_parts.append(
                f'<text x="{text_x}" y="{text_y}" font-family="{self.config["font_family"]}" '
                f'font-size="{self.config["font_size"]}" fill="{self.config["text_color"]}">{node.properties.get("name", "")}</text>'
            )
        return svg_parts

    def to_svg(self) -> str:
        self.layout.clear()
        self._calculate_layout(self.graph.root_id)
        canvas_layout = self.layout[self.graph.root_id]
        
        width = canvas_layout.get("width", 100) + 2 * self.config["padding"]
        height = canvas_layout.get("height", 100) + 2 * self.config["padding"]

        svg_body = self._render_node(self.graph.root_id, self.config["padding"], self.config["padding"])
        
        # NOTE: Ligature rendering would also need to be refactored to use the new model.
        # This involves finding absolute positions of hooks based on the new layout data.

        return f"""<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg" version="1.1">
    <rect width="100%" height="100%" fill="white" />
    <g transform="translate(0, 0)">
    {"\n".join(svg_body)}
    </g>
</svg>"""