from typing import Any, Dict, List, Optional, Union

from loguru import logger
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# --- Utility Function (used by Input models) ---
def clean_number(value: Any) -> Optional[Union[float, int, str]]:
    logger.debug(f"clean_number received: '{value}' (type: {type(value)})")
    if value is None or value == "---":
        logger.debug("clean_number returning None for '---' or None")
        return None
    if isinstance(value, (int, float)):
        logger.debug(f"clean_number returning as is (already numeric): {value}")
        return value
    if isinstance(value, str):
        num_part = value.split(",")[0].strip()
        try:
            if "." in num_part or "e" in num_part.lower():
                return float(num_part)
            return int(num_part)
        except ValueError:
            logger.warning(
                f"Could not parse numeric value from '{value}' (num_part: '{num_part}'), returning original value."
            )
            return value
    logger.warning(
        f"clean_number received unhandled type or value: '{value}' (type: {type(value)}), returning as is."
    )
    return value


# --- Forward Declarations for Output Models (for type hints in to_output methods) ---
class AlarmEntryOutput(BaseModel):
    pass


class ConfigAlarmSettingOutput(BaseModel):
    pass


class IntSensorTimeoutOutput(BaseModel):
    pass


class CheckedTimestampsOutput(BaseModel):
    pass


class HistoryRecordOutput(BaseModel):
    pass


class DeviceConfigOutput(BaseModel):
    pass


class CertificateOutput(BaseModel):
    pass


class QTagDataOutput(BaseModel):
    pass


# --- Input Models (for parsing raw data, using aliases) ---


class AlarmEntryInput(BaseModel):
    t_Acc: Optional[Any] = Field(default=None, alias="t Acc")
    TS_A: Optional[str] = Field(default=None, alias="TS A")
    C_A: Optional[Any] = Field(default=None, alias="C A")

    @model_validator(mode="before")
    @classmethod
    def preprocess_alarm_data(cls, data: Any) -> Any:
        logger.debug(
            f"AlarmEntryInput model_validator (preprocess_alarm_data) received: {data}"
        )
        if isinstance(data, dict):
            if "t Acc" in data:
                data["t Acc"] = clean_number(data["t Acc"])
            if "C A" in data and data["C A"] is not None:
                data["C A"] = clean_number(data["C A"])
        logger.debug(
            f"AlarmEntryInput model_validator (preprocess_alarm_data) returning: {data}"
        )
        return data

    def to_output(self) -> AlarmEntryOutput:
        # Convert accumulated time from minutes to hh:mm format
        formatted_time = None
        if self.t_Acc is not None:
            try:
                total_minutes = int(self.t_Acc)
                hours = total_minutes // 60
                minutes = total_minutes % 60
                formatted_time = f"{hours:02d}:{minutes:02d}"
            except (ValueError, TypeError):
                formatted_time = self.t_Acc  # Keep original if conversion fails
        
        return AlarmEntryOutput(
            accumulatedTime=formatted_time,
            alarmTimestamp=self.TS_A,
            alarmCount=self.C_A,
        )


class ConfigAlarmSettingInput(BaseModel):
    T_AL: Optional[Any] = Field(default=None, alias="T AL")
    t_AL: Optional[Any] = Field(default=None, alias="t AL")

    @field_validator("T_AL", "t_AL", mode="before")
    @classmethod
    def clean_config_alarm_numerics(cls, v: Any) -> Any:
        return clean_number(v)

    def to_output(self) -> ConfigAlarmSettingOutput:
        return ConfigAlarmSettingOutput(
            temperatureLimit=self.T_AL,
            timeLimit=self.t_AL,
        )


class IntSensorTimeoutInput(BaseModel):
    t_AccST: Optional[Any] = Field(default=None, alias="t AccST")

    @field_validator("t_AccST", mode="before")
    @classmethod
    def clean_t_accst(cls, v: Any) -> Any:
        return clean_number(v)

    def to_output(self) -> IntSensorTimeoutOutput:
        return IntSensorTimeoutOutput(accumulatedSensorTimeout=self.t_AccST)


class CheckedTimestampsInput(BaseModel):
    TS_PM: Optional[str] = Field(
        default=None, alias="TS PM"
    )  # Added alias for consistency
    TS_AM: Optional[str] = Field(
        default=None, alias="TS AM"
    )  # Added alias for consistency

    def to_output(self) -> CheckedTimestampsOutput:
        return CheckedTimestampsOutput(
            timestampPm=self.TS_PM,
            timestampAm=self.TS_AM,
        )


