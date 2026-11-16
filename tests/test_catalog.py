import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('catalog',Path(__file__).parents[1]/'tools/catalog.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class CatalogIntegrity(unittest.TestCase):
    def setUp(self):
        self.root=module.ROOT
        self.catalog=module.load_catalog()
    def invalid(self,mutate,exception=ValueError):
        c=copy.deepcopy(self.catalog);mutate(c)
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'catalog').mkdir()
            (root/'catalog/models.json').write_text(json.dumps(c))
            (root/'catalog/schema.json').write_bytes((self.root/'catalog/schema.json').read_bytes())
            with patch.object(module,'ROOT',root),self.assertRaises(exception):module.load_catalog()
    def test_unmapped_publication_cannot_inherit_another_papers_code(self):
        self.invalid(lambda c:c['studies'][4]['editions'][0].update(source=c['studies'][3]['editions'][0]['source']))
    def test_moving_branch_is_not_a_recorded_edition(self):
        from jsonschema import ValidationError
        self.invalid(lambda c:c['studies'][0]['editions'][0]['source'].update(commit='main'),ValidationError)
    def test_related_studies_must_exist(self):
        self.invalid(lambda c:c['studies'][0]['related'].append('missing-study'))
    def test_export_is_complete_and_checksummed(self):
        with tempfile.TemporaryDirectory() as folder:
            dest=Path(folder);module.export(self.catalog,dest)
            manifest=json.loads((dest/'catalog-manifest.json').read_text())
            self.assertEqual(len(self.catalog['studies'])+3,len(manifest['files']))
            for name,checksum in manifest['files'].items():
                self.assertEqual(checksum,hashlib.sha256((dest/name).read_bytes()).hexdigest())
            first={p.relative_to(dest):p.read_bytes() for p in dest.rglob('*') if p.is_file()}
            module.export(self.catalog,dest)
            self.assertEqual(first,{p.relative_to(dest):p.read_bytes() for p in dest.rglob('*') if p.is_file()})
if __name__=='__main__':unittest.main()
