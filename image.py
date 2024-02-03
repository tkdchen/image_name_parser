import os.path
import re
import pytest


class ImageReference:

    def __init__(self, repository: str, registry: str = "", namespace: str = "", tag: str = "", digest: str = ""):
        self.repository = repository
        self.registry = registry
        self.namespace = namespace
        self.tag = tag
        self.digest = digest

    def __str__(self) -> str:
        parts = [os.path.join(self.registry, self.namespace, self.repository)]
        if self.tag:
            parts.append(":" + self.tag)
        if self.digest:
            parts.append(f"@{self.digest}")
        return "".join(parts)

    @classmethod
    def rough_parse(cls, s: str) -> "ImageReference":
        buf = []
        colon_pos = 0  # only used for detecting tag
        slash_count = 0
        i = len(s)
        name_components: list[str] = []
        registry = ""
        namespace = ""
        repository = ""
        tag = ""
        digest = ""

        while True:
            i -= 1
            if i < 0:  # Scan ends
                break
            c = s[i]
            if c == ":":
                colon_pos = i
                buf.append(c)
            elif c == "@":
                # digest appears
                digest = "".join(reversed(buf))
                # reset
                buf = []
                colon_pos = -1  # digest includes :
            elif c == "/":
                slash_count += 1
                if slash_count == 1 and colon_pos > 0:
                    # tag appears
                    tag_buf = []
                    while True:
                        c = buf.pop(0)
                        if c == ":":
                            break
                        tag_buf.append(c)
                    tag = "".join(reversed(tag_buf))
                name_components.append("".join(reversed(buf)))
                # reset
                buf = []
            else:
                buf.append(c)

        name_components.append("".join(reversed(buf)))
        name_components.reverse()

        leftmost = name_components[0]

        if re.match(r"^[0-9a-zA-Z]+(\.[0-9a-zA-Z_-]+)+(:\d+)?$", leftmost) or leftmost == "localhost":
            registry = leftmost  # looks like a registry, treat it as it is
            name_components.pop(0)

        elif match := re.match(r"([^.]+):([0-9a-zA-Z_.-]+)", leftmost):
            # match: ubuntu:latest. Then, the list must be empty
            repository, tag = match.groups()
            name_components.pop(0)

        if len(name_components) > 0:
            if len(name_components) == 1:
                repository= name_components[0]
            else:
                namespace = name_components.pop(0)
                repository = "/".join(name_components)        

        return cls(
            registry=registry, repository=repository, namespace=namespace, tag=tag, digest=digest
        )


@pytest.mark.parametrize("pullspec,expected", [
    # Test pullspec, expected (registry, namespace, repository, tag, digest)

    # simple cases
    ["ubuntu", ("", "", "ubuntu", "", "")],
    ["ubuntu:22.04", ("", "", "ubuntu", "22.04", "")],
    ["ubuntu:latest", ("", "", "ubuntu", "latest", "")],
    ["localhost/ubuntu", ("localhost", "", "ubuntu", "", "")],
    ["library/ubuntu", ("", "library", "ubuntu", "", "")],
    ["app:3000", ("", "", "app", "3000", "")],
    ["reg.io:3000", ("reg.io:3000", "", "", "", "")],
    ["reg.io/ubi:9.3", ("reg.io", "", "ubi", "9.3", "")],
    ["reg.io:3000/ubi:9.3", ("reg.io:3000", "", "ubi", "9.3", "")],

    ["sha256:1234afe3", ("", "", "sha256", "1234afe3", "")],
    ["org/sha256:1234afe3", ("", "org", "sha256", "1234afe3", "")],
    ["org/app/sha256:1234afe3", ("", "org", "app/sha256", "1234afe3", "")],

    # multiple path components in the name
    ["reg.io/org/ubi:9.3", ("reg.io", "org", "ubi", "9.3", "")],
    ["reg.io/org/tenant/ubi:9.3", ("reg.io", "org", "tenant/ubi", "9.3", "")],
    ["reg.io:3000/org/tenant/ubi:9.3", ("reg.io:3000", "org", "tenant/ubi", "9.3", "")],

    # with digest
    ["reg.io/org/ubi@sha256:123", ("reg.io", "org", "ubi", "", "sha256:123")],
    ["reg.io/org/ubi:9.3@sha256:123", ("reg.io", "org", "ubi", "9.3", "sha256:123")],
])
def test_image_reference(pullspec, expected):
    ref = ImageReference.rough_parse(pullspec)
    assert expected == (ref.registry, ref.namespace, ref.repository, ref.tag, ref.digest)
