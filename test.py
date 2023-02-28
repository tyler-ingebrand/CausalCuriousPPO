import gym
import matplotlib.pyplot as plt
import torch
from causal_world.envs import CausalWorld
from causal_world.task_generators import generate_task
from pybullet_utils.util import set_global_seeds
from stable_baselines3.common.vec_env import SubprocVecEnv

from src.custom_task import MyOwnTask
from src.CausalCuriousPPO import *
from stable_baselines3.common.env_util import make_vec_env
from moviepy.editor import *
import os

# For Sophia, in the event I forget how to activate my virtual environment:  source /path/to/venv/bin/activate
if __name__ == '__main__':

    # parameters ##
    seed = 1
    number_envs = 8
    episodes_per_update = 8
    total_timesteps = 1000_000
    change_shape = True
    change_size = False
    change_mass = False
    separation_only = False # you have to go in and actually change the reward 
    ###############


    assert change_shape or change_size or change_mass
    torch.manual_seed(seed)

    # Get causal world environment. second half are cube, first half are sphere
    # things we can compare: weight heavy vs light, shape cube vs sphere, size big vs small? 
    def _make_env(rank):
        def _init():
            task = MyOwnTask(shape="Sphere" if rank < number_envs/2 and change_shape else "Cube",
                             size="Small" if rank < number_envs/2  and change_size else "Big",
                             mass="Light" if rank < number_envs/2 and change_mass else "Heavy")
            env = CausalWorld(task=task,
                              enable_visualization=False,
                              seed=seed + rank,
                              max_episode_length=249,
                              skip_frame=10,
                              )
            return env

        set_global_seeds(seed)
        return _init

    env = SubprocVecEnv([_make_env(i) for i in range(number_envs)])


    # train
    model = CausalCuriousPPO("MlpPolicy", env,
                             episode_length=env.get_attr("_max_episode_length", [0])[0] + 1, # this env returns the index of last step, we want total number of steps
                             episodes_per_update=episodes_per_update, verbose=1)

    model.learn(total_timesteps=total_timesteps)




    # plot result of learning
    exp_dir = "{}{}{}{}seed_{}_steps_{}".format("separation_only_" if separation_only == True else "", "change_shape_" if change_shape else "", "change_size_" if change_size else "", "change_mass_" if change_mass else "", seed, total_timesteps)
    os.makedirs("results/{}".format(exp_dir), exist_ok=True)
    plt.plot(model.timesteps, model.mean_distance_my_cluster, label="Cluster Size")
    plt.plot(model.timesteps, model.mean_distance_other_cluster, label="Cluster Separation")
    plt.xlabel("Env Interactions")
    plt.ylabel("Euclidean Distance")
    plt.title("Cluster Properties During Training")
    plt.legend()
    plt.savefig("results/{}/cluster_distances.png".format(exp_dir))

    # show episode, save
    seconds_per_frame = 0.1
    base_file_name = "experiment"
    for episode in range(10):
        images = []
        done = False
        obs = env.reset()
        while not done:
            action, _states = model.predict(obs)
            obs, rewards, dones, info = env.step(action)
            frame = env.render(mode='rgb_array')
            images.append(ImageClip(frame).set_duration(seconds_per_frame))
            done = dones.any()
        video = concatenate(images, method="compose")
        video.write_videofile("results/{}/{}_episode_{}.mp4".format( exp_dir, base_file_name, episode), fps=24)