class HistoryRecordInput(BaseModel):
    Date: Optional[str] = None
    Min_T: Optional[Any] = Field(default=None, alias="Min T")
    TS_Min_T: Optional[str] = Field(default=None, alias="TS Min T")
    Max_T: Optional[Any] = Field(default=None, alias="Max T")
    TS_Max_T: Optional[str] = Field(default=None, alias="TS Max T")
    Avrg_T: Optional[Any] = Field(default=None, alias="Avrg T")
    Alarm: Optional[Dict[str, AlarmEntryInput]] = None
    Int_Sensor_timeout: Optional[IntSensorTimeoutInput] = Field(
        default=None, alias="Int Sensor timeout"
    )
    Events: Optional[Any] = None
    Checked: Optional[CheckedTimestampsInput] = None

    @field_validator("Min_T", "Max_T", "Avrg_T", "Events", mode="before")
    @classmethod
    def clean_history_numerics(cls, v: Any) -> Any:
        return clean_number(v)

    def to_output(self) -> HistoryRecordOutput:
        return HistoryRecordOutput(
            date=self.Date,
            minTemperature=self.Min_T,
            timestampMinTemperature=self.TS_Min_T,
            maxTemperature=self.Max_T,
            timestampMaxTemperature=self.TS_Max_T,
            averageTemperature=self.Avrg_T,
            alarms={k: v.to_output() for k, v in self.Alarm.items()}
            if self.Alarm
            else None,
            internalSensorTimeout=(
                self.Int_Sensor_timeout.to_output() if self.Int_Sensor_timeout else None
            ),
            eventCount=self.Events,
            checkedTimestamps=self.Checked.to_output() if self.Checked else None,
        )


class DeviceConfigInput(BaseModel):
    Serial: Optional[str] = None
    PCB: Optional[str] = None
    CID: Optional[str] = None
    Lot: Optional[str] = None
    Zone: Optional[Any] = None
    Measurement_delay: Optional[Any] = Field(default=None, alias="Measurement delay")
    Moving_Avrg: Optional[Any] = Field(default=None, alias="Moving Avrg")
    User_Alarm_Config: Optional[Any] = Field(default=None, alias="User Alarm Config")
    User_Clock_Config: Optional[Any] = Field(default=None, alias="User Clock Config")
    Alarm_Indication: Optional[Any] = Field(default=None, alias="Alarm Indication")
    Temp_unit: Optional[str] = Field(default=None, alias="Temp unit")
    Alarm: Optional[Dict[str, ConfigAlarmSettingInput]] = None
    # Fields that were previously top-level in QTagData but parsed under Conf
    Int_Sensor: Optional[Dict[str, str]] = Field(
        default=None, alias="Int Sensor"
    )  # Keep as dict for input
    Report_history_length: Optional[Any] = Field(
        default=None, alias="Report history length"
    )
    Det_Report: Optional[Any] = Field(default=None, alias="Det Report")
    Use_ext_devices: Optional[Any] = Field(default=None, alias="Use ext devices")
    Test_Res: Optional[Any] = Field(default=None, alias="Test Res")
    Test_TS: Optional[str] = Field(default=None, alias="Test TS")

    @field_validator(
        "Zone",
        "Measurement_delay",
        "Moving_Avrg",
        "User_Alarm_Config",
        "User_Clock_Config",
        "Alarm_Indication",
        "Report_history_length",
        "Det_Report",
        "Use_ext_devices",
        "Test_Res",
        mode="before",
    )
    @classmethod
    def clean_config_numerics(cls, v: Any) -> Any:
        return clean_number(v)

    def to_output(self) -> DeviceConfigOutput:
        # Note: Int_Sensor from input is a Dict[str, str], e.g. {'Timeout': '1', 'Offset': '+0.0'}
        # Output model might want this structured differently or kept as is.
        # For now, let's assume it becomes a simple dict in output or specific fields.
        # Let's make it specific for the known sub-fields.
        internal_sensor_config = None
        if self.Int_Sensor:
            internal_sensor_config = {
                "timeout": clean_number(self.Int_Sensor.get("Timeout")),
                "offset": clean_number(self.Int_Sensor.get("Offset")),
            }

        return DeviceConfigOutput(
            serialNumber=self.Serial,
            pcbVersion=self.PCB,
            customerId=self.CID,
            lotNumber=self.Lot,
            timeZoneOffsetHours=self.Zone,  # Assuming Zone is hours
            measurementDelaySeconds=self.Measurement_delay,
            movingAverageSamples=self.Moving_Avrg,
            userAlarmConfigFlag=self.User_Alarm_Config,
            userClockConfigFlag=self.User_Clock_Config,
            alarmIndicationMode=self.Alarm_Indication,
            temperatureUnit=self.Temp_unit,
            alarmSettings={k: v.to_output() for k, v in self.Alarm.items()}
            if self.Alarm
            else None,
            internalSensor=internal_sensor_config,  # Transformed Int_Sensor
            reportHistoryLengthDays=self.Report_history_length,
            detailedReportType=self.Det_Report,  # Assuming this is a type/flag
            useExternalDevicesFlag=self.Use_ext_devices,
            lastTestResult=self.Test_Res,  # Assuming 1=Pass, 0=Fail or similar
            lastTestTimestamp=self.Test_TS,
        )


