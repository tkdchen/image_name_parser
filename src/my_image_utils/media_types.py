from collections.abc import Iterable
from enum import Enum, unique


@unique
class OCIV1(Enum):
    """Media types defined by OCI image spec v1

    OCI media types are described in media-types.md#oci-image-media-types under
    opencontainers/image-spec.
    """

    IMAGE_MANIFEST = "application/vnd.oci.image.manifest.v1+json"
    IMAGE_INDEX = "application/vnd.oci.image.index.v1+json"
    IMAGE_CONFIG = "application/vnd.oci.image.config.v1+json"

    # Layer, as a tar archive
    IMAGE_LAYER_TAR = "application/vnd.oci.image.layer.v1.tar"

    # Layer, as a tar archive compressed with gzip
    IMAGE_LAYER_GZIP = "application/vnd.oci.image.layer.v1.tar+gzip"

    # Layer, as a tar archive compressed with zstd
    IMAGE_LAYER_ZSTD = "application/vnd.oci.image.layer.v1.tar+zstd"

    # Content Descriptor
    DESCRIPTOR = "application/vnd.oci.descriptor.v1+json"
    # OCI Layout
    LAYOUT_HEADER = "application/vnd.oci.layout.header.v1+json"
    # Empty for unused descriptors
    EMPTY = "application/vnd.oci.empty.v1+json"

    # Layer, as a tar archive
    IMAGE_LAYER_NONDISTRIBUTABLE = "application/vnd.oci.image.layer.nondistributable.v1.tar"

    # Layer, as a tar archive with distribution restrictions compressed with gzip
    IMAGE_LAYER_NONDISTRIBUTABLE_GZIP = "application/vnd.oci.image.layer.nondistributable.v1.tar+gzip"

    # Layer, as a tar archive with distribution restrictions compressed with zstd
    IMAGE_LAYER_NONDISTRIBUTABLE_ZSTD = "application/vnd.oci.image.layer.nondistributable.v1.tar+zstd"


@unique
class ImageManifestV2S2(Enum):
    """Media types defined by Image Manifest Version 2, Schema 2.

    Media types are described in manifest-v2-2.md#media-types under
    distribution/distribution.
    """

    # Relates to IMAGE_MANIFEST_OCI_V1
    DISTRIBUTION_MANIFEST = "application/vnd.docker.distribution.manifest.v2+json"

    # Manifest list, aka "fat manifest"
    DISTRIBUTION_MANIFEST_LIST = "application/vnd.docker.distribution.manifest.list.v2+json"

    # Container config JSON
    CONTAINER_IMAGE = "application/vnd.docker.container.image.v1+json"

    # Layer, as a gzipped tar
    IMAGE_ROOTFS_DIFF_GZIP = "application/vnd.docker.image.rootfs.diff.tar.gzip"


def media_types_compatibility_matrix() -> Iterable[tuple[str, str]]:
    """
    Return media type compatibility matrix between OCI image spec and
    distribution project Image manifest definition.

    Refer to media-types.md#compatibility-matrix under opencontainers/image-spec.
    """
    return (
        (OCIV1.IMAGE_MANIFEST.value, ImageManifestV2S2.DISTRIBUTION_MANIFEST.value),
        (OCIV1.IMAGE_INDEX.value, ImageManifestV2S2.DISTRIBUTION_MANIFEST_LIST.value),
        (OCIV1.IMAGE_CONFIG.value, ImageManifestV2S2.CONTAINER_IMAGE.value),
        (OCIV1.IMAGE_LAYER_GZIP.value, ImageManifestV2S2.IMAGE_ROOTFS_DIFF_GZIP.value),
    )
