"""Source audits cannot transfer a verdict to a different claim or question."""
import unittest

from .report import computation_digest, source_verdict


class SourceAuditTest(unittest.TestCase):
    def setUp(self):
        self.item = {'question_id': 'q_a', 'facts': 'A on 2024-03-04', 'answer': '7 days', 'sources': ['s_a']}
        self.review = {'question_id': 'q_a', 'claim_sha256': computation_digest(self.item), 'verdict': 'supported'}

    def test_verdict_requires_exact_claim_and_question(self):
        self.assertEqual(source_verdict(self.item, [self.review]), 'supported')
        for change in [{'facts': 'A on 2024-03-05'}, {'sources': ['s_b']}, {'answer': '6 days'}, {'question_id': 'q_b'}]:
            self.assertEqual(source_verdict({**self.item, **change}, [self.review]), 'unreviewed')

    def test_conflicting_reviews_are_rejected(self):
        with self.assertRaises(ValueError):
            source_verdict(self.item, [self.review, {**self.review, 'verdict': 'unsupported'}])


if __name__ == '__main__':
    unittest.main()
