import numpy as np

g = 9.81                            # Gravitational acceleration

# Platform parameters
L = 144.495
L_P = 50
L_COM = 6                          # Meters below rotation point
m = 1.7838E+07 + 190000 + 507275   # Platform mass + Hub mass + Nacelle mass 
k = 4.5e4
zeta = 1
c = 2*zeta*np.sqrt(m*k)
J = 2*1.2507E+10 + m*(L_COM)**2     # 2*J_COM + m*d^2

# Rotor parameters
B = 0.94                            # Tip loss parameter (table 5.1 Pedersen)
lambda_star = 7.5                   # (table 5.1 Pedersen)
C_P_star = 0.48                     # (table 5.1 Pedersen)
C_F = 0.0145                        # (table 5.1 Pedersen)
rho = 1.225                         # Air density (table 5.1 Pedersen)
R = 63                              # Blade length
A = np.pi*R**2
R_p = B*R
A_p = np.pi*R_p**2
k_t = (2*rho*A_p*R)/(3*lambda_star) # k in Force/Torque equations
l_t = (2/3)*R_p                     # l in Force/Torque equations
b_d = 0.5*rho*A*(B**2*(16/27)-C_P_star)*(R/lambda_star)**3  # b_d in Force/Torque equations
d_t = 0.5*rho*A*C_F                 # d in Force/Torque equations
J_t = 4e7                           # (table 5.1 Pedersen)

max_thrust_force = 1e6              # maximum force input [N]
blade_pitch_max = 40*(np.pi/180)    # maximum blade pitch angle (-+)
max_wind_force = 1e5
tau_blade_pitch = 20                # Blade pitch time constant
tau_thr = 50                        # Thrust force time constant