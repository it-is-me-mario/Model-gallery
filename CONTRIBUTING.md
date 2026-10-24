# Contributing to the MARIO gallery

Help readers find the right example and understand what they need to run it.

1. Add or edit a record in `catalog/models.json`. Keep the id stable, use a source commit, and link to the original code and data instructions.
2. Record the MARIO version where known. Describe the setup and data access requirements. Keep a study association marked `candidate` until it is confirmed.
3. Leave execution as `not-run` unless an execution evidence format has been introduced and the model has been checked against its reference results.
4. Install the catalog tooling and regenerate the pages:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python tools/catalog.py build
python tools/catalog.py check
```

`catalog/models.json` is the editable source. The root README and `models/*.md` are generated from it. GitHub Actions checks the schema and generated content on each change. This workflow validates the catalog; it does not execute the scientific models.

Submit the change as a pull request. Include a short explanation of the resource and what was inspected or executed. For model-specific scientific or code questions, use the original source repository.
