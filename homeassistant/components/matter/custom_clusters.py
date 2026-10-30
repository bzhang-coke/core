"""Custom Matter cluster descriptors used by Home Assistant."""

from dataclasses import dataclass
from typing import Any

from chip.clusters.ClusterObjects import (
    Cluster,
    ClusterAttributeDescriptor,
    ClusterObjectDescriptor,
    ClusterObjectFieldDescriptor,
)
from chip.tlv import float32, uint

GEP_CUSTOM_CLUSTER_ID = 0xFFF1FC00
GEP_DEVICE_INFO_CLUSTER_ID = 0xFFF1FC10
GEP_DEVICE_CONFIGURATION_CLUSTER_ID = 0xFFF1FC11
GEP_DEVICE_TELEMETRY_CLUSTER_ID = 0xFFF1FC12
GEP_CHANNEL_CONFIGURATION_CLUSTER_ID = 0xFFF1FC30
GEP_CHANNEL_CALIBRATION_CLUSTER_ID = 0xFFF1FC31
GEP_CHANNEL_TELEMETRY_CLUSTER_ID = 0xFFF1FC32

type AttributeSpec = tuple[str, str, int, Any]


def _attribute_descriptor(
    name: str, cluster_id: int, attribute_id: int, value_type: Any
) -> type[ClusterAttributeDescriptor]:
    """Create an attribute descriptor for a custom cluster."""
    return dataclass(
        type(
            name,
            (ClusterAttributeDescriptor,),
            {
                "cluster_id": cluster_id,
                "attribute_id": attribute_id,
                "attribute_type": ClusterObjectFieldDescriptor(Type=value_type),
                "__annotations__": {"value": Any},
                "value": None,
            },
        )
    )


def _custom_cluster(
    name: str, cluster_id: int, attributes: tuple[AttributeSpec, ...]
) -> type[Cluster]:
    """Create a custom cluster and its attribute descriptors."""
    descriptor = ClusterObjectDescriptor(
        Fields=[
            ClusterObjectFieldDescriptor(Label=label, Tag=attribute_id, Type=value_type)
            for _, label, attribute_id, value_type in attributes
        ]
        + [
            ClusterObjectFieldDescriptor(
                Label="feature_map", Tag=0x0000FFFC, Type=uint
            ),
            ClusterObjectFieldDescriptor(
                Label="cluster_revision", Tag=0x0000FFFD, Type=uint
            ),
        ]
    )
    attribute_descriptors = type(
        "Attributes",
        (),
        {
            **{
                attr_name: _attribute_descriptor(
                    attr_name, cluster_id, attribute_id, value_type
                )
                for attr_name, _, attribute_id, value_type in attributes
            },
            "FeatureMap": _attribute_descriptor("FeatureMap", cluster_id, 0xFFFC, uint),
            "ClusterRevision": _attribute_descriptor(
                "ClusterRevision", cluster_id, 0xFFFD, uint
            ),
        },
    )
    return dataclass(
        type(
            name,
            (Cluster,),
            {
                "id": cluster_id,
                "descriptor": descriptor,
                "Attributes": attribute_descriptors,
            },
        )
    )


GepCustomCluster = _custom_cluster(
    "GepCustomCluster",
    GEP_CUSTOM_CLUSTER_ID,
    (
        ("TargetFlowRate", "target_flow_rate", 0x0000, float32 | None),
        ("CurrentFlowRate", "current_flow_rate", 0x0001, float32 | None),
        ("TargetRatio", "target_ratio", 0x0002, float32 | None),
        ("CurrentRatio", "current_ratio", 0x0003, float32 | None),
        ("LeverPressCount", "lever_press_count", 0x0004, uint | None),
    ),
)

GepDeviceInfoCluster = _custom_cluster(
    "GepDeviceInfoCluster",
    GEP_DEVICE_INFO_CLUSTER_ID,
    (
        ("ProductId", "product_id", 0x0000, uint),
        ("SerialNumber", "serial_number", 0x0001, str),
        (
            "ConnectivityBootloaderVersion",
            "connectivity_bootloader_version",
            0x0002,
            uint,
        ),
        (
            "ConnectivityApplicationVersion",
            "connectivity_application_version",
            0x0003,
            uint,
        ),
        ("RtMcuBootloaderVersion", "rt_mcu_bootloader_version", 0x0004, uint),
        ("RtMcuApplicationVersion", "rt_mcu_application_version", 0x0005, uint),
        ("DataModelVersion", "data_model_version", 0x0006, uint),
        ("InterMcuProtocolVersion", "inter_mcu_protocol_version", 0x0007, uint),
        ("MatterStackVersion", "matter_stack_version", 0x0008, uint),
        ("ControlBoard", "control_board", 0x0009, uint),
        ("ChannelCount", "channel_count", 0x000A, uint),
        ("ManufactureDate", "manufacture_date", 0x000B, uint),
        ("ManufacturePlant", "manufacture_plant", 0x000C, uint),
        ("ManufactureLine", "manufacture_line", 0x000D, uint),
        ("ManufactureLot", "manufacture_lot", 0x000E, uint),
        ("ManufacturerCode", "manufacturer_code", 0x000F, uint),
        ("EolTestDate", "eol_test_date", 0x0010, uint),
        ("TestFixtureIdentifier", "test_fixture_identifier", 0x0011, uint),
    ),
)

