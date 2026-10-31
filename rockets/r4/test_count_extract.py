"""Literal extraction checks and opt-in counting through the real R4 stages."""
import copy
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from . import rocket
from .count_extract import cache_fingerprint, cache_key, closed_list_response, computation, requested_window, source_response, validate_response, visible_sources
from . import test_counting


class ExtractionTest(unittest.TestCase):
    def setUp(self):
        fixture = test_counting.CountingTest(); fixture.setUp()
        self.h = fixture.h
        self.q = {'question_id': 'q_synthetic', 'history_id': self.h['history_id'],
                  'question': 'How many different museums did I visit in March 2024?', 'question_date': '2024/03/31'}
        self.cands = [{'session_id': s['session_id'], 'turn': 0, 'role': 'user', 'kind': 'turn',
                       'text': s['turns'][0]['content'], 'score': 1.0, 'notes': {}} for s in self.h['sessions']]
        self.evidence = rocket.compatible_evidence(self.h, self.cands)
        self.sources = visible_sources(self.h, self.cands, self.evidence)
        self.response = {'mode': 'distinct', 'complete': True, 'items': [
            {'source': 0, 'entity': 'Amber Museum', 'quote': 'I visited Amber Museum yesterday.', 'date': 'yesterday'},
            {'source': 1, 'entity': 'Amber Museum', 'quote': 'Amber Museum was wonderful.', 'date': None},
            {'source': 1, 'entity': 'Cedar Museum', 'quote': 'I visited Cedar Museum today.', 'date': 'today'},
        ]}

    def record(self):
        return validate_response(self.q, self.h, self.cands, self.sources, self.response)

    def test_valid_extraction_adds_deduplicated_count_and_correct_labels_through_stages(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {'R4_COUNT_CACHE': tmp}):
            record = self.record()
            Path(tmp, cache_key(self.q, self.h, self.cands) + '.json').write_text(json.dumps(record))
            before = copy.deepcopy([self.q, self.h, self.cands])
            enriched = rocket.enrich(self.q, self.h, self.cands)
            pack = rocket.assemble(self.q, self.h, enriched)
            decision = rocket.decide(self.q, self.h, enriched, pack)
            self.assertIn('Computed: 2 distinct named items', pack['facts'])
            self.assertIn('source [E1],', pack['facts'])
            self.assertIn('source [E2],', pack['facts'])
            self.assertIn('not independent proof', decision['question'])
            self.assertEqual([self.q, self.h, self.cands], before)
            self.assertEqual(rocket.grounded_computation(self.q, enriched, pack['evidence'], self.h)['answer'], '2')

    def test_counting_is_identical_to_r1_without_opt_in_or_a_matching_cache(self):
        with patch.dict(os.environ, {}, clear=True):
            enriched = rocket.enrich(self.q, self.h, self.cands)
            self.assertEqual(rocket.assemble(self.q, self.h, enriched), rocket.baseline_assemble(self.q, self.h, self.cands))

    def test_hallucinated_entity_quote_source_and_date_are_rejected(self):
        changes = [{'entity': 'Imaginary Museum'}, {'entity': 'Ambe'}, {'quote': 'A sentence outside the source.'},
                   {'source': 999}, {'source': True}, {'date': 'today'}]
        for change in changes:
            response = copy.deepcopy(self.response)
            response['items'][0].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_response(self.q, self.h, self.cands, self.sources, response)

    def test_one_missing_quote_cannot_silently_shrink_the_inventory(self):
        from .dates import annotate_dates
        record = self.record()
        evidence = [{**e, 'text': annotate_dates(e['text'], e['date'])} for e in self.evidence]
        self.assertIsNotNone(computation(self.q, self.h, record, evidence))
        self.assertIsNone(computation(self.q, self.h, record, evidence[:1]))

    def test_empty_incomplete_and_unsupported_results_do_not_prove_a_zero(self):
        for value in [{**self.response, 'items': []}, {**self.response, 'complete': False},
                      {**self.response, 'mode': 'unsupported'}]:
            self.assertIsNone(validate_response(self.q, self.h, self.cands, self.sources, value))
        self.assertIsNone(computation(self.q, self.h, {**self.record(), 'items': []}, self.evidence))

    def test_unknown_period_membership_falls_back(self):
        self.response['items'][0]['date'] = None
        self.assertIsNone(self.record())

    def test_weighted_quantities_and_event_occurrences_cannot_use_an_entity_count(self):
        for question in ['How many hours did I spend visiting museums?', 'How many times did I visit museums?',
                         'What is the total cost of my museum trips?']:
            q = {**self.q, 'question': question}
            self.assertIsNone(validate_response(q, self.h, self.cands, self.sources, self.response))

    def test_time_scopes_resolve_against_question_date_or_decline(self):
        self.assertEqual(requested_window('How many books did I read last week?', '2024/03/13'),
                         (True, ['2024-03-04', '2024-03-10']))
        self.assertEqual(requested_window('How many books did I read in December?', '2024/03/13'),
                         (True, ['2023-12-01', '2023-12-31']))
        self.assertEqual(requested_window('How many books in the past month?', '2024/03/31'),
                         (True, ['2024-02-29', '2024-03-31']))
        for question in ['How many books did I read recently?', 'How many books did I read before the move?',
                         'How many books do I currently own?', 'How many books in the past few months?',
                         'How many books in the past two weeks and last month?',
                         'How many books in the past fortnight?', 'How many books in March and April?',
                         'How many books in March 2024 and last week?']:
            self.assertFalse(requested_window(question, '2024/03/13')[0])
        self.assertEqual(requested_window("How many books titled 'Last Week' did I buy?", '2024/03/13'), (True, None))

    def test_cache_identity_covers_history_and_resume_fingerprint_covers_item_changes(self):
        original = cache_key(self.q, self.h, self.cands)
        changed = copy.deepcopy(self.h); changed['sessions'][0]['date'] = '2024/04/04'
        self.assertNotEqual(original, cache_key(self.q, changed, self.cands))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, original + '.json'); path.write_text(json.dumps(self.record()))
            before = cache_fingerprint(tmp)
            path.write_text('{}')
            self.assertNotEqual(before, cache_fingerprint(tmp))

    def test_closed_lists_use_rules_but_mixed_or_conflicting_prose_needs_semantics(self):
        q = {**self.q, 'question': 'How many different museums have I visited?'}
        sources = [{'text': 'I visited exactly these museums: "Amber Museum" and "Cedar Museum".'}]
        response = closed_list_response(q, sources)
        self.assertEqual([i['entity'] for i in response['items']], ['Amber Museum', 'Cedar Museum'])
        self.assertIsNone(closed_list_response(q, sources + [{'text': 'I visited another museum too.'}]))
        self.assertIsNone(closed_list_response({**q, 'question': 'How many museums have I built?'}, sources))

    def test_one_source_response_copies_quote_and_assigns_its_source_in_code(self):
        result, known = source_response(self.q, self.sources[0], 0, {'complete': True, 'items': [
            {'entity': 'Amber Museum', 'same_as': None, 'date': 'yesterday', 'source': 999, 'quote': 'invented'}]}, [])
        self.assertEqual(result[0]['source'], 0)
        self.assertEqual(result[0]['quote'], 'I visited Amber Museum yesterday.')
        self.assertEqual(result[0]['identity'], 0)
        self.assertEqual(known, [{'id': 0, 'labels': ['Amber Museum']}])

    def test_exact_repeats_merge_in_code_and_alias_links_cannot_point_to_nonexistent_entities(self):
        source = {'text': 'I visited Amber Museum yesterday.'}
        known = [{'id': 0, 'labels': ['Amber Museum']}]
        response = {'complete': True, 'items': [{'entity': 'Amber Museum', 'same_as': None, 'date': None}]}
        items, after = source_response(self.q, source, 0, response, known)
        self.assertEqual(len(after), 1)
        self.assertEqual(items[0]['identity'], 0)
        for change in [{'same_as': 5}, {'same_as': True}, {'entity': 'Ambe'}]:
            modified = copy.deepcopy(response);modified['items'][0].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                source_response(self.q, source, 0, modified, known)

    def test_oversize_inventory_falls_back_without_dropping_items(self):
        import prepare
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {'R4_COUNT_CACHE': tmp}):
            Path(tmp, cache_key(self.q, self.h, self.cands) + '.json').write_text(json.dumps(self.record()))
            enriched = rocket.enrich(self.q, self.h, self.cands)
            with patch.object(prepare, 'message_chars', return_value=prepare.MAX_MESSAGE + 1):
                pack = rocket.assemble(self.q, self.h, enriched)
            self.assertEqual(pack, rocket.baseline_assemble(self.q, self.h, self.cands))


if __name__ == '__main__':
    unittest.main()
