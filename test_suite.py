# test_suite.py
import unittest
import xml.etree.ElementTree as ET
import os
from eg_model import *
from eg_logic import *
from eg_renderer import *
from session_model import * 
from serialization import * 

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
        p_id, _ = self.editor.add_predicate("P", 1, self.soa_id)
        cut_id, _ = self.editor.add_cut(self.soa_id)
        self.assertIn(p_id, self.graph.get_object(self.soa_id).contents)
        self.assertIn(cut_id, self.graph.get_object(self.soa_id).contents)
        self.assertEqual(self.graph.get_parent(p_id).id, self.soa_id)
        print("  - OK: Predicate and Cut added correctly.")

    def test_nesting_level(self):
        self.assertEqual(self.graph.get_nesting_level(self.soa_id), 0)
        cut1_id, _ = self.editor.add_cut(self.soa_id)
        self.assertEqual(self.graph.get_nesting_level(cut1_id), 1)
        cut2_id, _ = self.editor.add_cut(cut1_id)
        self.assertEqual(self.graph.get_nesting_level(cut2_id), 2)
        print("  - OK: Nesting levels are correct.")

class TestNewLogic(unittest.TestCase):
    def setUp(self):
        self.graph = ExistentialGraph()
        self.editor = EGEditor(self.graph)
        self.soa_id = self.graph.root_id
        print(f"\n----- Running New Logic Test: {self._testMethodName} -----")

    def test_connect_and_sever(self):
        p_id, _ = self.editor.add_predicate("P", 1, self.soa_id)
        q_id, _ = self.editor.add_predicate("Q", 1, self.soa_id)
        
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
        self.editor.add_predicate("P", 0, self.soa_id)
        cut1_id, _ = self.editor.add_cut(self.soa_id)
        self.editor.add_predicate("Q", 0, cut1_id)
        self.editor.add_predicate("T", 0, cut1_id)
        cut2_id, _ = self.editor.add_cut(cut1_id)
        self.editor.add_predicate("R", 0, cut2_id)
        self.editor.add_predicate("S", 0, cut2_id)

        cut1_contents = self.graph.get_object(cut1_id).contents
        q_id = cut1_contents[0]
        t_id = cut1_contents[1]
        self.assertEqual(self.graph.get_object(q_id).properties['name'], 'Q')
        self.assertEqual(self.graph.get_object(t_id).properties['name'], 'T')
        
        svg = self.renderer.to_svg()
        root = ET.fromstring(svg)
        ns = {'svg': 'http://www.w3.org/2000/svg'}
        
        texts = {t.text: (float(t.get('x')), float(t.get('y'))) for t in root.findall('.//svg:text', ns)}
        self.assertTrue(texts['Q'][0] < texts['T'][0])
        self.assertTrue(texts['T'][0] < texts['R'][0])
        print("  - OK: Renderer correctly preserves element order.")

class TestSessionManagement(unittest.TestCase):
    def setUp(self):
        self.folio = Folio("Test Project")
        self.test_filepath = "test_folio.json"
        print(f"\n----- Running Session Management Test: {self._testMethodName} -----")

    def tearDown(self):
        if os.path.exists(self.test_filepath):
            os.remove(self.test_filepath)

    def test_folio_creation_and_action_logging(self):
        graph = self.folio.new_graph("My First Proof")
        editor = EGEditor(graph)
        session = GameSession(graph_id=graph.root_id)
        
        soa_id = graph.root_id
        _, action1 = editor.add_predicate("P", 0, soa_id)
        session.history.append(action1)
        
        _, action2 = editor.add_cut(soa_id)
        session.history.append(action2)

        self.assertIn("My First Proof", self.folio.graphs)
        self.assertEqual(len(session.history), 2)
        self.assertEqual(session.history[0].action_name, "add_predicate")
        self.assertEqual(session.history[1].parameters['parent_id'], soa_id)
        print("  - OK: Folio, Graph, and Session action logging work.")
        
    def test_serialization_round_trip(self):
        graph = self.folio.new_graph("Complex Graph")
        editor = EGEditor(graph)
        session = GameSession(graph_id=graph.root_id)
        self.folio.sessions[session.id] = session
        
        soa_id = graph.root_id
        p_id, p_act = editor.add_predicate("P", 1, soa_id)
        session.history.append(p_act)
        q_id, q_act = editor.add_predicate("Q", 1, soa_id)
        session.history.append(q_act)
        
        ep1 = {"node_id": p_id, "hook_index": 0}
        ep2 = {"node_id": q_id, "hook_index": 0}
        conn_act = editor.connect(ep1, ep2)
        session.history.append(conn_act)

        save_folio(self.folio, self.test_filepath)
        self.assertTrue(os.path.exists(self.test_filepath))
        loaded_folio = load_folio(self.test_filepath)

        self.assertEqual(self.folio.name, loaded_folio.name)
        self.assertEqual(len(self.folio.graphs), len(loaded_folio.graphs))
        loaded_session = list(loaded_folio.sessions.values())[0]
        self.assertEqual(len(session.history), len(loaded_session.history))
        self.assertEqual(session.history[2].parameters, loaded_session.history[2].parameters)
        print("  - OK: Serialization round-trip successful.")


if __name__ == '__main__':
    unittest.main()