class CertificateInput(BaseModel):
    Vers: Optional[str] = None
    Lot: Optional[str] = None
    Issuer: Optional[str] = None
    Valid_from: Optional[str] = Field(default=None, alias="Valid from")
    Owner: Optional[str] = None
    Public_Key: Optional[str] = Field(default=None, alias="Public Key")
    Sig_Cert: Optional[str] = Field(default=None, alias="Sig Cert")
    Sig: Optional[str] = Field(default=None)

    def to_output(self) -> CertificateOutput:
        return CertificateOutput(
            version=self.Vers,
            lotNumber=self.Lot,
            issuerName=self.Issuer,
            validFromTimestamp=self.Valid_from,
            ownerName=self.Owner,
            publicKey=self.Public_Key,
            signatureCertificate=self.Sig_Cert,
            signature=self.Sig,
        )


class QTagDataInput(BaseModel):
    Device: Optional[str] = None
    Vers: Optional[str] = None
    Fw_Vers: Optional[str] = Field(default=None, alias="Fw Vers")
    Sensor: Optional[Any] = None
    Conf: Optional[DeviceConfigInput] = None
    # Top-level Alarm from text file, if any (distinct from Conf.Alarm)
    # This field was in the original QTagData model, but data usually comes from Conf.Alarm
    Alarm: Optional[Dict[str, ConfigAlarmSettingInput]] = None
    Hist: Optional[List[HistoryRecordInput]] = Field(default_factory=list)
    TS_Actv: Optional[str] = Field(default=None, alias="TS Actv")
    TS_Report_Creation: Optional[str] = Field(default=None, alias="TS Report Creation")
    Cert: Optional[CertificateInput] = None

    # Removed direct fields like Int_Sensor, Report_history_length etc. from here,
    # as they are parsed under Conf by the current parser logic.
    # If they need to be top-level in output, DeviceConfigInput.to_output()
    # will return them, and QTagDataOutput will incorporate them.

    @field_validator("Sensor", mode="before")
    @classmethod
    def clean_qtag_numerics(cls, v: Any) -> Any:
        return clean_number(v)

    def to_output(self) -> QTagDataOutput:
        config_output = self.Conf.to_output() if self.Conf else None

        # Fields that were originally under Conf in text but might be top-level in output
        # These are now part of DeviceConfigOutput
        internal_sensor_output = config_output.internalSensor if config_output else None
        report_history_length_output = (
            config_output.reportHistoryLengthDays if config_output else None
        )
        detailed_report_type_output = (
            config_output.detailedReportType if config_output else None
        )
        use_external_devices_flag_output = (
            config_output.useExternalDevicesFlag if config_output else None
        )
        last_test_result_output = (
            config_output.lastTestResult if config_output else None
        )
        last_test_timestamp_output = (
            config_output.lastTestTimestamp if config_output else None
        )

        return QTagDataOutput(
            deviceType=self.Device,
            softwareVersion=self.Vers,
            firmwareVersion=self.Fw_Vers,
            sensorType=self.Sensor,  # Assuming Sensor is a type identifier
            configuration=config_output,
            # Top-level alarm settings if they exist outside of Conf
            # This might be redundant if all alarm settings are always under Conf
            alarmSettingsGlobal={k: v.to_output() for k, v in self.Alarm.items()}
            if self.Alarm
            else None,
            historyRecords=[h.to_output() for h in self.Hist] if self.Hist else [],
            activationTimestamp=self.TS_Actv,
            reportCreationTimestamp=self.TS_Report_Creation,
            certificate=self.Cert.to_output() if self.Cert else None,
            # Adding fields that were part of Conf but might be desired at top level of output
            # These are now sourced from the config_output
            internalSensorInfo=internal_sensor_output,
            reportHistoryLength=report_history_length_output,
            detailedReportTypeInfo=detailed_report_type_output,
            useExternalDevices=use_external_devices_flag_output,
            lastTestResultInfo=last_test_result_output,
            lastTestTimestampInfo=last_test_timestamp_output,
        )


# --- Output Models (camelCase, descriptive names) ---
# Pydantic's to_camel alias generator can be used if we want snake_case in Python
# but camelCase in JSON. User asked for camelCase field names directly.


class OutputBaseModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True
    )  # Allows using field names or aliases


class AlarmEntryOutput(OutputBaseModel):
    accumulatedTime: Optional[str] = None  # Formatted as hh:mm
    alarmTimestamp: Optional[str] = None
    alarmCount: Optional[int] = None  # Or consecutiveAlarmPeriods


class ConfigAlarmSettingOutput(OutputBaseModel):
    temperatureLimit: Optional[float] = None
    timeLimit: Optional[int] = None  # Assuming seconds


class IntSensorTimeoutOutput(OutputBaseModel):
    accumulatedSensorTimeout: Optional[int] = None  # Assuming minutes or seconds


class CheckedTimestampsOutput(OutputBaseModel):
    timestampPm: Optional[str] = None
    timestampAm: Optional[str] = None


class HistoryRecordOutput(OutputBaseModel):
    date: Optional[str] = None
    minTemperature: Optional[float] = None
    timestampMinTemperature: Optional[str] = None
    maxTemperature: Optional[float] = None
    timestampMaxTemperature: Optional[str] = None
    averageTemperature: Optional[float] = None
    alarms: Optional[Dict[str, AlarmEntryOutput]] = None
    internalSensorTimeout: Optional[IntSensorTimeoutOutput] = None
    eventCount: Optional[int] = None
    checkedTimestamps: Optional[CheckedTimestampsOutput] = None


class DeviceConfigOutput(OutputBaseModel):
    serialNumber: Optional[str] = None
    pcbVersion: Optional[str] = None
    customerId: Optional[str] = None  # Or customerIdentifier
    lotNumber: Optional[str] = None
    timeZoneOffsetHours: Optional[float] = None
    measurementDelaySeconds: Optional[int] = None
    movingAverageSamples: Optional[int] = None
    userAlarmConfigFlag: Optional[int] = None  # Or userDefinedAlarmConfiguration
    userClockConfigFlag: Optional[int] = None  # Or userDefinedClockConfiguration
    alarmIndicationMode: Optional[int] = None
    temperatureUnit: Optional[str] = None  # 'C' or 'F'
    alarmSettings: Optional[Dict[str, ConfigAlarmSettingOutput]] = None
    internalSensor: Optional[Dict[str, Any]] = (
        None  # e.g. {"timeout": 1, "offset": 0.0}
    )
    reportHistoryLengthDays: Optional[int] = None
    detailedReportType: Optional[int] = None
    useExternalDevicesFlag: Optional[int] = None
    lastTestResult: Optional[int] = None  # e.g. 1 for Pass
    lastTestTimestamp: Optional[str] = None


class CertificateOutput(OutputBaseModel):
    version: Optional[str] = None
    lotNumber: Optional[str] = None
    issuerName: Optional[str] = None
    validFromTimestamp: Optional[str] = None
    ownerName: Optional[str] = None
    publicKey: Optional[str] = None
    signatureCertificate: Optional[str] = None  # Or certificateSignature
    signature: Optional[str] = None


class QTagDataOutput(OutputBaseModel):
    deviceType: Optional[str] = None
    softwareVersion: Optional[str] = None
    firmwareVersion: Optional[str] = None
    sensorType: Optional[int] = None  # Or sensorIdentifier
    configuration: Optional[DeviceConfigOutput] = None
    alarmSettingsGlobal: Optional[Dict[str, ConfigAlarmSettingOutput]] = (
        None  # Top-level alarms if any
    )
    historyRecords: List[HistoryRecordOutput] = Field(default_factory=list)
    activationTimestamp: Optional[str] = None
    reportCreationTimestamp: Optional[str] = None
    certificate: Optional[CertificateOutput] = None

    # Fields that were originally under Conf but might be desired at top level of output
    # These are now sourced from the configuration object during transformation
    internalSensorInfo: Optional[Dict[str, Any]] = None
    reportHistoryLength: Optional[int] = None
    detailedReportTypeInfo: Optional[int] = None
    useExternalDevices: Optional[int] = None
    lastTestResultInfo: Optional[int] = None
    lastTestTimestampInfo: Optional[str] = None


# Update forward references now that all models are defined
AlarmEntryOutput.model_rebuild()
ConfigAlarmSettingOutput.model_rebuild()
IntSensorTimeoutOutput.model_rebuild()
CheckedTimestampsOutput.model_rebuild()
HistoryRecordOutput.model_rebuild()
DeviceConfigOutput.model_rebuild()
CertificateOutput.model_rebuild()
QTagDataOutput.model_rebuild()
CertificateOutput.model_rebuild()
QTagDataOutput.model_rebuild()
QTagDataOutput.model_rebuild()
