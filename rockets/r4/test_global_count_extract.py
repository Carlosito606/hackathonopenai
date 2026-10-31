"""Global source binding and exact-repeat arithmetic, with synthetic records."""
import copy
import json
import unittest
from unittest.mock import Mock

from .global_count_extract import extract, response_format, validate
from . import test_count_extract
from .count_extract import computation


class GlobalExtractionTest(unittest.TestCase):
    def setUp(self):
        f = test_count_extract.ExtractionTest(); f.setUp()
        self.q, self.h, self.cands, self.sources = f.q, f.h, f.cands, f.sources
        self.response = {'s' + str(i): [] for i in range(len(self.sources))}
        self.response.update(complete=True, s0=[{'entity': 'Amber Museum', 'identity': 17, 'date': 'yesterday'}],
                             s1=[{'entity': 'Amber Museum', 'identity': 48, 'date': None},
                                 {'entity': 'Cedar Museum', 'identity': 9, 'date': 'today'}])

    def test_repeated_names_merge_even_when_the_model_splits_their_group_ids(self):
        record = validate(self.q, self.h, self.cands, self.sources, self.response)
        self.assertEqual(record['identities'], [0, 0, 1])
        self.assertFalse(record['pipeline_cache_compatible'])
        from . import rocket
        from .dates import annotate_dates
        evidence = rocket.compatible_evidence(self.h, self.cands)
        evidence = [{**e, 'text': annotate_dates(e['text'], e['date'])} for e in evidence]
        self.assertEqual(computation(self.q, self.h, record, evidence)['answer'], '2')

    def test_missing_sources_and_borrowed_names_cannot_create_a_partial_count(self):
        missing = copy.deepcopy(self.response); del missing['s1']
        borrowed = copy.deepcopy(self.response); borrowed['s0'][0]['entity'] = 'Cedar Museum'
        for response in [missing, borrowed]:
            with self.subTest(response=response), self.assertRaises(ValueError):
                validate(self.q, self.h, self.cands, self.sources, response)

    def test_uncertainty_and_empty_inventories_do_not_establish_a_total(self):
        self.assertIsNone(validate(self.q, self.h, self.cands, self.sources, {'complete': False}))
        empty = {'s' + str(i): [] for i in range(len(self.sources))};empty['complete'] = True
        self.assertIsNone(validate(self.q, self.h, self.cands, self.sources, empty))

    def test_schema_choices_belong_to_each_source_and_complete_follows_the_ledger(self):
        schema = response_format(self.sources)['schema']
        self.assertEqual(list(schema['properties'])[-1], 'complete')
        self.assertEqual(set(schema['properties']), set(schema['required']))
        names = schema['properties']['s0']['items']['properties']['entity']['enum']
        self.assertIn('Amber Museum', names)
        self.assertNotIn('Cedar Museum', names)

    def test_boolean_or_missing_alias_group_is_rejected(self):
        for group in [True, None, -1, 128]:
            response = copy.deepcopy(self.response);response['s0'][0]['identity'] = group
            with self.subTest(group=group), self.assertRaises(ValueError):
                validate(self.q, self.h, self.cands, self.sources, response)

    def test_one_global_call_no_semantic_retries_and_no_call_when_oversize(self):
        call = Mock(return_value=json.dumps(self.response))
        record, outcome = extract(self.q, self.h, self.cands, self.sources, call)
        self.assertIsNotNone(record)
        self.assertEqual((call.call_count, outcome['calls']), (1, 1))
        call = Mock(return_value='{"complete":false}')
        self.assertEqual(extract(self.q, self.h, self.cands, self.sources, call)[1]['status'], 'unresolved')
        self.assertEqual(call.call_count, 1)
        call.reset_mock()
        self.assertEqual(extract(self.q, self.h, self.cands, self.sources, call, max_chars=1)[1]['calls'], 0)
        call.assert_not_called()

    def test_occurrence_counts_do_not_spend_a_model_call_on_distinct_items(self):
        q = {**self.q, 'question': 'How many times did I visit museums?'}
        call = Mock()
        self.assertEqual(extract(q, self.h, self.cands, self.sources, call)[1]['status'], 'unsupported')
        call.assert_not_called()


if __name__ == '__main__':
    unittest.main()
