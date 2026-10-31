# Independent audit of R1's test evidence (two GPT-6 Astra agents, read-only)

What: two independent reviewers (openai/gpt-6-astra, high) read R1's plan for all 146 test questions (plan built at
fd7587f, 18k-char evidence) and searched the full histories for every fact each question needs. No gold exists
for test; the audit says whether the needed turns reach Reactor, not whether answers are right. Nothing from it
is encoded in code or prompts; only the generic patterns below were acted on.

Per question class (146): OK 13, MISSING 14 (a needed turn not in the evidence), TRAP 109 (the evidence also holds
a misleading near miss), UNANSWERABLE? 10 (reviewer found no answer in the history), DATE 0 (no date the
tagger missed).

Generic patterns and what R1 did about them:
| pattern | questions | change |
|---|---|---|
| near miss about another person (family, friend, neighbour, colleague) or their pet | most TRAPs | GUIDE: facts about other people do not answer a question about me; abstain if only said about someone else (323eb44) |
| plan / recommendation / attempt / undone change taken as the current state | many TRAPs | GUIDE: these are not my current state (323eb44) |
| the user's answer or correction cut off after an assistant question | 4+ MISSING | evidence brings the start of the next user turn (323eb44) |
| fact said in passing inside an off-topic session | ~5 MISSING | date windows and session diversity in retrieval (retrieval/recall-audit, merged 088d1a0) |
| incomplete enumeration for counting / totals over months | ~5 MISSING, 9 TRAP | same, plus a larger evidence budget for counting questions (see 20261031-0030-budget.md) |
