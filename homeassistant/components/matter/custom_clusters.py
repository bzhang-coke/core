"""Custom Matter cluster descriptors used by Home Assistant."""

# pylint: disable=missing-class-docstring

from dataclasses import dataclass

from chip.clusters.ClusterObjects import (
    Cluster,
    ClusterAttributeDescriptor,
    ClusterObjectDescriptor,
    ClusterObjectFieldDescriptor,
)
from chip.tlv import float32, uint

GEP_CUSTOM_CLUSTER_ID = 0xFFF1FC00


@dataclass
class GepCustomCluster(Cluster):  # type: ignore[misc]
    """GEP custom cluster for water valve devices."""

    id = GEP_CUSTOM_CLUSTER_ID
    descriptor = ClusterObjectDescriptor(
        Fields=[
            ClusterObjectFieldDescriptor(
                Label="target_flow_rate",
                Tag=0x00000000,
                Type=float32 | None,
            ),
            ClusterObjectFieldDescriptor(
                Label="current_flow_rate",
                Tag=0x00000001,
                Type=float32 | None,
            ),
            ClusterObjectFieldDescriptor(
                Label="target_ratio",
                Tag=0x00000002,
                Type=float32 | None,
            ),
            ClusterObjectFieldDescriptor(
                Label="current_ratio",
                Tag=0x00000003,
                Type=float32 | None,
            ),
            ClusterObjectFieldDescriptor(
                Label="lever_press_count",
                Tag=0x00000004,
                Type=uint | None,
            ),
            ClusterObjectFieldDescriptor(
                Label="feature_map", Tag=0x0000FFFC, Type=uint
            ),
            ClusterObjectFieldDescriptor(
                Label="cluster_revision", Tag=0x0000FFFD, Type=uint
            ),
        ]
    )

    class Attributes:
        """Attribute descriptors for the GEP custom cluster."""

        @dataclass
        class TargetFlowRate(ClusterAttributeDescriptor):  # type: ignore[misc]
            """Target flow rate value requested by the controller."""

            cluster_id = GEP_CUSTOM_CLUSTER_ID
            attribute_id = 0x0000
            attribute_type = ClusterObjectFieldDescriptor(Type=float32 | None)
            value: float32 | None = None

        @dataclass
        class CurrentFlowRate(ClusterAttributeDescriptor):  # type: ignore[misc]
            """Current measured flow rate reported by the device."""

            cluster_id = GEP_CUSTOM_CLUSTER_ID
            attribute_id = 0x0001
            attribute_type = ClusterObjectFieldDescriptor(Type=float32 | None)
            value: float32 | None = None

        @dataclass
        class TargetRatio(ClusterAttributeDescriptor):  # type: ignore[misc]
            """Target ratio value requested by the controller."""

            cluster_id = GEP_CUSTOM_CLUSTER_ID
            attribute_id = 0x0002
            attribute_type = ClusterObjectFieldDescriptor(Type=float32 | None)
            value: float32 | None = None

        @dataclass
        class CurrentRatio(ClusterAttributeDescriptor):  # type: ignore[misc]
            """Current measured ratio reported by the device."""

            cluster_id = GEP_CUSTOM_CLUSTER_ID
            attribute_id = 0x0003
            attribute_type = ClusterObjectFieldDescriptor(Type=float32 | None)
            value: float32 | None = None

        @dataclass
        class LeverPressCount(ClusterAttributeDescriptor):  # type: ignore[misc]
            """Count of lever presses reported by the device."""

            cluster_id = GEP_CUSTOM_CLUSTER_ID
            attribute_id = 0x0004
            attribute_type = ClusterObjectFieldDescriptor(Type=uint | None)
            value: uint | None = None

        @dataclass
        class FeatureMap(ClusterAttributeDescriptor):  # type: ignore[misc]
            """Matter feature map bitmap for this cluster."""

            cluster_id = GEP_CUSTOM_CLUSTER_ID
            attribute_id = 0xFFFC
            attribute_type = ClusterObjectFieldDescriptor(Type=uint)
            value: uint = 0

        @dataclass
        class ClusterRevision(ClusterAttributeDescriptor):  # type: ignore[misc]
            """Matter cluster revision value."""

            cluster_id = GEP_CUSTOM_CLUSTER_ID
            attribute_id = 0xFFFD
            attribute_type = ClusterObjectFieldDescriptor(Type=uint)
            value: uint = 1
