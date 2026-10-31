"""Exact chunk selection and fail-closed checks for shared R1 manifests."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from . import rocket
from .manifest import CandidateManifest, reconstruction_signature
from .test_contract import fixture


class ManifestTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.q, self.h, _ = fixture()
        # Several distinct windows in the SAME turn; the export asks for the last
        # one first. Mapping repeated turn ids by occurrence would select wrongly.
        content = ('early ' * 180) + ('middle ' * 180) + ('late\u2028detail ' * 120)
        self.h['sessions'][0]['turns'][0]['content'] = content
        self.pieces = rocket.r1().split_text(content)
        self.rows = [[self.h['sessions'][0]['session_id'], 0, len(self.pieces) - 1, 0.9],
                     [self.h['sessions'][0]['session_id'], 0, 0, 0.8]]
        self.export()

    def export(self):
        sid = self.h['sessions'][0]['session_id']
        cands = [{'session_id': sid, 'si': 0, 'turn': 0, 'role': 'user',
                  'text': self.pieces[row[2]], 'score': row[3]} for row in self.rows]
        evidence = rocket.baseline_assemble(self.q, self.h, cands)['evidence']
        values = {
            'meta.json': {'git_sha': 'abcdef0 (synthetic source)'},
            'candidates.jsonl': {'question_id': self.q['question_id'], 'ranked': self.rows},
            'evidence.jsonl': {'question_id': self.q['question_id'],
                               'sessions': [e['id'] for e in evidence],
                               'chars': sum(len(e['text']) for e in evidence)},
        }
        for name, value in values.items():
            (self.folder / name).write_text(json.dumps(value) + '\n')

    def test_exact_indices_preserve_ranked_order_and_current_history_date(self):
        before = copy.deepcopy(self.h)
        cands = CandidateManifest(self.folder).rebuild(self.q, self.h)
        self.assertEqual([c['text'] for c in cands], [self.pieces[-1], self.pieces[0]])
        self.assertEqual(cands[0]['date'], self.h['sessions'][0]['date'])
        self.assertIn('\u2028', cands[0]['text'])
        self.assertEqual(self.h, before)

    def test_ambiguous_turn_only_manifest_is_rejected(self):
        p = self.folder / 'candidates.jsonl'
        p.write_text(json.dumps({'question_id': self.q['question_id'], 'ranked': [self.rows[0][:2] + [0.9]]}))
        with self.assertRaisesRegex(ValueError, 'chunk_idx'):
            CandidateManifest(self.folder).rebuild(self.q, self.h)

    def test_foreign_session_negative_indices_and_nonfinite_scores_are_rejected(self):
        for row in [['foreign', 0, 0, 1.0], [self.rows[0][0], -1, 0, 1.0],
                    [self.rows[0][0], 0, -1, 1.0], [self.rows[0][0], 0, 0, float('nan')]]:
            with self.subTest(row=row):
                (self.folder / 'candidates.jsonl').write_text(json.dumps(
                    {'question_id': self.q['question_id'], 'ranked': [row]}))
                with self.assertRaises(ValueError):
                    CandidateManifest(self.folder).rebuild(self.q, self.h)

    def test_incomplete_or_changed_evidence_cannot_silently_become_a_baseline(self):
        (self.folder / 'evidence.jsonl').write_text(json.dumps(
            {'question_id': self.q['question_id'], 'sessions': [], 'chars': 0}))
        with self.assertRaisesRegex(ValueError, 'does not match'):
            CandidateManifest(self.folder).rebuild(self.q, self.h)

    def test_missing_question_and_duplicate_exports_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'does not cover'):
            CandidateManifest(self.folder).rebuild({**self.q, 'question_id': 'other'}, self.h)
        p = self.folder / 'candidates.jsonl'
        p.write_text(p.read_text() * 2)
        with self.assertRaisesRegex(ValueError, 'duplicate question'):
            CandidateManifest(self.folder)

    def test_only_the_unused_retrieve_body_may_differ_for_manifest_reconstruction(self):
        source = 'CHUNK, OVERLAP = 900, 200\ndef split_text(text):\n return text[:CHUNK]\ndef retrieve(h, n=80):\n return h[:n]\n'
        wider_pool = source.replace('return h[:n]', 'return h[:n + 40]')
        self.assertEqual(reconstruction_signature(source), reconstruction_signature(wider_pool))
        for changed in [source.replace('900, 200', '800, 200'),
                        source.replace('text[:CHUNK]', 'text[:OVERLAP]'),
                        source.replace('n=80', 'n=120'),
                        source + '\nCHUNK = 100\n']:
            self.assertNotEqual(reconstruction_signature(source), reconstruction_signature(changed))


if __name__ == '__main__':
    unittest.main()
