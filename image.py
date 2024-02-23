import copy
import os.path
import re
from typing import Final, Union

import pytest

__author__ = "tkdchen"
__version__ = "0.0.0"

# Matches registered algorithm in OCI image spec
REGEX_DIGEST: Final = r"^(sha256:[0-9a-f]{64}|sha512:[0-9a-f]{128})$"
# Matches a string that looks like a registry host with optional port
REGEX_REGISTRY: Final = r"^[0-9a-zA-Z]+(\.[0-9a-zA-Z_-]+)+(:\d+)?$"


def looks_like_a_registry(s: str) -> bool:
    return s == "localhost" or re.match(REGEX_REGISTRY, s) is not None


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

    def __copy__(self) -> "ImageReference":
        return ImageReference(
            registry=self.registry,
            namespace=self.namespace,
            repository=self.repository,
            tag=self.tag,
            digest=self.digest,
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
    def parse(cls, s: str) -> "ImageReference":
        buf: list[str] = []
        colon_pos = -1
        slash_count = 0
        name_components: list[str] = []
        reg = ns = repo = tag = digest = ""
        i = len(s)

        while True:
            i -= 1

            if i < 0:  # Scan ends
                if not buf:
                    raise ValueError("Missing image name component.")

                name_components.append("".join(reversed(buf)))
                name_components.reverse()

                if slash_count == 0:
                    if colon_pos < 0:
                        repo = name_components[0]
                    elif colon_pos > 0:
                        part = name_components[0]
                        repo = part[:colon_pos]
                        tag_start_pos = colon_pos + 1
                        tag = part[tag_start_pos:]
                    else:
                        raise ValueError("Missing image name component.")
                else:
                    part = name_components[0]
                    if looks_like_a_registry(part):
                        reg = part
                        name_components.pop(0)
                        slash_count -= 1
                    if slash_count > 0:
                        ns = name_components.pop(0)
                    repo = "/".join(name_components)

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
                if not buf:
                    raise ValueError("Missing image name component.")
                name_components.append("".join(reversed(buf)))
                # reset
                buf = []

            else:
                buf.append(c)

        return cls(registry=reg, repository=repo, namespace=ns, tag=tag, digest=digest)


ImageRefTuple = tuple[str, str, str, str]
FAKE_DIGEST: Final = "sha256:b330d9e6aa681d5fe2b11fcfe0ca51e1801d837dd26804b0ead9a09ca8246c40"


@pytest.mark.parametrize(
    "image_name,expected",
    [
        # Test image name, expected (registry, namespace, repository, tag, digest)
        # simple cases
        ["ubuntu", ("", "", "ubuntu", "", "")],
        ["ubuntu:22.04", ("", "", "ubuntu", "22.04", "")],
        ["ubuntu:latest", ("", "", "ubuntu", "latest", "")],
        ["localhost/ubuntu", ("localhost", "", "ubuntu", "", "")],
        ["library/ubuntu", ("", "library", "ubuntu", "", "")],
        ["app:3000", ("", "", "app", "3000", "")],
        ["reg.io:3000", ("", "", "reg.io", "3000", "")],
        ["reg.io/ubi:9.3", ("reg.io", "", "ubi", "9.3", "")],
        ["reg.comp.io/ubi:9.3", ("reg.comp.io", "", "ubi", "9.3", "")],
        ["reg.io:3000/ubi:9.3", ("reg.io:3000", "", "ubi", "9.3", "")],
        ["sha256:1234afe3", ("", "", "sha256", "1234afe3", "")],
        ["org/sha256:1234afe3", ("", "org", "sha256", "1234afe3", "")],
        ["org/app/sha256:1234afe3", ("", "org", "app/sha256", "1234afe3", "")],
        # multiple path components in the name
        ["reg.io/org/ubi:9.3", ("reg.io", "org", "ubi", "9.3", "")],
        ["reg.io/org/tenant/ubi:9.3", ("reg.io", "org", "tenant/ubi", "9.3", "")],
        [
            "reg.comp.io:3000/org/tenant/ubi:9.3",
            ("reg.comp.io:3000", "org", "tenant/ubi", "9.3", ""),
        ],
        # with digest
        [f"reg.io/org/ubi@{FAKE_DIGEST}", ("reg.io", "org", "ubi", "", FAKE_DIGEST)],
        [f"reg.io/org/ubi:9.3@{FAKE_DIGEST}", ("reg.io", "org", "ubi", "9.3", FAKE_DIGEST)],
    ],
)
def test_parse_image_reference(image_name: str, expected: ImageRefTuple):
    ref = ImageReference.parse(image_name)
    assert expected == (ref.registry, ref.namespace, ref.repository, ref.tag, ref.digest)


@pytest.mark.parametrize(
    "image_name",
    [
        "app/:9.3",
        "reg.io/app/:9.3",
        "reg.io/app/:9.3@" + FAKE_DIGEST,
        "reg.io/org/app/:9.3",
        "reg.io/org//app:9.3",
        "/reg.io/org/app:9.3",
        ":9.3",
    ],
)
def test_missing_image_name_components(image_name: str) -> None:
    with pytest.raises(ValueError, match="Missing image name component"):
        ImageReference.parse(image_name)


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
def test___str__(attrs: dict[str, str], expected: str) -> None:
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
def test___eq__(image_url: str, attrs: dict[str, str]) -> None:
    left = ImageReference.parse(image_url)
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
def test_not__eq__(image_url: str, attrs: dict[str, str]) -> None:
    left = ImageReference.parse(image_url)
    right = ImageReference(**attrs)
    assert left != right


def test___eq__wrong_type() -> None:
    with pytest.raises(TypeError, match=""):
        ImageReference.parse("app:9.3").__eq__("app:9.3")


def test___repr__() -> None:
    assert "reg.io/app:9.3" in repr(ImageReference.parse("reg.io/app:9.3"))


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
def test_direct_initialization(attrs: dict[str, str], expected: Union[str, ImageRefTuple]) -> None:
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
            ImageReference("app", registry="reg.io", namespace="org", tag="9.3", digest=FAKE_DIGEST),
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
def test_as_dict(image_ref: ImageReference, expected: dict[str, str]) -> None:
    assert expected == image_ref.as_dict()


@pytest.mark.parametrize(
    "origin_ref,expected",
    [
        [ImageReference("app"), ("", "", "app", "", "")],
        [ImageReference("app", registry="reg.io"), ("reg.io", "", "app", "", "")],
        [
            ImageReference("app", registry="reg.io", namespace="org"),
            ("reg.io", "org", "app", "", ""),
        ],
        [
            ImageReference("app", registry="reg.io", namespace="org", tag="9.3"),
            ("reg.io", "org", "app", "9.3", ""),
        ],
        [
            ImageReference("app", registry="reg.io", namespace="org", tag="9.3", digest=FAKE_DIGEST),
            ("reg.io", "org", "app", "9.3", FAKE_DIGEST),
        ],
    ],
)
def test___copy__(origin_ref: ImageReference, expected: ImageRefTuple) -> None:
    ref = copy.copy(origin_ref)
    assert id(ref) != id(origin_ref)
    assert expected == (ref.registry, ref.namespace, ref.repository, ref.tag, ref.digest)
