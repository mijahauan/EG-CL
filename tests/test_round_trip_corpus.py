import unittest
import json

# Absolute imports from the project root
from tests.clif_corpus import CORPUS
from eg_model import GraphModel
from clif_parser import ClifParser
from clif_translation import ClifTranslator 
from eg_editor import EGEditor
from serialization import EgClEncoder


class TestRoundTripCorpus(unittest.TestCase):

    def test_clif_corpus_round_trip_idempotency(self):
        """
        Iterates through the CLIF corpus and performs a round-trip test
        to ensure the translation process is idempotent.

        The test follows these steps:
        1. Parse the original CLIF string into a graph object (graph1).
        2. Translate graph1 back into a CLIF string (clif1).
        3. Parse the new CLIF string (clif1) into a second graph object (graph2).
        4. Translate graph2 back into a CLIF string (clif2).
        5. Assert that the first and second translated CLIF strings are identical.
        """
        for item in CORPUS:
            clif_original = item['clif']
            description = item['description']

            with self.subTest(msg=f"Testing: {description}"):
                # 1. Parse the original CLIF string into the first editor
                editor1 = EGEditor()
                parser1 = ClifParser(editor1)
                parser1.parse(clif_original) # This modifies editor1
                self.assertIsInstance(editor1.model, GraphModel)

                # 2. Translate the graph from the first editor
                translator1 = ClifTranslator(editor1)
                clif1 = translator1.translate()
                self.assertIsInstance(clif1, str)

                # 3. Parse the translated CLIF string into the second editor
                editor2 = EGEditor()
                parser2 = ClifParser(editor2)
                parser2.parse(clif1) # This modifies editor2
                self.assertIsInstance(editor2.model, GraphModel)
                
                # 4. Translate the graph from the second editor
                translator2 = ClifTranslator(editor2)
                clif2 = translator2.translate()
                self.assertIsInstance(clif2, str)

                # 5. Assert that the translations are idempotent
                self.assertEqual(clif1, clif2,
                                 f"\nRound-trip idempotency failed for: {description}"
                                 f"\nOriginal CLIF: {clif_original}"
                                 f"\nFirst translation: {clif1}"
                                 f"\nSecond translation: {clif2}")

if __name__ == '__main__':
    unittest.main()