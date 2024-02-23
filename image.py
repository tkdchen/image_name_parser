import os.path
import re
from typing import Final

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
