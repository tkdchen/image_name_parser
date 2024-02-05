import os.path
import re
from typing import Final

import pytest

__author__ = "tkdchen"
__version__ = "0.0.0"

# Regular expression matches registered algorithm in OCI image spec
REGEX_DIGEST: Final = r"^(sha256:[0-9a-f]{64}|sha512:[0-9a-f]{128})$"


class ImageReference:

    def __init__(
        self,
        repository: str,
        registry: str = "",
        namespace: str = "",
        tag: str = "",
        digest: str = "",
    ):
        self.repository = repository
        self.registry = registry
        self.namespace = namespace
        self.tag = tag
        self.digest = digest

    @property
    def digest(self) -> str:
        return self._digest

    @digest.setter
    def digest(self, value: str) -> None:
        if value == "":
            self._digest = value
            return
        if not re.match(REGEX_DIGEST, value):
            raise ValueError(f"Value {value} is not a valid sha256 or sha512 digest.")
        self._digest = value

    def __str__(self) -> str:
        parts = [os.path.join(self.registry, self.namespace, self.repository)]
        if self.tag:
            parts.append(":" + self.tag)
        if self.digest:
            parts.append("@" + self.digest)
        return "".join(parts)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} ({id(self)}): {str(self)}>"

    def __eq__(self, that: object) -> bool:
        if not isinstance(that, ImageReference):
            raise TypeError("Passed object is not an instance of ImageReference.")
        return (
            self.registry == that.registry
            and self.namespace == that.namespace
            and self.repository == that.repository
            and self.tag == that.tag
            and self.digest == that.digest
        )

    def as_dict(self) -> dict[str, str]:
        return {
            "registry": self.registry,
            "namespace": self.namespace,
            "repository": self.repository,
            "tag": self.tag,
            "digest": self.digest,
        }

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

        match = re.match(r"^[0-9a-zA-Z]+(\.[0-9a-zA-Z_-]+)+(:\d+)?$", leftmost)
        if match is not None or leftmost == "localhost":
            registry = leftmost  # looks like a registry, treat it as it is
            name_components.pop(0)

        elif match := re.match(r"([^.]+):([0-9a-zA-Z_.-]+)", leftmost):
            # match: ubuntu:latest. Then, the list must be empty
            repository, tag = match.groups()
            name_components.pop(0)

        if len(name_components) > 0:
            if len(name_components) == 1:
                repository = name_components[0]
            else:
                namespace = name_components.pop(0)
                repository = "/".join(name_components)

        return cls(
            registry=registry, repository=repository, namespace=namespace, tag=tag, digest=digest
        )


FAKE_DIGEST: Final = "sha256:b330d9e6aa681d5fe2b11fcfe0ca51e1801d837dd26804b0ead9a09ca8246c40"


@pytest.mark.parametrize(
    "pullspec,expected",
    [
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
        [f"reg.io/org/ubi@{FAKE_DIGEST}", ("reg.io", "org", "ubi", "", FAKE_DIGEST)],
        [f"reg.io/org/ubi:9.3@{FAKE_DIGEST}", ("reg.io", "org", "ubi", "9.3", FAKE_DIGEST)],
    ],
)
def test_image_reference(pullspec, expected):
    ref = ImageReference.rough_parse(pullspec)
    assert expected == (ref.registry, ref.namespace, ref.repository, ref.tag, ref.digest)


@pytest.mark.parametrize(
    "attrs,expected",
    [
        [{"repository": ""}, ""],
        [{"repository": "ubuntu"}, "ubuntu"],
        [{"repository": "ubuntu", "namespace": "library"}, "library/ubuntu"],
        [
            {"repository": "ubuntu", "namespace": "library", "registry": "docker.io"},
            "docker.io/library/ubuntu",
        ],
        [{"repository": "ubuntu", "tag": "22.04"}, "ubuntu:22.04"],
        [{"repository": "ubuntu", "tag": "latest"}, "ubuntu:latest"],
        [{"repository": "ubuntu", "namespace": "library"}, "library/ubuntu"],
        [
            {
                "repository": "ubuntu",
                "namespace": "library",
                "registry": "docker.io",
                "tag": "22.04",
            },
            "docker.io/library/ubuntu:22.04",
        ],
        [
            {"repository": "ubuntu", "tag": "22.04", "digest": FAKE_DIGEST},
            f"ubuntu:22.04@{FAKE_DIGEST}",
        ],
        [{"repository": "ubuntu", "digest": FAKE_DIGEST}, f"ubuntu@{FAKE_DIGEST}"],
        [
            {"repository": "ubuntu", "registry": "reg.io", "digest": FAKE_DIGEST},
            f"reg.io/ubuntu@{FAKE_DIGEST}",
        ],
    ],
)
def test___str__(attrs, expected):
    assert expected == str(ImageReference(**attrs))


