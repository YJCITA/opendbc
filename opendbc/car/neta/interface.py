from cereal import car
from panda import Panda
from opendbc.car.common.conversions import Conversions as CV
from opendbc.car import STD_CARGO_KG, get_safety_config, create_button_events
from opendbc.car.interfaces import CarInterfaceBase
from opendbc.car.neta.values import CAR, CanBus, NetworkLocation, TransmissionType, GearShifter,CruiseButtons
from opendbc.car.neta.carstate import CarState
from opendbc.car.neta.carcontroller import CarController
from opendbc.car import get_safety_config, structs


class CarInterface(CarInterfaceBase):
  CarState = CarState
  CarController = CarController

  @staticmethod
  def _get_params(ret: structs.CarParams, candidate: CAR, fingerprint, car_fw, experimental_long, docs) -> structs.CarParams:
  # def _get_params(ret, candidate, fingerprint, car_fw, experimental_long, docs):
    ret.brand = "neta"
    ret.radarUnavailable = True
    ret.safetyConfigs = [get_safety_config(car.CarParams.SafetyModel.neta)]
    ret.enableBsm = False

    ret.transmissionType = TransmissionType.manual
    ret.networkLocation = NetworkLocation.fwdCamera

    ret.steerActuatorDelay = 0.1
    ret.steerLimitTimer = 0.4
    ret.steerRatio = 15.6  # Let the params learner figure this out
    ret.lateralTuning.pid.kpBP = [0.]
    ret.lateralTuning.pid.kiBP = [0.]
    ret.lateralTuning.pid.kf = 0.00006
    ret.lateralTuning.pid.kpV = [0.6]
    ret.lateralTuning.pid.kiV = [0.2]

    # Global longitudinal tuning defaults, can be overridden per-vehicle
    ret.experimentalLongitudinalAvailable = ret.networkLocation == NetworkLocation.gateway or docs
    if experimental_long:
      # Proof-of-concept, prep for E2E only. No radar points available. Panda ALLOW_DEBUG firmware required.
      ret.openpilotLongitudinalControl = True
      ret.safetyConfigs[0].safetyParam |= Panda.FLAG_NETA_LONG_CONTROL
      if ret.transmissionType == TransmissionType.manual:
        ret.minEnableSpeed = 4.5

    ret.pcmCruise = True
    # ret.stoppingControl = True
    ret.startingState = True
    ret.startAccel = 1.0
    ret.stopAccel = -0.55
    ret.vEgoStarting = 1.0
    ret.vEgoStopping = 1.0
    ret.longitudinalTuning.kpV = [0.1]
    ret.longitudinalTuning.kiV = [0.0]

    if candidate == CAR.NETA_L_ARS513 or candidate == CAR.NETA_L_CH :
        ret.radarUnavailable = False

    ret.openpilotLongitudinalControl = True
    ret.steerControlType = structs.CarParams.SteerControlType.angle

    cfgs = [get_safety_config(car.CarParams.SafetyModel.neta), ]
    cfgs.insert(0, get_safety_config(car.CarParams.SafetyModel.noOutput))

    ret.safetyConfigs = cfgs
    ret.mass = 2070 + STD_CARGO_KG
    ret.wheelbase = 2.81
    ret.steerRatio = 15.84
    tire_stiffness_factor = 0.5533
    ret.steerActuatorDelay = 0 #0.25
    ret.steerLimitTimer = 0.8


    ret.autoResumeSng = ret.minEnableSpeed == -1
    ret.centerToFront = ret.wheelbase * 0.45
    return ret
