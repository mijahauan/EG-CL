# test_suite.py
import unittest
import xml.etree.ElementTree as ET 
from eg_model import *
from eg_logic import *
from eg_renderer import *

## REWRITTEN ##
# The entire test suite is updated to use the new API, operating on Nodes,
# Hyperedges, and IDs instead of the old direct object references.

class TestNewModel(unittest.TestCase):
    def setUp(self):
        self.graph = ExistentialGraph()
        self.editor = EGEditor(self.graph)
        self.soa_id = self.graph.root_id
        print(f"\n----- Running New Model Test: {self._testMethodName} -----")

    def test_model_creation(self):
        self.assertIsNotNone(self.graph.get_object(self.soa_id))
        self.assertEqual(self.graph.get_object(self.soa_id).node_type, GraphObjectType.CUT)
        print("  - OK: Graph and Sheet of Assertion created.")

    def test_add_predicate_and_cut(self):
        p_id = self.editor.add_predicate("P", 1, self.soa_id)
        cut_id = self.editor.add_cut(self.soa_id)
        self.assertIn(p_id, self.graph.get_object(self.soa_id).contents)
        self.assertIn(cut_id, self.graph.get_object(self.soa_id).contents)
        self.assertEqual(self.graph.get_parent(p_id).id, self.soa_id)
        print("  - OK: Predicate and Cut added correctly.")

    def test_nesting_level(self):
        self.assertEqual(self.graph.get_nesting_level(self.soa_id), 0)
        cut1_id = self.editor.add_cut(self.soa_id)
        self.assertEqual(self.graph.get_nesting_level(cut1_id), 1)
        cut2_id = self.editor.add_cut(cut1_id)
        self.assertEqual(self.graph.get_nesting_level(cut2_id), 2)
        print("  - OK: Nesting levels are correct.")

class TestNewLogic(unittest.TestCase):
    def setUp(self):
        self.graph = ExistentialGraph()
        self.editor = EGEditor(self.graph)
        self.soa_id = self.graph.root_id
        print(f"\n----- Running New Logic Test: {self._testMethodName} -----")

    def test_connect_and_sever(self):
        p_id = self.editor.add_predicate("P", 1, self.soa_id)
        q_id = self.editor.add_predicate("Q", 1, self.soa_id)
        
        ep1 = {"node_id": p_id, "hook_index": 0}
        ep2 = {"node_id": q_id, "hook_index": 0}
        
        self.editor.connect(ep1, ep2)
        lig_id = self.editor.find_ligature_for_endpoint(ep1)
        self.assertIsNotNone(lig_id)
        self.assertEqual(lig_id, self.editor.find_ligature_for_endpoint(ep2))
        self.assertEqual(len(self.graph.get_object(lig_id).endpoints), 2)
        print("  - OK: Connect works.")
        
        self.editor.sever_endpoint(ep1)
        self.assertNotEqual(self.editor.find_ligature_for_endpoint(ep1), self.editor.find_ligature_for_endpoint(ep2))
        new_lig_id = self.editor.find_ligature_for_endpoint(ep1)
        self.assertEqual(len(self.graph.get_object(new_lig_id).endpoints), 1)
        print("  - OK: Sever works.")

class TestNewRenderer(unittest.TestCase):
    def setUp(self):
        self.graph = ExistentialGraph()
        self.editor = EGEditor(self.graph)
        self.renderer = Renderer(self.graph)
        self.soa_id = self.graph.root_id
        print(f"\n----- Running New Renderer Test: {self._testMethodName} -----")

    def test_render_order_is_preserved(self):
        """
        Tests that the new model and renderer correctly preserve creation
        order and solve the old layout problem.
        Intended Layout: (P (Q T (R S)))
        """
        self.editor.add_predicate("P", 0, self.soa_id)
        cut1_id = self.editor.add_cut(self.soa_id)
        self.editor.add_predicate("Q", 0, cut1_id)
        self.editor.add_predicate("T", 0, cut1_id)
        cut2_id = self.editor.add_cut(cut1_id)
        self.editor.add_predicate("R", 0, cut2_id)
        self.editor.add_predicate("S", 0, cut2_id)

        # Check the actual contents order
        cut1_contents = self.graph.get_object(cut1_id).contents
        q_id = cut1_contents[0]
        t_id = cut1_contents[1]
        self.assertEqual(self.graph.get_object(q_id).properties['name'], 'Q')
        self.assertEqual(self.graph.get_object(t_id).properties['name'], 'T')
        
        svg = self.renderer.to_svg()
        root = ET.fromstring(svg)
        ns = {'svg': 'http://www.w3.org/2000/svg'}
        
        texts = {t.text: (float(t.get('x')), float(t.get('y'))) for t in root.findall('.//svg:text', ns)}

        # Assert that the visual layout order matches the creation order
        self.assertTrue(texts['Q'][0] < texts['T'][0])
        self.assertTrue(texts['T'][0] < texts['R'][0])
        print("  - OK: Renderer correctly preserves element order.")

if __name__ == '__main__':
    unittest.main()