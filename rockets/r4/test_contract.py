"""Four-stage and reader/score integration on a synthetic history, without Reactor."""
import json
import os
import re
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from . import rocket, run


def fixture():
    q = {'question_id': 'q_synthetic', 'history_id': 'h_synthetic', 'question_date': '2024/03/11 (Mon) 09:00',
         'question': 'How many days ago did I visit the botanical garden?'}
    h = {'history_id': q['history_id'], 'sessions': [{'session_id': 's_synthetic', 'date': '2024/03/05 (Tue) 09:00',
         'turns': [{'role': 'user', 'content': 'I visited the botanical garden yesterday.'}]}]}
    c = {'si': 0, 'session_id': 's_synthetic', 'date': h['sessions'][0]['date'], 'turn': 0, 'kind': 'turn',
         'role': 'user', 'text': h['sessions'][0]['turns'][0]['content'], 'score': 1.0, 'notes': {}}
    return q, h, [c]


class ContractTest(unittest.TestCase):
    def test_retrieve_supports_r1_facade_without_private_reranker(self):
        q, h, cands = fixture()
        module = SimpleNamespace(Embedder=Mock(return_value=object()), reranker=Mock(),
                                 retrieve=Mock(return_value=cands))
        with patch.object(rocket, 'r1', return_value=module), patch.object(rocket, '_emb', None), \
                patch.dict(os.environ, {'R4_DEVICE': 'cpu'}):
            result = rocket.retrieve(q, h)
        module.reranker.assert_called_once_with(device='cpu')
        self.assertEqual(result[0]['text'], cands[0]['text'])

    def test_missing_final_answer_remains_a_reader_failure(self):
        result = {'question_id': 'q_synthetic', 'status': 'timeout', 'reply': 'I need more time.'}
        self.assertEqual(run.prediction(result), {'question_id': 'q_synthetic', 'abstain': False,
                                                  'answer': '', 'citations': []})

    def test_stages_preserve_inputs_and_ground_facts_in_evidence(self):
        q, h, cands = fixture()
        before = json.dumps([q, h, cands], sort_keys=True)
        enriched = rocket.enrich(q, h, cands)
        pack = rocket.assemble(q, h, enriched)
        decision = rocket.decide(q, h, enriched, pack)
        self.assertEqual(set(rocket.STAGES), {'retrieve', 'enrich', 'assemble', 'decide'})
        self.assertEqual(set(pack), {'evidence', 'facts'})
        self.assertIn('Computed: 7 days', pack['facts'])
        self.assertIn('[E1]', pack['facts'])
        self.assertIn('Computed: 7 days', decision['question'])
        self.assertIn('e.g. "<answer> [E4]"', decision['question'])
        self.assertEqual(before, json.dumps([q, h, cands], sort_keys=True))
        self.assertTrue(all(e['id'] == 's_synthetic' for e in pack['evidence']))

    def test_omitted_excerpts_cannot_supply_facts(self):
        q, h, cands = fixture()
        enriched = rocket.enrich(q, h, cands)
        result = rocket.grounded_computation(q, enriched, [{'id': 's_synthetic', 'date': '2024-03-05', 'text': 'unrelated'}])
        self.assertFalse(result['computed'])

    def test_no_computation_uses_the_identical_r1_pack_and_prompt(self):
        q, h, cands = fixture()
        h['sessions'][0]['turns'][0]['content'] = 'I enjoy botanical gardens.'
        cands[0]['text'] = h['sessions'][0]['turns'][0]['content']
        enriched = rocket.enrich(q, h, cands)
        baseline = rocket.baseline_assemble(q, h, cands)
        pack = rocket.assemble(q, h, enriched)
        self.assertEqual(pack, baseline)
        self.assertEqual(rocket.decide(q, h, enriched, pack), rocket.baseline_decide(q, h, cands, baseline))

    def test_r1_previous_user_context_can_ground_event(self):
        q, h, cands = fixture()
        h['sessions'][0]['turns'].append({'role': 'assistant', 'content': 'That sounds like a lovely visit.'})
        cands = [{**cands[0], 'role': 'assistant', 'turn': 1, 'text': h['sessions'][0]['turns'][1]['content']}]
        enriched = rocket.enrich(q, h, cands)
        pack = rocket.assemble(q, h, enriched)
        self.assertIn('Computed: 7 days', pack['facts'])
        self.assertIn('[E1]', pack['facts'])

    def test_contract_candidates_do_not_need_r1_private_fields(self):
        q, h, cands = fixture()
        cands = [{key: value for key, value in cands[0].items() if key not in ('si', 'date')}]
        pack = rocket.assemble(q, h, rocket.enrich(q, h, cands))
        self.assertIn('Computed: 7 days', pack['facts'])

    def test_session_units_with_no_turn_are_valid_docking_inputs(self):
        for role in (None, 'user'):
            q, h, cands = fixture()
            cands = [{**cands[0], 'turn': None, 'kind': 'session', 'role': role}]
            pack = rocket.assemble(q, h, rocket.enrich(q, h, cands))
            self.assertEqual(pack['facts'], '')
            self.assertEqual(pack['evidence'][0]['id'], 's_synthetic')

    def test_foreign_history_source_is_rejected(self):
        q, h, cands = fixture()
        cands[0]['session_id'] = 's_another_history'
        with self.assertRaises(ValueError):
            rocket.assemble(q, h, cands)

    def test_paired_runner_and_official_score(self):
        scorer = Path(os.environ.get('R4_SCORER', 'score.py')).resolve()
        if not scorer.exists():
            self.skipTest('pass the official scorer on the development machine')
        q, h, cands = fixture()

        class Reader(BaseHTTPRequestHandler):
            def do_GET(self):
                payload = json.dumps({'data': [{'id': 'synthetic-protocol-fixture'}]}).encode()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def do_POST(self):
                request = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                text = request['messages'][0]['content']
                ref = re.search(r'\[ref:([0-9a-f]{8})\]', text).group(1)
                reply = {'choices': [{'message': {'content': f'# FINAL ANSWER [ref:{ref}]: 7 days [E1]'}}]}
                payload = json.dumps(reply).encode()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(('127.0.0.1', 0), Reader)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                (root / 'splits').mkdir()
                (root / 'splits/dev_holdout.txt').write_text('q_held_out\n')
                data = root / 'dev'
                data.mkdir()
                for file, values in [('questions.jsonl', [q, {**q, 'question_id': 'q_held_out'}]),
                                     ('histories.jsonl', [h]), ('gold.jsonl', [
                                         {'question_id': q['question_id'], 'question_type': 'temporal-reasoning',
                                          'abstain': False, 'answer': '7 days', 'evidence': ['s_synthetic']},
                                         {'question_id': 'q_held_out', 'question_type': 'temporal-reasoning',
                                          'abstain': False, 'answer': '7 days', 'evidence': ['s_synthetic']}])]:
                    (data / file).write_text(''.join(json.dumps(v) + '\n' for v in values))
                argv = ['run', '--data', str(data), '--candidate-cache', str(root / 'cache'),
                        '--local', f'http://127.0.0.1:{server.server_port}', '--reader', 'synthetic-protocol-fixture',
                        '--scorer', str(scorer), '--run-id', 'synthetic']
                with patch.object(run, 'ROOT', root), patch.object(rocket, 'retrieve', return_value=cands), \
                        patch.object(sys, 'argv', argv), patch.object(run.subprocess, 'check_output',
                            side_effect=['0' * 40, b'', '0' * 40, b'', '0' * 40, b'']):
                    ask = __import__('ask')
                    local = ask.local
                    calls = []

                    def interrupted(args, plan):
                        calls.append(plan['question_id'])
                        if len(calls) == 2:
                            raise ConnectionError('synthetic reader interruption between R1 and R4')
                        return local(args, plan)

                    with patch.object(ask, 'local', side_effect=interrupted), self.assertRaises(ConnectionError):
                        run.main()
                    argv.append('--resume')
                    run.main()
                    argv.remove('--resume')
                    argv[argv.index('--run-id') + 1] = 'identical'
                    with patch.object(rocket, 'assemble', side_effect=rocket.baseline_assemble), \
                            patch.object(rocket, 'decide', side_effect=rocket.baseline_decide), \
                            patch.object(ask, 'local', wraps=local) as call:
                        run.main()
                    self.assertEqual(call.call_count, 1)
                    shared = root / 'runs/r4/identical-0000000'
                    self.assertEqual(json.loads((shared / 'summary.json').read_text())['shared_reader_results'], 1)
                    self.assertEqual(run.rows(shared / 'predictions.jsonl'),
                                     run.rows(shared / 'baseline-r1/predictions.jsonl'))
                out = root / 'runs/r4/synthetic-0000000'
                meta = json.loads((out / 'meta.json').read_text())
                self.assertEqual(meta['questions'], 1)
                self.assertTrue(meta['complete'])
                for folder in [out, out / 'baseline-r1']:
                    for name in ['meta.json', 'candidates.jsonl', 'evidence.jsonl', 'predictions.jsonl', 'details.jsonl']:
                        self.assertTrue((folder / name).exists(), name)
                    detail = json.loads((folder / 'details.jsonl').read_text())
                    self.assertEqual(detail['answer'], 'correct')
                    self.assertEqual(detail['evidence_f1'], 1)
        finally:
            server.shutdown()
            server.server_close()
            worker.join()


if __name__ == '__main__':
    unittest.main()
