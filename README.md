# Image name parser

Test code: `tox`

## Usage

```python
from image import ImageReference

ref = ImageReference.rough_parse("quay.io/nitrate/web:4.13")
print("registry:", ref.registry)
print("namespace:", ref.namespace)
print("repository:", ref.repository)
print("tag:", ref.tag)
print("digest:", ref.digest)
```

that outputs:

```bash
registry: quay.io
namespace: nitrate
repository: web
tag: 4.13
digest:
```

## Contribution

Contribute idea and issues via issues.

Open a pull request to add test cases.
