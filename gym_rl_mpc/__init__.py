from gym.envs.registration import register

from gym_rl_mpc.utils.model_params import RAD2DEG, RAD2RPM, RPM2RAD, DEG2RAD

DEFAULT_CONFIG = {
    "use_psf": False,
    "step_size": 0.1,
    "max_episode_time": 300,                    # Max time for episode [seconds]
    "crash_reward": -1000,
    "crash_angle_condition": 10*DEG2RAD,
    "crash_omega_max": 10*RPM2RAD,
    "crash_omega_min": 3*RPM2RAD,
    "max_wind_speed": 25,
    "min_wind_speed": 5,
    "gamma_theta": 0.12,                        # Exponential coefficient for platform_angle angle reward
    "gamma_omega": 0.285,                        # Exponential coefficient for omega reward
    "gamma_power": 0.1,                        # Exponential coefficient for power reward
    "gamma_theta_dot": 3,                      # Coefficient for angular rate penalty
    "gamma_omega_dot": 4,
    "gamma_psf": 5,
    "gamma_input": 0,                        # Coefficient for control input penalty
    "reward_survival": 1,
}

VARIABLE_WIND_CONFIG = DEFAULT_CONFIG.copy()
VARIABLE_WIND_CONFIG["wind_period"] = 60
VARIABLE_WIND_CONFIG.pop('max_wind_speed')
VARIABLE_WIND_CONFIG.pop('min_wind_speed')

CRAZY_ENV_CONFIG = VARIABLE_WIND_CONFIG.copy()
CRAZY_ENV_CONFIG["action_space_increase"] = 3 # Violation will happen with N/N+1 and with size N-1 outside

SCENARIOS = {
    'ConstantWind-v16': {   
        'entry_point': 'gym_rl_mpc.envs:ConstantWind',
        'config': DEFAULT_CONFIG
    },
    'VariableWindLevel0-v16': {
        'entry_point': 'gym_rl_mpc.envs:VariableWindLevel0',
        'config': VARIABLE_WIND_CONFIG
    },
    'VariableWindLevel1-v16': {
        'entry_point': 'gym_rl_mpc.envs:VariableWindLevel1',
        'config': VARIABLE_WIND_CONFIG
    },
    'VariableWindLevel2-v16': {
        'entry_point': 'gym_rl_mpc.envs:VariableWindLevel2',
        'config': VARIABLE_WIND_CONFIG
    },
    'VariableWindLevel3-v16': {
        'entry_point': 'gym_rl_mpc.envs:VariableWindLevel3',
        'config': VARIABLE_WIND_CONFIG
    },
    'VariableWindLevel4-v16': {
        'entry_point': 'gym_rl_mpc.envs:VariableWindLevel4',
        'config': VARIABLE_WIND_CONFIG
    },
    'VariableWindLevel5-v16': {
        'entry_point': 'gym_rl_mpc.envs:VariableWindLevel5',
        'config': VARIABLE_WIND_CONFIG
    },
    'VariableWindLevel6-v16': {
        'entry_point': 'gym_rl_mpc.envs:VariableWindLevel6',
        'config': VARIABLE_WIND_CONFIG
    },
    'CrazyAgent-v16': {
        'entry_point': 'gym_rl_mpc.envs:CrazyAgent',
        'config': CRAZY_ENV_CONFIG
    }
}

for scenario in SCENARIOS:
    register(
        id=scenario,
        entry_point=SCENARIOS[scenario]['entry_point'],
        kwargs={'env_config': SCENARIOS[scenario]['config']}
    )