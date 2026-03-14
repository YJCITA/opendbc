"""
Copyright (c) 2021-, Haibin Wen, sunnypilot, and a number of other contributors.

This file is part of sunnypilot and is licensed under the MIT License.
See the LICENSE.md file in the root directory for more details.
"""
from enum import StrEnum

from opendbc.car import Bus, create_button_events, structs
from opendbc.can.parser import CANParser
from opendbc.car.common.conversions import Conversions as CV
from opendbc.car.tesla.values import DBC, CANBUS
from opendbc.sunnypilot.car.tesla.values import TeslaFlagsSP

ButtonType = structs.CarState.ButtonEvent.Type


class CarStateExt:
  def __init__(self, CP: structs.CarParams, CP_SP: structs.CarParamsSP):
    self.CP = CP
    self.CP_SP = CP_SP

    self.infotainment_3_finger_press = 0

    self.gap_adjust_prev = False  # scroll+cruise for gap adjustment (no gas required)
    self.gap_adjust_press_after_stable = False  # True only if current press started after cruise was already stable
    self.brake_combo_prev = False
    self.cruise_enabled_prev = False
    self.cruise_enabled_frames = 0  # debounce: only emit gap_adjust after cruise stable

  def update(self, ret: structs.CarState, ret_sp: structs.CarStateSP, can_parsers: dict[StrEnum, CANParser]) -> None:
    button_events = []
    if self.CP_SP.flags & TeslaFlagsSP.HAS_VEHICLE_BUS:
      cp_adas = can_parsers[Bus.adas]

      prev_infotainment_3_finger_press = self.infotainment_3_finger_press
      self.infotainment_3_finger_press = int(cp_adas.vl["UI_status2"]["UI_activeTouchPoints"])

      button_events += create_button_events(self.infotainment_3_finger_press, prev_infotainment_3_finger_press,
                                                {3: ButtonType.lkas})

    cp_party = can_parsers[Bus.party]
    cp_ap_party = can_parsers[Bus.ap_party]

    speed_units = self.can_define.dv["DI_state"]["DI_speedUnits"].get(int(cp_party.vl["DI_state"]["DI_speedUnits"]), None)
    speed_limit = cp_ap_party.vl["DAS_status"]["DAS_fusedSpeedLimit"]
    if self.can_define.dv["DAS_status"]["DAS_fusedSpeedLimit"].get(int(speed_limit), None) in ["NONE", "UNKNOWN_SNA"]:
      ret_sp.speedLimit = 0
    else:
      if speed_units == "KPH":
        ret_sp.speedLimit = speed_limit * CV.KPH_TO_MS
      elif speed_units == "MPH":
        ret_sp.speedLimit = speed_limit * CV.MPH_TO_MS

    ret.genericToggle = cp_party.vl["UI_warning"]["scrollWheelPressed"] != 0

    # Gap adjustment: scroll+cruise. Only emit release when press started after cruise was already stable (avoids
    # activation gesture press+release firing gapAdjustCruise and changing personality).
    gap_adjust = ret.genericToggle and ret.cruiseState.enabled
    if ret.cruiseState.enabled:
      self.cruise_enabled_frames += 1
    else:
      self.cruise_enabled_frames = 0
    cruise_stable = self.cruise_enabled_prev and self.cruise_enabled_frames >= 200  # ~2s at 100Hz

    if gap_adjust and not self.gap_adjust_prev:
      self.gap_adjust_press_after_stable = cruise_stable
    if not gap_adjust:
      self.gap_adjust_press_after_stable = False

    if cruise_stable and (gap_adjust != self.gap_adjust_prev) and (gap_adjust or self.gap_adjust_press_after_stable):
      button_events += create_button_events(int(gap_adjust), int(self.gap_adjust_prev), {1: ButtonType.gapAdjustCruise})
    self.gap_adjust_prev = gap_adjust

    # Add brake + scroll press combo as a button event for LKAS
    brake_combo = ret.brakePressed and ret.genericToggle
    button_events += create_button_events(int(brake_combo), int(self.brake_combo_prev), {1: ButtonType.lkas})
    ret.buttonEvents = button_events
    self.brake_combo_prev = brake_combo
    self.cruise_enabled_prev = ret.cruiseState.enabled

  @staticmethod
  def get_parser(CP: structs.CarParams, CP_SP: structs.CarParamsSP) -> dict[StrEnum, CANParser]:
    messages = {}

    if CP_SP.flags & TeslaFlagsSP.HAS_VEHICLE_BUS:
      messages[Bus.adas] = CANParser(DBC[CP.carFingerprint][Bus.adas], [], CANBUS.vehicle)

    return messages