@pytest.mark.parametrize(
    "image_url,attrs",
    [
        [
            "ubuntu",
            {
                "registry": "",
                "namespace": "",
                "repository": "ubuntu",
                "tag": "",
                "digest": "",
            },
        ],
        [
            f"reg.io/app@{FAKE_DIGEST}",
            {
                "registry": "reg.io",
                "namespace": "",
                "repository": "app",
                "tag": "",
                "digest": FAKE_DIGEST,
            },
        ],
        [
            f"reg.io/org/room/app:9.3@{FAKE_DIGEST}",
            {
                "registry": "reg.io",
                "namespace": "org",
                "repository": "room/app",
                "tag": "9.3",
                "digest": FAKE_DIGEST,
            },
        ],
    ],
)
def test___eq__(image_url: str, attrs: dict[str, str]):
    left = ImageReference.rough_parse(image_url)
    right = ImageReference(**attrs)
    assert left == right


@pytest.mark.parametrize(
    "image_url,attrs",
    [
        [
            "ubuntu",
            {
                "registry": "docker.io",
                "namespace": "library",
                "repository": "ubuntu",
                "tag": "",
                "digest": "",
            },
        ],
        [
            f"reg.io/app@{FAKE_DIGEST}",
            {
                "registry": "reg.io",
                "namespace": "",
                "repository": "app",
                "tag": "",
                "digest": FAKE_DIGEST.replace("0", "1"),
            },
        ],
        [
            f"reg.io/org/room/app:9.3@{FAKE_DIGEST}",
            {
                "registry": "reg.io",
                "namespace": "org",
                "repository": "app",
                "tag": "9.3",
                "digest": FAKE_DIGEST,
            },
        ],
    ],
)
def test_not__eq__(image_url: str, attrs: dict[str, str]):
    left = ImageReference.rough_parse(image_url)
    right = ImageReference(**attrs)
    assert left != right


def test___eq__wrong_type():
    with pytest.raises(TypeError, match=""):
        ImageReference.rough_parse("app:9.3").__eq__("app:9.3")


def test___repr__():
    assert "reg.io/app:9.3" in repr(ImageReference.rough_parse("reg.io/app:9.3"))


@pytest.mark.parametrize(
    "attrs,expected",
    [
        [{"repository": ""}, ("", "", "", "", "")],
        [{"repository": "app"}, ("", "", "app", "", "")],
        [{"repository": "app", "registry": "reg.io"}, ("reg.io", "", "app", "", "")],
        [
            {"repository": "app", "registry": "reg.io", "tag": "9.3"},
            ("reg.io", "", "app", "9.3", ""),
        ],
        [
            {"repository": "org/user/app", "registry": "reg.io", "tag": "9.3"},
            ("reg.io", "", "org/user/app", "9.3", ""),
        ],
        [{"repository": "app", "digest": "sha:123"}, "is not a valid"],
    ],
)
def test_direct_initialization(attrs: dict[str, str], expected):
    if isinstance(expected, str):
        with pytest.raises(ValueError, match=expected):
            ImageReference(**attrs)
    else:
        ref = ImageReference(**attrs)
        assert expected == (ref.registry, ref.namespace, ref.repository, ref.tag, ref.digest)


@pytest.mark.parametrize(
    "image_ref,expected",
    [
        [
            ImageReference("app"),
            {"registry": "", "namespace": "", "repository": "app", "tag": "", "digest": ""},
        ],
        [
            ImageReference("app", registry="reg.io"),
            {"registry": "reg.io", "namespace": "", "repository": "app", "tag": "", "digest": ""},
        ],
        [
            ImageReference("app", registry="reg.io", namespace="org"),
            {
                "registry": "reg.io",
                "namespace": "org",
                "repository": "app",
                "tag": "",
                "digest": "",
            },
        ],
        [
            ImageReference("app", registry="reg.io", namespace="org", tag="9.3"),
            {
                "registry": "reg.io",
                "namespace": "org",
                "repository": "app",
                "tag": "9.3",
                "digest": "",
            },
        ],
        [
            ImageReference(
                "app", registry="reg.io", namespace="org", tag="9.3", digest=FAKE_DIGEST
            ),
            {
                "registry": "reg.io",
                "namespace": "org",
                "repository": "app",
                "tag": "9.3",
                "digest": FAKE_DIGEST,
            },
        ],
    ],
)
def test_as_dict(image_ref: ImageReference, expected: dict[str, str]):
    assert expected == image_ref.as_dict()
