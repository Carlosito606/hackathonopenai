"""Synthetic invariants: calendar boundaries, provenance, ambiguity and non-events."""
import unittest

from .dates import annotate_dates, resolve_dates
from .timeline import calendar_difference, classify, compute, entities_match, events


class DatesTest(unittest.TestCase):
    def single(self, expression, base='2024/03/04 (Mon) 09:00'):
        return resolve_dates(expression, base)[0]

    def test_relative_dates_are_history_local(self):
        self.assertEqual(self.single('yesterday')['start'], '2024-03-03')
        self.assertEqual(self.single('yesterday', '2024-05-01')['start'], '2024-04-30')

    def test_leap_day_and_year_boundary(self):
        self.assertEqual(self.single('a couple of days ago', '2024-03-02')['start'], '2024-02-29')
        self.assertEqual(self.single('two days ago', '2024-01-01')['start'], '2023-12-30')

    def test_weekends_stay_ranges(self):
        item = self.single('two weekends ago')
        self.assertEqual((item['start'], item['end'], item['precision']), ('2024-02-24', '2024-02-25', 'range'))
        self.assertEqual(self.single('last weekend')['start'], '2024-03-02')

    def test_ordinal_infers_previous_month_without_pretending_certainty(self):
        item = self.single('I went on the 15th.')
        self.assertEqual((item['start'], item['precision']), ('2024-02-15', 'inferred'))
        self.assertEqual(self.single('I will go on the 15th.')['start'], '2024-03-15')

    def test_month_shift_clamps_without_claiming_exactness(self):
        item = self.single('a month ago', '2024-03-31')
        self.assertEqual((item['start'], item['precision']), ('2024-02-29', 'inferred'))

    def test_explicit_date_annotated_once(self):
        annotated = annotate_dates('I went on March 4, 2024.', '2024-03-10')
        self.assertEqual(annotated.count('day '), 1)
        self.assertIn('2024-03-04', annotated)

    def test_invalid_dates_are_not_events(self):
        self.assertEqual(resolve_dates('2024-02-30', '2024-03-04'), [])


