import unittest
from eg_editor import EGEditor
from clif_parser import ClifParser
from eg_model import Predicate, LineOfIdentity, Cut

class TestClifParser(unittest.TestCase):
    def setUp(self):
        self.editor = EGEditor()
        self.parser = ClifParser(self.editor)

    def test_parse_simple_existential(self):
        clif = "(exists (?x) (Human ?x))"
        self.parser.parse(clif)
        lines = [obj for obj in self.editor.model.objects.values() if isinstance(obj, LineOfIdentity)]
        self.assertEqual(len(lines), 1)
        line_id = lines[0].id
        preds = [obj for obj in self.editor.model.objects.values() if isinstance(obj, Predicate)]
        self.assertEqual(len(preds), 1)
        pred = preds[0]
        self.assertEqual(pred.label, "Human")
        self.assertEqual(pred.hooks[1], line_id)

    def test_parse_nested_expression(self):
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