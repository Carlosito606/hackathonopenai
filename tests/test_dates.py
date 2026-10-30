"""Unit tests for dates.py: python tests/test_dates.py"""
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dates import TEMPORAL, annotate_dates, day_no, parse_date  # noqa: E402

WED = datetime(2023, 3, 22)  # a Wednesday
SAT = datetime(2023, 3, 25)
SUN = datetime(2023, 3, 26)


def tag(text, sd=WED):
    return annotate_dates(text, sd)


def check(text, expected, sd=WED):
    got = tag(text, sd)
    assert got == expected, f"\n  text: {text!r}\n  want: {expected!r}\n  got:  {got!r}"


def test_explicit():
    check("on 2023-06-10.", "on 2023-06-10 [2023-06-10, day 161].")
    check("June 3rd and 23 April 2023", "June 3rd [2023-06-03, day 154] and 23 April 2023 [2023-04-23, day 113]")
    check("on January 15th", "on January 15th [2023-01-15, day 15]")
    check("the 10th of June", "the 10th of June [2023-06-10, day 161]")
    check("on 2023/06/10", "on 2023/06/10 [2023-06-10, day 161]")
    assert day_no(parse_date("2023/01/01 (Sun) 10:00")) == 1


def test_ranges():
    check("from May 3-5", "from May 3-5 [2023-05-03, day 123 to 2023-05-05, day 125]")
    check("from the 20th to the 27th of April",
          "from the 20th to the 27th of April [2023-04-20, day 110 to 2023-04-27, day 117]")
    check("June 15th to 17th", "June 15th to 17th [2023-06-15, day 166 to 2023-06-17, day 168]")


def test_year_across_new_year():
    jan = datetime(2023, 1, 5)
    check("I went skiing on December 28th.", "I went skiing on December 28th [2022-12-28, day -3].", jan)
    check("The vote closed on Feb. 22.", "The vote closed on Feb. 22 [2023-02-22, day 53].", datetime(2023, 10, 15))
    check("My trip is on January 10.", "My trip is on January 10 [2024-01-10, day 375].", datetime(2023, 12, 20))
    check("The conference is from June 15th to 17th.",
          "The conference is from June 15th to 17th [2023-06-15, day 166 to 2023-06-17, day 168].",
          datetime(2023, 7, 17))


def test_numeric_and_ordinals():
    check("an issue on 3/22, fixed", "an issue on 3/22 [2023-03-22, day 81], fixed")
    check("a 1/25 scale model", "a 1/25 scale model")
    check("the 50/30/20 rule", "the 50/30/20 rule")
    check("the gala on the 5th of last month", "the gala on the 5th of last month [2023-02-05, day 36]")
    check("In March, I flew on the 10th and returned on the 12th.",
          "In March, I flew on the 10th [2023-03-10, day 69] and returned on the 12th [2023-03-12, day 71].")
    check("in the 36th minute", "in the 36th minute")
    check("the festival I attended on the 15th", "the festival I attended on the 15th")


def test_relative_days():
    check("yesterday", "yesterday [2023-03-21, day 80]")
    check("last night", "last night [2023-03-21, day 80]")
    check("the day before yesterday", "the day before yesterday [2023-03-20, day 79]")
    check("3 days ago", "3 days ago [2023-03-19, day 78]")
    check("a couple of days ago", "a couple of days ago [about 2023-03-20, day 79]")
    check("two weeks ago", "two weeks ago [2023-03-08, day 67]")
    check("a few weeks ago", "a few weeks ago [about 2023-03-01, day 60]")
    check("a month ago", "a month ago [about 2023-02-22, day 53]")
    check("last week", "last week [about 2023-03-15, day 74]")
    check("last month", "last month [about 2023-02-22, day 53]")
    check("next month", "next month [about 2023-04-22, day 112]")
    check("for the next week", "for the next week")


def test_weekends():
    check("last weekend", "last weekend [2023-03-18, day 77]")  # Wed -> the Saturday before
    check("last weekend", "last weekend [2023-03-18, day 77]", SAT)
    check("last weekend", "last weekend [2023-03-18, day 77]", SUN)
    check("this past weekend", "this past weekend [2023-03-25, day 84]", SUN)
    check("two weekends ago", "two weekends ago [2023-03-11, day 70]")
    check("this weekend", "this weekend [2023-03-25, day 84]")
    check("this weekend", "this weekend [2023-03-25, day 84]", SAT)
    check("next weekend", "next weekend [about 2023-04-01, day 91]")


def test_weekdays():
    check("last Friday", "last Friday [2023-03-17, day 76]")
    check("this past Saturday", "this past Saturday [2023-03-18, day 77]")
    check("I bought sneakers on Monday.", "I bought sneakers on Monday [2023-03-20, day 79].")
    check("I'm planning to inspect the hive on Saturday.",
          "I'm planning to inspect the hive on Saturday [2023-03-25, day 84].")
    check("My son's team has a tournament on Saturday, and I promised a cookout.",
          "My son's team has a tournament on Saturday [2023-03-25, day 84], and I promised a cookout.")
    check("I need to finish a proposal - I spent three hours on it on Thursday.",
          "I need to finish a proposal - I spent three hours on it on Thursday [2023-03-16, day 75].")
    check("I've got a client deadline on Friday.", "I've got a client deadline on Friday [2023-03-24, day 83].")
    check("I'm enjoying the PS5, a gift on 10th January.",
          "I'm enjoying the PS5, a gift on 10th January [2023-01-10, day 10].", datetime(2023, 5, 19))
    check("next Friday", "next Friday [2023-03-24, day 83]")
    check("a draft due Wednesday", "a draft due Wednesday [2023-03-22, day 81]")
    check("on Wednesday last week", "on Wednesday last week [2023-03-15, day 74]")
    check("on Tuesdays and Thursdays", "on Tuesdays and Thursdays")
    check("on Saturday mornings", "on Saturday mornings")
    check("on Monday and Wednesday", "on Monday and Wednesday")
    check("during Black Friday", "during Black Friday")


def test_temporal_questions():
    assert TEMPORAL.search("How many days apart were my son's school play and my daughter's appointment?")
    assert TEMPORAL.search("How many days after I bought my ticket was the closing night?")


if __name__ == "__main__":
    tests = [f for name, f in sorted(globals().items()) if name.startswith("test_")]
    for f in tests:
        f()
    print(f"{len(tests)} tests ok")
