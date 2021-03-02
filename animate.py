import numpy as np
import gym
from stable_baselines3 import PPO
from gym_rl_mpc.utils import model_params as params
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from matplotlib.animation import FuncAnimation
import pandas as pd
import argparse
import os

def animate(frame):
    plt.cla()
    height = params.L

    if args.data:
        # If reading from file:
        x_top = height*np.sin(data_angle[frame])
        y_top = -(height*np.cos(data_angle[frame]))
        action = data_input[0][frame]/params.max_input
    else:
        if args.agent:
            action, _states = agent.predict(env.observation, deterministic=True)
        else:
            if frame > 100:
                action = 1
            else:
                action = 0
            
        _, _, done, _ = env.step(action)
        if done:
            print("Environment done")
            raise SystemExit
        x_top = height*np.sin(env.pendulum.angle)
        y_top = height*np.cos(env.pendulum.angle)
        x_bottom = -params.L_P*np.sin(env.pendulum.angle)
        y_bottom = -params.L_P*np.cos(env.pendulum.angle)
        recorded_states.append(env.pendulum.state)
        recorded_inputs.append(env.pendulum.input)
        recorded_disturbance.append(env.pendulum.disturbance_force)

    x = [x_bottom, x_top]
    y = [y_bottom, y_top]
    ax_ani.set(xlim=(-0.7*height, 0.7*height), ylim=(-1.1*params.L_P, 1.1*height))
    ax_ani.set_xlabel('$X$')
    ax_ani.set_ylabel('$Y$')

    # Plot water line
    ax_ani.plot([-0.6*height, 0.6*height], [0, 0], linewidth=1, linestyle='--')

    # Plot pole
    ax_ani.plot(x, y, color='b', linewidth=2)
    # Plot line from neutral top position to current top position
    ax_ani.plot([0, x_top], [y_top, y_top], color='k', linewidth=1)
    # Plot arrow proportional to input force
    ax_ani.arrow(x = -params.L_P*np.sin(env.pendulum.angle), y = -params.L_P*np.cos(env.pendulum.angle), dx=-30*float(action), dy=0, head_width=2, head_length=2, length_includes_head=True)
    # Plot arrow proportional to disturbance force
    ax_ani.arrow(x = x_top, y = y_top, dx=30*(env.pendulum.disturbance_force/params.max_disturbance), dy=0, head_width=2, head_length=2, length_includes_head=True)


if __name__ == "__main__":
    fig_ani = plt.figure()
    ax_ani = fig_ani.add_subplot(111)

    recorded_states = []
    recorded_inputs = []
    recorded_disturbance = []

    parser = argparse.ArgumentParser()
    parser_group = parser.add_mutually_exclusive_group()
    parser_group.add_argument(
        '--data',
        help='Path to data .csv file.',
    )
    parser_group.add_argument(
        '--agent',
        help='Path to agent .zip file.',
    )
    parser.add_argument(
        '--time',
        type=int,
        default=50,
        help='Max simulation time (seconds).',
    )
    parser.add_argument(
        '--save_video',
        help='Save animation as mp4 file',
        action='store_true'
    )
    args = parser.parse_args()

    if args.data:
        # If file specified, read data from file and animate
        data = pd.read_csv(args.data)
        data_angle = data['theta']
        data_input = np.array([data['F']])
        data_reward = np.array(data['reward'])
        env_id = "PendulumStab-v0"
    else:
        done = False
        env = gym.make("PendulumStab-v0")
        env_id = env.unwrapped.spec.id
        env.reset()
        if args.agent:
            agent = PPO.load(args.agent)
        else:
            pass
            # env.pendulum.state = np.zeros(6)
        recorded_states.append(env.pendulum.state)
        recorded_inputs.append(env.pendulum.input)
        recorded_disturbance.append(env.pendulum.disturbance_force)

    ani = FuncAnimation(fig_ani, animate, interval=10, blit=False)

    plt.tight_layout()
    if args.save_video:
        agent_path_list = args.agent.split("\\")
        video_dir = os.path.join("logs", env_id, agent_path_list[-3], "videos")
        os.makedirs(video_dir, exist_ok=True)
        i = 0
        video_path = os.path.join(video_dir, agent_path_list[-1][0:-4] + f"_animation_{i}.mp4")
        while os.path.exists(video_path):
            i += 1
            video_path = os.path.join(video_dir, agent_path_list[-1][0:-4] + f"_animation_{i}.mp4")
        ani.save(video_path, dpi=150)
    plt.show()

    if not args.data:
        recorded_states = np.array(recorded_states)
        recorded_inputs = np.array(recorded_inputs)
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2)
        ax1.plot(recorded_states[:,0]*(180/np.pi), label='theta')
        ax1.set_ylabel('Degrees')
        ax1.set_title('Angle')
        ax1.legend()

        ax2.plot(recorded_states[:,1]*(180/np.pi), label='theta_dot')
        ax2.set_ylabel('Degrees/sec')
        ax2.set_title('Angluar velocity')
        ax2.legend()

        ax3.plot(recorded_inputs, label='F')
        ax3.set_ylabel('[N]')
        ax3.set_title('Input')
        ax3.legend()

        ax4.plot(recorded_disturbance, label='F_d')
        ax4.set_ylabel('[N]')
        ax4.set_title('Disturbance force')
        ax4.legend()

        plt.show()