GepDeviceConfigurationCluster = _custom_cluster(
    "GepDeviceConfigurationCluster",
    GEP_DEVICE_CONFIGURATION_CLUSTER_ID,
    (
        ("Blocked", "blocked", 0x1000, bool),
        ("BeverageRatio", "beverage_ratio", 0x1001, float32),
        ("TargetBeverageFlowrate", "target_beverage_flowrate", 0x1002, uint),
        ("ExternalModuleId", "external_module_id", 0x1003, uint),
        ("ExternalModuleParameters", "external_module_parameters", 0x1004, bytes),
        ("DispenseWaterOnly", "dispense_water_only", 0x1005, bool),
    ),
)

GepDeviceTelemetryCluster = _custom_cluster(
    "GepDeviceTelemetryCluster",
    GEP_DEVICE_TELEMETRY_CLUSTER_ID,
    (
        ("PouredChannels", "poured_channels", 0x3000, uint),
        ("McuVoltage", "mcu_voltage", 0x3001, uint),
        ("McuTemperature", "mcu_temperature", 0x3002, uint),
        ("Uptime", "uptime", 0x3003, uint),
        ("BootCounter", "boot_counter", 0x3004, uint),
        ("DeviceAlarms", "device_alarms", 0x4000, uint),
    ),
)

GepChannelConfigurationCluster = _custom_cluster(
    "GepChannelConfigurationCluster",
    GEP_CHANNEL_CONFIGURATION_CLUSTER_ID,
    (
        ("FluidId", "fluid_id", 0x1100, uint),
        ("ViscosityParameter", "viscosity_parameter", 0x1101, float32),
        (
            "RegressionModelParameters",
            "regression_model_parameters",
            0x1102,
            list[float32],
        ),
        ("FlowSetpoint", "flow_setpoint", 0x1103, uint),
        ("RegressionModelId", "regression_model_id", 0x1104, uint),
    ),
)

GepChannelCalibrationCluster = _custom_cluster(
    "GepChannelCalibrationCluster",
    GEP_CHANNEL_CALIBRATION_CLUSTER_ID,
    (
        ("LinearizationCurve", "linearization_curve", 0x2000, list[uint]),
        ("DeltaPressureCorrection", "delta_pressure_correction", 0x2001, float32),
        ("TemperatureCorrection", "temperature_correction", 0x2002, float32),
        ("FlowmeterCalibration", "flowmeter_calibration", 0x2003, float32),
        ("ActuatorTuningMinimum", "actuator_tuning_minimum", 0x2004, uint),
        ("ActuatorTuningMaximum", "actuator_tuning_maximum", 0x2005, uint),
        ("ActuatorTuningIdle", "actuator_tuning_idle", 0x2006, uint),
        ("ActuatorMagnetPolarity", "actuator_magnet_polarity", 0x2007, uint),
    ),
)

GepChannelTelemetryCluster = _custom_cluster(
    "GepChannelTelemetryCluster",
    GEP_CHANNEL_TELEMETRY_CLUSTER_ID,
    (
        ("ChannelState", "channel_state", 0x3100, uint),
        ("Opening", "opening", 0x3101, uint),
        ("PwmDutyCycle", "pwm_duty_cycle", 0x3102, uint),
        ("Temperature", "temperature", 0x3103, uint),
        ("Flowrate", "flowrate", 0x3104, uint),
        ("Volume", "volume", 0x3105, uint),
        ("DeltaPressure", "delta_pressure", 0x3106, uint),
        ("Pressure0", "pressure_0", 0x3107, uint),
        ("Pressure1", "pressure_1", 0x3108, uint),
        ("DispensingTime", "dispensing_time", 0x3109, uint),
        ("AverageOpening", "average_opening", 0x310A, uint),
        ("AveragePwmDutyCycle", "average_pwm_duty_cycle", 0x310B, uint),
        ("AverageTemperature", "average_temperature", 0x310C, uint),
        ("AverageFlowrate", "average_flowrate", 0x310D, uint),
        ("AverageVolume", "average_volume", 0x310E, uint),
        ("AverageDeltaPressure", "average_delta_pressure", 0x310F, uint),
        ("AveragePressure0", "average_pressure_0", 0x3110, uint),
        ("AveragePressure1", "average_pressure_1", 0x3111, uint),
        ("AverageDispensingTime", "average_dispensing_time", 0x3112, uint),
        ("ActuatorCalibrationCounter", "actuator_calibration_counter", 0x3113, uint),
        ("ActuationsCounter", "actuations_counter", 0x3114, uint),
        ("ChannelAlarms", "channel_alarms", 0x4100, uint),
    ),
)
