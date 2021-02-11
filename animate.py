import numpy as np
import gym
from stable_baselines3 import PPO
from gym_turbine.objects import turbine
from gym_turbine.utils import state_space as ss
import matplotlib.pyplot as plt

from mpl_toolkits.mplot3d import Axes3D
from matplotlib.patches import FancyArrowPatch
from mpl_toolkits.mplot3d.proj3d import proj_transform

from matplotlib.animation import FuncAnimation
import pandas as pd
import argparse

class Arrow3D(FancyArrowPatch):
    def __init__(self, x, y, z, dx, dy, dz, *args, **kwargs):
        super().__init__((0, 0), (0, 0), *args, **kwargs)
        self._xyz = (x, y, z)
        self._dxdydz = (dx, dy, dz)

    def draw(self, renderer):
        x1, y1, z1 = self._xyz
        dx, dy, dz = self._dxdydz
        x2, y2, z2 = (x1+dx, y1+dy, z1+dz)

        xs, ys, zs = proj_transform((x1, x2), (y1, y2), (z1, z2), renderer.M)
        self.set_positions((xs[0], ys[0]), (xs[1], ys[1]))
        super().draw(renderer)

def _arrow3D(ax, x, y, z, dx, dy, dz, *args, **kwargs):
    '''Add an 3d arrow to an `Axes3D` instance.'''

    arrow = Arrow3D(x, y, z, dx, dy, dz, *args, **kwargs)
    ax.add_artist(arrow)


def plot_states(turbine, sim_time):
    step_size = 0.01
    N = int(sim_time/step_size)
    pitch = np.array([])
    roll = np.array([])
    dva_input = []

    for i in range(N):
        wind_dir = 0
        action = np.array([0, 0, 0, 0])
        turbine.step(action, wind_dir)
        pitch = np.append(pitch, turbine.pitch)
        roll = np.append(roll, turbine.roll)
        dva_input.append(turbine.input)

    dva_input = np.asarray(dva_input)

    fig, (ax1, ax2) = plt.subplots(nrows=2)
    time = np.linspace(0, N*step_size, pitch.size)
    ax1.plot(time, pitch*(180/np.pi), label='Pitch')
    ax1.plot(time, roll*(180/np.pi), label='Roll')
    ax2.plot(time, dva_input[:, 0], label='DVA#1')
    ax2.plot(time, dva_input[:, 1], label='DVA#2')
    ax2.plot(time, dva_input[:, 2], label='DVA#3')
    ax2.plot(time, dva_input[:, 3], label='DVA#4')
    plt.legend()
    plt.tight_layout()
    plt.show()

