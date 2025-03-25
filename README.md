# fyn-runner
A runner, for getting hardware specs and running calculations.

## Testing strategy

Most of the tests in this library will be written by AI, or at least it's requested that LLMs generate the initial boilerplate for the unit tests. Organization should still be maintained within the test files and structures. Further, generated tests should still be checked for coverage and correctness (acting as a code review for tests). See the `/doc/test_prompt.md` document which can be used for prompting the LLM when generating unit tests; this document also contains the specific guidelines regarding `fixtures`, `mocking`, what needs testing, and whether to combine or separate tests.
