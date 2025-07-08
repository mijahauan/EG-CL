import unittest
from eg_editor import EGEditor
from clif_parser import ClifParser
from clif_translation import ClifTranslator # Import the translator for the round-trip test
from eg_model import Predicate, LineOfIdentity, Cut

class TestClifParser(unittest.TestCase):
    def setUp(self):
        self.editor = EGEditor()
        self.parser = ClifParser(self.editor)

    def test_parse_simple_existential(self):
        """Tests parsing '(exists (?x) (Human ?x))'."""
        clif = "(exists (?x) (Human ?x))"
        self.parser.parse(clif)

        # Verification
        lines = [obj for obj in self.editor.model.objects.values() if isinstance(obj, LineOfIdentity)]
        self.assertEqual(len(lines), 1)
        line_id = lines[0].id

        preds = [obj for obj in self.editor.model.objects.values() if isinstance(obj, Predicate)]
        self.assertEqual(len(preds), 1)
        pred = preds[0]
        
        self.assertEqual(pred.label, "Human")
        self.assertEqual(pred.hooks[1], line_id)
        
    def test_parse_nested_expression(self):
        """Tests parsing a nested expression like '(exists (?x) (and (P ?x) (not (Q ?x))))'."""
        clif = "(exists (?x) (and (P ?x) (not (Q ?x))))"
        self.parser.parse(clif)

        preds = {obj.label: obj for obj in self.editor.model.objects.values() if isinstance(obj, Predicate)}
        self.assertIn('P', preds)
        self.assertIn('Q', preds)
        p_pred = preds['P']
        q_pred = preds['Q']
        
        cuts = [obj for obj in self.editor.model.objects.values() if isinstance(obj, Cut)]
        self.assertEqual(len(cuts), 1)
        cut = cuts[0]

        self.assertEqual(self.editor.get_parent_context(p_pred.id), 'SA')
        self.assertEqual(self.editor.get_parent_context(cut.id), 'SA')
        self.assertEqual(self.editor.get_parent_context(q_pred.id), cut.id)
        self.assertIsNotNone(p_pred.hooks[1])
        self.assertEqual(p_pred.hooks[1], q_pred.hooks[1])
        self.assertEqual(self.parser.variable_map['?x'], p_pred.hooks[1])

    def test_round_trip_negated_conjunction(self):
        """Tests that translating a graph and parsing it back results in an equivalent graph."""
        # 1. Build the original graph manually
        p_id = self.editor.add_predicate('P', 1)
        cut_id = self.editor.add_cut()
        q_id = self.editor.add_predicate('Q', 1, parent_id=cut_id)
        self.editor.connect([(p_id, 1), (q_id, 1)])

        # 2. Translate it to CLIF using a new translator instance
        translator = ClifTranslator(self.editor)
        clif_string = translator.translate()
        self.assertEqual(clif_string, "(exists (?v1) (and (P ?v1) (not (Q ?v1))))")

        # 3. Parse the CLIF into a NEW graph
        new_editor = EGEditor()
        new_parser = ClifParser(new_editor)
        new_parser.parse(clif_string)

        # 4. Translate the NEW graph back to CLIF
        new_translator = ClifTranslator(new_editor)
        new_clif_string = new_translator.translate()
        
        # 5. Assert that the round-trip result is identical
        self.assertEqual(clif_string, new_clif_string)