class ComputationTest(unittest.TestCase):
    def event(self, text, base, sid='s_a', role='user'):
        return events(text, base, sid, 0, role)

    def test_elapsed_days_with_provenance(self):
        pool = self.event('I visited the botanical garden yesterday.', '2024-03-05')
        result = compute('How many days ago did I visit the botanical garden?', '2024-03-11', pool)
        self.assertTrue(result['computed'])
        self.assertEqual(result['answer'], '7 days')
        self.assertEqual(result['sources'], ['s_a'])

    def test_two_event_duration(self):
        pool = self.event('I visited the botanical garden today.', '2024-03-04')
        pool += self.event('I attended the pottery workshop yesterday.', '2024-03-12', 's_b')
        result = compute('How many days passed between the botanical garden and the pottery workshop?', '2024-03-20', pool)
        self.assertEqual(result.get('answer'), '7 days')
        self.assertEqual(result['sources'], ['s_a', 's_b'])

    def test_order(self):
        pool = self.event('I visited the botanical garden today.', '2024-03-04')
        pool += self.event('I attended the pottery workshop today.', '2024-03-11', 's_b')
        result = compute('Which came first, the botanical garden or the pottery workshop?', '2024-03-20', pool)
        self.assertTrue(result['computed'])
        self.assertEqual(result['answer'], 'the botanical garden')

    def test_latest_event_is_selected_in_code(self):
        pool = self.event('I used the bus today.', '2024-03-04')
        pool += self.event('I used the train today.', '2024-03-11', 's_b')
        result = compute("Which did I use most recently, 'bus' or 'train'?", '2024-03-20', pool)
        self.assertEqual(result.get('answer'), 'train')

    def test_conflicting_dates_do_not_choose_arbitrarily(self):
        pool = self.event('I visited the botanical garden today.', '2024-03-04')
        pool += self.event('I visited the botanical garden today.', '2024-03-11', 's_b')
        self.assertFalse(compute('How many days ago did I visit the botanical garden?', '2024-03-20', pool)['computed'])

    def test_approximate_date_not_used_for_exact_duration(self):
        pool = self.event('I visited the botanical garden two weekends ago.', '2024-03-04')
        self.assertFalse(compute('How many days ago did I visit the botanical garden?', '2024-03-20', pool)['computed'])

    def test_plans_negations_and_assistant_not_user_events(self):
        for text, role in [('I will visit the botanical garden today.', 'user'),
                           ("I did not visit the botanical garden today.", 'user'),
                           ('You visited the botanical garden today.', 'assistant')]:
            with self.subTest(text=text):
                pool = self.event(text, '2024-03-04', role=role)
                self.assertFalse(compute('How many days ago did I visit the botanical garden?', '2024-03-20', pool)['computed'])

    def test_multiple_dates_in_sentence_are_not_proximity_matched(self):
        pool = self.event('I visited the garden on 2024-03-04 and the workshop on 2024-03-11.', '2024-03-20')
        self.assertTrue(all(e['ambiguous_clause'] for e in pool))

    def test_near_miss_entity_is_not_silently_accepted(self):
        pool = self.event('I visited the botanical garden today.', '2024-03-04')
        self.assertFalse(compute('How many days ago did I visit the Botanical Museum?', '2024-03-20', pool)['computed'])

    def test_classifies_count_without_inventing_total(self):
        q = 'How many charity events did I participate in before the fundraiser?'
        self.assertEqual(classify(q)['form'], 'count')
        self.assertFalse(compute(q, '2024-03-20', [])['computed'])

    def test_classifies_duration_without_two_grounded_endpoints(self):
        self.assertEqual(classify('How many days did it take me to finish the book?')['form'], 'duration')
        self.assertEqual(classify('How long had I been taking pottery lessons when I bought the kiln?')['form'], 'between')

    def test_order_named_list_preserves_three_anchors(self):
        result = classify('Who graduated first, second and third among Alice, Brenda and Clara?')
        self.assertEqual(result['anchors'], ['Alice', 'Brenda', 'Clara'])

    def test_cancellation_is_an_event_but_not_a_completed_visit(self):
        pool = self.event('I cancelled the botanical garden visit today.', '2024-03-04')
        self.assertFalse(compute('How many days ago did I visit the botanical garden?', '2024-03-11', pool)['computed'])
        result = compute('How many days ago did I cancel the botanical garden visit?', '2024-03-11', pool)
        self.assertTrue(result['computed'])

    def test_other_persons_visit_is_not_my_visit(self):
        pool = self.event('My cousin visited the botanical garden today.', '2024-03-04')
        self.assertFalse(compute('How many days ago did I visit the botanical garden?', '2024-03-11', pool)['computed'])

    def test_before_question_requires_chronological_premise(self):
        pool = self.event('I visited the botanical garden today.', '2024-03-11')
        pool += self.event('I attended the pottery workshop today.', '2024-03-04', 's_b')
        result = compute('How many days before the pottery workshop did I visit the botanical garden?', '2024-03-20', pool)
        self.assertFalse(result['computed'])

    def test_future_event_is_not_a_completed_event(self):
        pool = self.event('Tomorrow I attend the botanical garden workshop.', '2024-03-04')
        result = compute('How many days ago did I attend the botanical garden workshop?', '2024-03-20', pool)
        self.assertFalse(result['computed'])

    def test_generic_museum_does_not_name_a_specific_museum(self):
        self.assertFalse(entities_match('the Museum of Modern Art (MMA)', 'I visited an art museum and saw modern art.'))
        self.assertTrue(entities_match('the Museum of Modern Art (MMA)', 'I visited MMA yesterday.'))
        self.assertTrue(entities_match('the Museum of Modern Art (MMA)', 'I visited the Museum of Modern Art yesterday.'))
        pool = self.event('I visited MMA yesterday.', '2024-03-05')
        result = compute('How many days ago did I visit the Museum of Modern Art (MMA)?', '2024-03-11', pool)
        self.assertEqual(result.get('answer'), '7 days')

    def test_titles_preserve_phrase_not_word_bag(self):
        self.assertTrue(entities_match("'The Seven Husbands of Evelyn Hugo'", 'I finished Seven Husbands of Evelyn Hugo today.'))
        self.assertFalse(entities_match("'Seven Husbands of Evelyn Hugo'", 'Evelyn met seven people. Hugo discussed their husbands.'))

    def test_alphanumeric_event_names_are_not_swapped(self):
        self.assertFalse(entities_match('5K charity run', 'I participated in a 10K charity run today.'))

    def test_a_question_is_not_a_completed_event(self):
        pool = self.event('Did I visit the botanical garden yesterday?', '2024-03-05')
        self.assertFalse(compute('How many days ago did I visit the botanical garden?', '2024-03-11', pool)['computed'])

    def test_order_can_be_proved_from_disjoint_periods(self):
        pool = self.event('I visited the botanical garden last weekend.', '2024-03-04')
        pool += self.event('I attended the pottery workshop last weekend.', '2024-03-18', 's_b')
        result = compute('Which came first, the botanical garden or the pottery workshop?', '2024-03-20', pool)
        self.assertTrue(result['computed'])
        self.assertEqual(result['answer'], 'the botanical garden')
        self.assertIn('2024-03-02..2024-03-03', result['facts'])

    def test_overlapping_periods_do_not_prove_order(self):
        pool = self.event('I visited the botanical garden last weekend.', '2024-03-04')
        pool += self.event('I attended the pottery workshop today.', '2024-03-03', 's_b')
        result = compute('Which came first, the botanical garden or the pottery workshop?', '2024-03-20', pool)
        self.assertFalse(result['computed'])

    def test_mixed_period_and_day_in_sentence_are_ambiguous(self):
        pool = self.event('I visited the garden last weekend and the workshop today.', '2024-03-04')
        self.assertTrue(all(e['ambiguous_clause'] for e in pool))

    def test_calendar_months_and_years_clamp_anniversaries(self):
        self.assertEqual(calendar_difference('2023-01-31', '2023-02-28', 'month'), '1 complete calendar month (28 days)')
        self.assertEqual(calendar_difference('2024-02-29', '2025-02-28', 'year'), '1 complete calendar year (365 days)')
        self.assertEqual(calendar_difference('2023-01-31', '2023-02-27', 'month'), '0 complete calendar months (27 days)')

    def test_single_day_and_week_are_grammatical(self):
        self.assertEqual(calendar_difference('2024-03-04', '2024-03-05', 'day'), '1 day')
        self.assertEqual(calendar_difference('2024-03-04', '2024-03-11', 'week'), '1 week (7 days)')

    def test_recollection_date_does_not_date_the_recalled_visit(self):
        pool = self.event('I was thinking about my botanical garden tour today, and I remembered that I went with a friend.',
                          '2024-03-04')
        result = compute('How many days ago did I visit the botanical garden with a friend?', '2024-03-11', pool)
        self.assertFalse(result['computed'])

    def test_date_scopes_only_to_its_coordinated_predicate(self):
        pool = self.event('I recently discovered a jazz quartet and started enjoying their music today.', '2024-03-04')
        self.assertFalse(compute('How many days ago did I discover a jazz quartet?', '2024-03-11', pool)['computed'])
        self.assertEqual(pool[0]['text'], 'started enjoying their music today.')

    def test_dated_visit_before_separate_recollection_remains_valid(self):
        pool = self.event('I visited the botanical garden today and remembered my old music teacher.', '2024-03-04')
        result = compute('How many days ago did I visit the botanical garden?', '2024-03-11', pool)
        self.assertEqual(result.get('answer'), '7 days')

    def test_recollection_itself_can_be_a_dated_event(self):
        pool = self.event('I remembered my botanical garden trip today.', '2024-03-04')
        result = compute('How many days ago did I remember my botanical garden trip?', '2024-03-11', pool)
        self.assertEqual(result.get('answer'), '7 days')

    def test_discussion_today_does_not_date_a_trip(self):
        pool = self.event('I discussed my botanical garden trip today.', '2024-03-04')
        self.assertFalse(compute('How many days ago did I visit the botanical garden?', '2024-03-11', pool)['computed'])

    def test_deciding_to_buy_does_not_establish_a_purchase(self):
        pool = self.event('I decided to buy a telescope today.', '2024-03-04')
        self.assertFalse(compute('How many days ago did I buy a telescope?', '2024-03-11', pool)['computed'])

    def test_decision_itself_remains_a_supported_event(self):
        pool = self.event('I decided to buy a telescope today.', '2024-03-04')
        result = compute('How many days ago did I decide to buy a telescope?', '2024-03-11', pool)
        self.assertEqual(result.get('answer'), '7 days')

    def test_past_intention_is_not_a_completed_event(self):
        for expression in ['hoped to', 'wanted to', 'planned to', 'intended to']:
            pool = self.event(f'I {expression} visit the botanical garden today.', '2024-03-04')
            self.assertFalse(compute('How many days ago did I visit the botanical garden?', '2024-03-11', pool)['computed'])


if __name__ == '__main__':
    unittest.main()
