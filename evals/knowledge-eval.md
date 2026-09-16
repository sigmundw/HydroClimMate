# v0.6 local knowledge evaluation

The cases in [knowledge-eval.json](knowledge-eval.json) separate three measurements:
triggering, selective reading and answer quality. Rubrics are evaluator-only; do not give
expected features, file lists or answers to the agent being measured. Relevant topics are
possible dependencies, not a mandatory read sequence or an exact-count assertion.

## Offline A/B protocol

- Use fresh independent sessions and the same prompt/model/settings for each condition.
- A receives the current workflow with the knowledge hook removed and no models directory;
  B receives the same workflow plus the local packs. Keep project inputs identical.
- Disable browser/search and shell network access while retaining local reads. The model
  service connection itself is still needed; offline here means no external knowledge retrieval.
- Explicitly point to the workflow when testing reading/answer quality. This primes activation
  and therefore cannot measure spontaneous triggering; use trigger-eval.json separately.
- Record actual file/tool traces, bytes or words read, repeated reads, answer, local citations,
  unresolved gaps and provider token usage where available. Do not infer reads from the answer.
- Score scientific correctness and unsupported claims independently of token count. A higher
  context cost can be justified by a more reliable answer; no saving percentage is assumed.
- Authentication, startup or timeout failure is unmeasured, not a failed scientific answer.
  Confirm successful completion before scoring. Do not force a new model or weaken sandboxing.

Use isolated temporary fixtures, not actual project outputs. Do not run models, submit jobs,
install software or reveal test rubrics. A read of a second feature is valid when it addresses
a necessary dependency. Loading unrelated models or all topics without reason is an error.

## Checks and status

[check_knowledge.py](check_knowledge.py) validates package links/anchors, source references,
route synchronization and fixture shape, then checks two mathematical examples independently.
It does not prove model physics or agent behavior. Run `python3 evals/check_knowledge.py`.

[v0.6 results](v0.6-results.md) records what was actually performed and what remains unmeasured.
Historical v0.5 probes have not been retroactively converted to v0.6 scores.
