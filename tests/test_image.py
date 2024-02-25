import copy
import pytest
from image_name_parser import ImageReference
from typing import Final, Union

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
