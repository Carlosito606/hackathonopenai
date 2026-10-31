"""Interrupted paired runs never duplicate rows or mix source/model identities."""
import json
import tempfile
import unittest
from pathlib import Path

from .checkpoint import read_checkpoint, recover, validate_resume


class CheckpointTest(unittest.TestCase):
    def test_recovers_common_prefix_including_reader_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'baseline-r1').mkdir()
            for base in [root, root / 'baseline-r1']:
                for name in ['candidates.jsonl', 'evidence.jsonl', 'predictions.jsonl']:
                    # The second question reached R1, but has not completed R4.
                    count = 2 if base.name == 'baseline-r1' else 1
                    (base / name).write_text(''.join(json.dumps({'question_id': q}) + '\n'
                                                    for q in ['q_a', 'q_b'][:count]))
            (root / 'computations.jsonl').write_text(json.dumps({'question_id': 'q_a', 'computed': True}) + '\n')
            (root / 'reader_status.jsonl').write_text(json.dumps({'question_id': 'q_a', 'r1': 'answered', 'r4': 'timeout'}) + '\n')
            count, computations, statuses = recover(root, ['q_a', 'q_b'], True)
            self.assertEqual(count, 1)
            self.assertTrue(computations[0]['computed'])
            self.assertEqual(statuses[0]['r4'], 'timeout')
            for path in root.rglob('*.jsonl'):
                self.assertEqual(len(read_checkpoint(path)), 1)

    def test_truncated_last_append_is_recoverable(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'checkpoint.jsonl'
            path.write_text('{"question_id":"q_a"}\n{"question_id":')
            self.assertEqual(read_checkpoint(path), [{'question_id': 'q_a'}])

    def test_unicode_line_separators_inside_answers_are_not_record_boundaries(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'checkpoint.jsonl'
            item = {'question_id': 'q_a', 'answer': 'north\u2028south\u0085east'}
            path.write_text(json.dumps(item, ensure_ascii=False) + '\n')
            self.assertEqual(read_checkpoint(path), [item])

    def test_corruption_before_last_append_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'checkpoint.jsonl'
            path.write_text('corrupt\n{"question_id":"q_a"}\n')
            with self.assertRaises(json.JSONDecodeError):
                read_checkpoint(path)

    def test_foreign_question_order_is_not_rewritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / 'candidates.jsonl'
            original = '{"question_id":"q_foreign"}\n'
            path.write_text(original)
            with self.assertRaises(ValueError):
                recover(root, ['q_expected'], False)
            self.assertEqual(path.read_text(), original)

    def test_resume_rejects_changed_source_and_model(self):
        metadata = {'git_sha': 'original', 'source_dirty': False,
                    'flags': {'local': 'http://127.0.0.1:8899', 'reader_revision': 'rev_a'}}
        validate_resume(metadata, metadata)
        for changed in [{**metadata, 'git_sha': 'different'}, {**metadata, 'source_dirty': True},
                        {**metadata, 'candidate_manifest': {'sha256': 'changed-export'}},
                        {**metadata, 'counting_cache_sha256': 'changed-items'},
                        {**metadata, 'flags': {**metadata['flags'], 'reader_revision': 'rev_b'}}]:
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                validate_resume(metadata, changed)


if __name__ == '__main__':
    unittest.main()
