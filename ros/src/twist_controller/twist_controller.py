import rospy
from pid import PID
from lowpass import LowPassFilter
from yaw_controller import YawController


GAS_DENSITY = 2.858
ONE_MPH = 0.44704
MIN_SPEED = 0.1


class Controller(object):
    def __init__(self, vehicle_mass, fuel_capacity, brake_deadband, decel_limit, 
                 accel_limit, wheel_radius, wheel_base, steer_ratio, max_lat_accel, max_steer_angle):
        self.yaw_controller = YawController(wheel_base, steer_ratio, MIN_SPEED, max_lat_accel, max_steer_angle)

        kp = 0.3
        ki = 0.1
        kd = 0.
        mn = 0.  # minimum throttle value
        mx = 0.2  # maximum throttle value 
        self.throttle_controller = PID(kp, ki, kd, mn, mx)

        tau = 0.5  # cutoff frequency
        ts = 0.02  # sample time
        self.vel_lpf = LowPassFilter(tau, ts)

        self.vehicle_mass=vehicle_mass
        self.fuel_capacity=fuel_capacity
        self.brake_deadband=brake_deadband
        self.decel_limit=decel_limit
        self.accel_limit=accel_limit
        self.wheel_radius=wheel_radius

        self.last_time = rospy.get_time()


    def control(self, current_vel, dwb_enabled, linear_vel, angular_vel):

        if not dwb_enabled:
            # resets integral term in PID controller
            self.throttle_controller.reset()            
            return 0., 0., 0.

        current_vel = self.vel_lpf.filt(current_vel)

        # steering from yaw controller
        steering = self.yaw_controller.get_steering(linear_vel, angular_vel, current_vel)

        vel_error = linear_vel - current_vel
        # self.last_vel = current_vel

        current_time = rospy.get_time()
        sample_time = current_time - self.last_time
        self.last_time = current_time

        # throttle from pid
        throttle = self.throttle_controller.step(vel_error, sample_time)

        # brake
        brake = 0.

        if linear_vel == 0. and current_vel < MIN_SPEED:
            throttle = 0.
            brake = 700.
        elif throttle < .1 and vel_error < 0:
            throttle = 0.
            decel = max(vel_error, self.decel_limit)
            brake = abs(decel) * self.vehicle_mass * self.wheel_radius

        return throttle, brake, steering