def animate(frame):
    plt.cla()
    height = 90
    wind_dir = 0
    spoke_length = 27

    if args.data:
        # If reading from file:
        x_surface = data_position[0][frame]
        y_surface = data_position[1][frame]
        z_surface = data_position[2][frame]
        x_top = x_surface + height*np.sin(data_pitch[frame])*np.cos(data_roll[frame])
        y_top = -(y_surface + height*np.sin(data_roll[frame])*np.cos(data_pitch[frame]))
        z_top = z_surface + height*np.cos(data_pitch[frame])
        action = np.array([data_input[0][frame]/ss.max_input, data_input[1][frame]/ss.max_input, data_input[2][frame]/ss.max_input, data_input[3][frame]/ss.max_input])
    elif args.agent:
        action, _states = agent.predict(env.observation, deterministic=True)
        _, _, done, _ = env.step(action)
        # if done:
        #     print("Environment done")
        #     raise SystemExit
        x_surface = env.turbine.position[0]
        y_surface = env.turbine.position[1]
        z_surface = env.turbine.position[2]
        x_top = x_surface + height*np.sin(env.turbine.pitch)*np.cos(env.turbine.roll)
        y_top = -(y_surface + height*np.sin(env.turbine.roll)*np.cos(env.turbine.pitch))
        z_top = z_surface + height*np.cos(env.turbine.pitch)
        recorded_states.append(env.turbine.state[0:11])
    else:
        ## Simulate turbine step by step ##
        if frame in range(50, 60):
            action = np.array([0.5, 0, 0, 0])
        else:
            action = np.array([0, 0, 0, 0])
        turbine.step(action, wind_dir)
        x_surface = turbine.position[0]
        y_surface = turbine.position[1]
        z_surface = turbine.position[2]
        x_top = x_surface + height*np.sin(turbine.pitch)*np.cos(turbine.roll)
        y_top = -(y_surface + height*np.sin(turbine.roll)*np.cos(turbine.pitch))
        z_top = z_surface + height*np.cos(turbine.pitch)
        recorded_states.append(turbine.state[0:11])


    x = [x_surface, x_top]
    y = [y_surface, y_top]
    z = [z_surface, z_top]
    x_base = [-0.5*(x_top-x_surface) + x_surface, x_surface]
    y_base = [-0.5*(y_top-y_surface) + y_surface, y_surface]
    z_base = [-0.5*(z_top-z_surface) + z_surface, z_surface]
    # ax_ani.set_aspect('equal', adjustable='datalim')
    ax_ani.set(xlim=(-0.6*height, 0.6*height), ylim=(-0.6*height, 0.6*height), zlim=(-0.7*height, 1.1*height))
    ax_ani.set_xlabel('$X$')
    ax_ani.set_ylabel('$Y$')
    ax_ani.set_zlabel('$Z$')

    # Plot surface (water)
    surface_X = np.arange(-0.6*height, 0.6*height+1, height)
    surface_Y = np.arange(-0.6*height, 0.6*height+1, height)
    surface_X, surface_Y = np.meshgrid(surface_X, surface_Y)
    surface_Z = 0*surface_X
    ax_ani.plot_surface(surface_X, surface_Y, surface_Z, alpha=0.1, linewidth=0, antialiased=False)

    # Plot pole
    ax_ani.plot(x, y, z, color='b', linewidth=2)
    # Plot base
    ax_ani.plot(x_base, y_base, z_base, color='r', linewidth=8)
    # Plot line from neutral top position to current top position
    ax_ani.plot([0, x_top], [0, y_top], [height, z_top], color='k', linewidth=1)
    # Plot line from neutral base position to current base position
    ax_ani.plot([0, x_surface], [0, y_surface], [0, z_surface], color='k', linewidth=1)

    # Plot arrow proportional to DVA_1 input
    ax_ani.arrow3D(x = x_surface + spoke_length, y = y_surface, z = z_surface, dx=0, dy=0, dz=100*action[0], mutation_scale=10, arrowstyle="-|>")
    # Plot arrow proportional to DVA_2 input
    ax_ani.arrow3D(x = x_surface, y = y_surface + spoke_length, z = z_surface, dx=0, dy=0, dz=100*action[1], mutation_scale=10, arrowstyle="-|>")
    # Plot arrow proportional to DVA_3 input
    ax_ani.arrow3D(x = x_surface - spoke_length, y = y_surface, z = z_surface, dx=0, dy=0, dz=100*action[2], mutation_scale=10, arrowstyle="-|>")
    # Plot arrow proportional to DVA_4 input
    ax_ani.arrow3D(x = x_surface, y = y_surface - spoke_length, z = z_surface, dx=0, dy=0, dz=100*action[3], mutation_scale=10, arrowstyle="-|>")


if __name__ == "__main__":
    setattr(Axes3D, 'arrow3D', _arrow3D)
    fig_ani = plt.figure()
    ax_ani = fig_ani.add_subplot(111, projection='3d')
    ax_ani.view_init(elev=18, azim=45)

    state_labels = np.array([r"x_sg", r"x_sw", r"x_hv", r"theta_r", r"theta_p", r"x_tf", r"x_ts", r"x_1", r"x_2", r"x_3", r"x_4"])
    recorded_states = []

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--data',
        help='Path to data .csv file.',
    )
    parser.add_argument(
        '--agent',
        help='Path to agent .pkl file or model .zip file.',
    )
    parser.add_argument(
        '--time',
        type=int,
        default=50,
        help='Max simulation time (seconds).',
    )
    args = parser.parse_args()

    if args.data:
        # If file specified, read data from file and animate
        data = pd.read_csv(args.data)
        data_position = np.array([data['x_sg'], data['x_sw'], data['x_hv']])
        data_roll = data['theta_r']
        data_pitch = data['theta_p']
        data_input = np.array([data['DVA_1'], data['DVA_2'], data['DVA_3'], data['DVA_4']])
        data_reward = np.array(data['reward'])
    elif args.agent:
        done = False
        agent_path = args.agent
        env = gym.make("TurbineStab-v0")
        agent = PPO.load(agent_path)
        env.reset()
    else:
        # If not file specified, simulate turbine step by step and animate
        step_size = 0.01
        init_roll = 0
        init_pitch = 0
        turbine = turbine.Turbine(np.array([init_roll, init_pitch]), step_size)

    ani = FuncAnimation(fig_ani, animate, interval=10, blit=False)

    plt.tight_layout()
    plt.show()
    if not (args.data or args.agent):
        fig, (ax1, ax2) = plt.subplots(1, 2)
        rec_data = pd.DataFrame(recorded_states, columns=state_labels)
        ax1.plot(rec_data['x_tf'], label='Fore-Aft')
        ax1.plot(rec_data['x_ts'], label='Side-Side')
        ax1.set_ylabel('Meters')
        ax1.set_title('Tower top displacements')
        ax1.legend()

        ax2.plot(rec_data['theta_p']*(180/np.pi), label='Pitch')
        ax2.plot(rec_data['theta_r']*(180/np.pi), label='Roll')
        ax2.set_ylabel('Degrees')
        ax2.set_title('Angles')
        ax2.legend()
        plt.show()
