"""Synthetic ledger invariants independent of item extraction quality."""
import copy
import unittest

from .counting import count_distinct, entity_key


class CountingTest(unittest.TestCase):
    def setUp(self):
        self.h = {'history_id': 'h_synthetic', 'sessions': [
            {'session_id': 's_a', 'date': '2024/03/04', 'turns': [
                {'role': 'user', 'content': 'I visited Amber Museum yesterday.'},
                {'role': 'assistant', 'content': 'Try Cedar Museum next.'}]},
            {'session_id': 's_b', 'date': '2024/03/11', 'turns': [
                {'role': 'user', 'content': 'Amber Museum was wonderful. I visited Cedar Museum today.'}]},
        ]}

    def item(self, sid, label, date=None, turn=0):
        session = next(s for s in self.h['sessions'] if s['session_id'] == sid)
        text = session['turns'][turn]['content']
        left = text.index(label)
        return {'session_id': sid, 'turn': turn, 'span': [left, left + len(label)],
                'date_span': None if date is None else [text.index(date), text.index(date) + len(date)]}

    def test_duplicate_entities_across_sessions_and_chunks_count_once_with_sources(self):
        amber = self.item('s_a', 'Amber Museum', 'yesterday')
        items = [amber, copy.deepcopy(amber), self.item('s_b', 'Amber Museum'), self.item('s_b', 'Cedar Museum', 'today')]
        before = copy.deepcopy([self.h, items])
        result = count_distinct(self.h, items)
        self.assertEqual(result['count'], 2)
        self.assertEqual([len(i['mentions']) for i in result['items']], [2, 1])
        self.assertEqual(result['sources'], ['s_a', 's_b'])
        self.assertFalse(result['history_coverage_verified'])
        self.assertEqual([self.h, items], before)

    def test_near_names_and_aliases_do_not_merge_without_source_proof(self):
        self.assertNotEqual(entity_key('Museum of Art'), entity_key('Museum of Modern Art'))
        self.assertNotEqual(entity_key('Museum of Modern Art'), entity_key('MoMA'))
        self.assertNotEqual(entity_key('The Garden'), entity_key('Garden'))
        self.assertEqual(entity_key('AMBER  Museum'), entity_key('Amber Museum'))

    def test_period_uses_event_day_not_the_reporting_session(self):
        result = count_distinct(self.h, [self.item('s_a', 'Amber Museum', 'yesterday')], ['2024-03-04', '2024-03-31'])
        self.assertEqual(result['count'], 0)
        self.assertEqual(result['sources'], [])

    def test_same_session_id_in_another_history_resolves_its_own_date(self):
        item = self.item('s_a', 'Amber Museum', 'yesterday')
        self.h['sessions'][0]['date'] = '2024/04/04'
        result = count_distinct(self.h, [item], ['2024-04-01', '2024-04-30'])
        self.assertEqual(result['count'], 1)
        self.assertEqual(result['items'][0]['mentions'][0]['date']['start'], '2024-04-03')

    def test_unknown_and_inferred_dates_leave_a_bounded_count(self):
        result = count_distinct(self.h, [self.item('s_a', 'Amber Museum'), self.item('s_b', 'Cedar Museum', 'today')],
                                ['2024-03-01', '2024-03-31'])
        self.assertIsNone(result['count'])
        self.assertEqual((result['lower_bound'], result['upper_bound']), (1, 2))
        self.h['sessions'][0]['turns'][0]['content'] = 'I visited Amber Museum a month ago.'
        result = count_distinct(self.h, [self.item('s_a', 'Amber Museum', 'a month ago')], ['2024-02-01', '2024-02-29'])
        self.assertIsNone(result['count'])

    def test_known_inside_mention_suffices_despite_undated_duplicate(self):
        items = [self.item('s_a', 'Amber Museum', 'yesterday'), self.item('s_b', 'Amber Museum')]
        result = count_distinct(self.h, items, ['2024-03-01', '2024-03-31'])
        self.assertEqual(result['count'], 1)
        self.assertEqual(result['sources'], ['s_a'])

    def test_partial_range_overlap_is_uncertain_but_contained_weekend_counts(self):
        self.h['sessions'][0]['turns'][0]['content'] = 'I visited Amber Museum last weekend.'
        item = self.item('s_a', 'Amber Museum', 'last weekend')
        self.assertEqual(count_distinct(self.h, [item], ['2024-03-01', '2024-03-04'])['count'], 1)
        self.assertIsNone(count_distinct(self.h, [item], ['2024-03-03', '2024-03-04'])['count'])

    def test_fabricated_source_offsets_and_assistant_items_fail(self):
        item = self.item('s_a', 'Amber Museum', 'yesterday')
        bad = [{**item, 'session_id': 'foreign'}, {**item, 'turn': -1},
               {**item, 'span': [0, 10000]}, {**item, 'date_span': [0, 1]},
               self.item('s_a', 'Cedar Museum', turn=1)]
        for value in bad:
            with self.subTest(value=value), self.assertRaises(ValueError):
                count_distinct(self.h, [value])

    def test_date_on_another_action_or_recollection_cannot_date_the_item(self):
        for text in ['I visited Amber Museum recently and I bought a map today.',
                     'I remembered my old visit to Amber Museum today.',
                     'My cousin visited Amber Museum today.']:
            self.h['sessions'][0]['turns'][0]['content'] = text
            with self.subTest(text=text), self.assertRaises(ValueError):
                count_distinct(self.h, [self.item('s_a', 'Amber Museum', 'today')])

    def test_external_alias_partition_changes_arithmetic_without_certifying_semantics(self):
        self.h['sessions'][0]['turns'][0]['content'] = 'I visited Amber Museum today. I call it AM.'
        items = [self.item('s_a', 'Amber Museum'), self.item('s_a', 'AM')]
        result = count_distinct(self.h, items, identities=[0, 0])
        self.assertEqual(result['count'], 1)
        self.assertFalse(result['item_semantics_verified'])
        for identities in [[0], [0, 2], [0, True]]:
            with self.subTest(identities=identities), self.assertRaises(ValueError):
                count_distinct(self.h, items, identities=identities)


if __name__ == '__main__':
    unittest.main()
