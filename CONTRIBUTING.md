# Maintaining the model gallery

`catalog/models.json` owns the research catalogue. `tools/catalog.py` generates
GitHub pages and the Sphinx export used by the MARIO website. Edit the catalogue,
then regenerate; do not edit generated pages independently.

## A study and its editions

Each study identifies one publication, its authors, contribution and modelling
scope. Families group related applications. An edition binds a study to a fixed
code revision, data references, MARIO environment and an explicit reproduction
scope. Archived releases, historical scripts and later examples can coexist.

Use a full commit identifier for every code source. Keep database version,
reference year and publication year distinct. Record a version-specific data DOI
when the source establishes it; do not silently replace a historical dataset with
its latest release. Use `unmapped` when code and data have not been identified.
An unmapped edition must not claim a source repository or dataset.

The current gallery is based on source review. Links to maintainers' execution
reports do not mean the gallery has reproduced the paper. Adding independent
execution evidence requires extending the validation contract with the exact
inputs, environment, command, reference outputs, tolerances and check date.

## Repository responsibilities

- MARIO owns general accounting and modelling operations.
- Database projects such as NXSUT own background construction and data releases.
- Research repositories own study inventories, scenarios and reference results.
- Model-gallery owns discovery, citations, edition metadata and generated pages.

Keep existing repository ownership and publication citations. A study's release
can live in its existing repository; a new paper does not automatically require
a new repository. Extract shared code only after comparing its assumptions and
checking that the intended results are preserved. Porting a model to NXSUT creates
a new edition rather than changing the historical study record.

## Build and export

```bash
python -m pip install -r requirements-dev.txt
python tools/catalog.py build
python -m unittest discover -s tests
python tools/catalog.py check
python tools/catalog.py export-sphinx --output /path/to/MARIO/doc/source/resources/model-gallery
```

Commit the complete export and `catalog-manifest.json` in MARIO. The manifest
records the catalogue, generator and output checksums, so the website builds
without fetching a moving branch. Run MARIO's strict documentation build and
link checks; inspect the gallery and study pages in light/dark themes and at
narrow widths. The export is a publication snapshot, not a second editable source.

The three historical learning-resource URLs under `models/` are retained as
links to their canonical teaching resources. Research study URLs remain stable.

## Open provenance work

- Map the 2026 sufficiency paper to its exact code and data edition.
- Verify the GCAM study workflow against the published supplemental results.
- Match the EU steel source revision to its archived release.
- Keep PV's archived release and documented reconstruction distinguishable.

These tasks do not prevent documenting the papers and available resources, but
must be resolved before claiming complete reproduction.
