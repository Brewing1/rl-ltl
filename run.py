import time
import numpy as np
import gym
from envs.frozen_lake import FrozenLakeRMEnv
# from stable_baselines3 import A2C

from agents.qlearning import QLearning
from agents.qtlearning import QTLearning
import solver
from reward_machines.rm_environment import RewardMachineEnv, RewardMachineWrapper
import utils
import plotting


def run_always_down():
    env = FrozenLake(map_name="5x5", slip=0.5)
    go_down = 0
    n_rollout_steps = 20
    for step in range(n_rollout_steps):
        obs, reward, done, _ = env.step(go_down)
        print(f"Step: {step}. Obs: {obs}. Reward: {reward}. Done: {done}")
        env.render()
        if done:
            print("Rollout finished.")
            break

# def run_a2c():
#     env = FrozenLake(map_name="5x5", slip=0.5)
#     # With gamma<1, agent learns to only go DownRight in s3
#     model = A2C('MlpPolicy', env, gamma=0.99, verbose=1)
#     model.learn(total_timesteps=10000)
#     rollout_model(env, model)

def rollout_model(env, model, num_eps=1, horizon=20):
    for ep in range(num_eps):
        s = tuple(env.reset())
        env.render()
        for t in range(horizon, 0, -1):
            if horizon:
                # If no q-values for this state, add them
                if (t, s) not in model.q:
                    model.q[(t, s)] = [0] * model.env.action_space.n
                a, _ = model.predict((t, s), deterministic=True)
            else:
                # If no q-values for this state, add them
                if s not in model.q:
                    model.q[s] = [0] * model.env.action_space.n
                a, _ = model.predict(s, deterministic=True)
            new_s, _, done, _ = env.step(a)
            env.render()
            s = tuple(new_s)

            if done:
                print("Finished ep")
                break

def run_value_iteration(finite=False):
    rm_files = ["./envs/rm_t1_frozen_lake.txt"]
    multi_objective_weights = None
    map_name = "5x5"
    obj_name = "objects_t1"
    options = {
        "seed": seed,
        "lr": 0.5,
        "gamma": 1,
        "epsilon": 0.2,
        "n_episodes": 1000,
        "n_rollout_steps": 100,
        "use_crm": True,
        "use_rs": False,
        "horizon": 1,
        "all_acts": True,
    }

    if multi_objective_weights:
        # Create a new rm_file combining rm_files with multi_objective_weights
        rm_files = [utils.scalarize_rewards(rm_files, multi_objective_weights)]

    rm_env = FrozenLakeRMEnv(
        rm_files, map_name=map_name, obj_name=obj_name, slip=0.5, seed=options["seed"],
        all_acts=options["all_acts"]
    )
    rm_env = RewardMachineWrapper(rm_env, options["use_crm"], options["use_rs"], options["gamma"], 1)
    # Only one reward machine for these experiments
    rm = rm_env.reward_machines[0]

    if finite:
        optim_vals, n_iter, optim_pol = solver.value_iteration_finite(
            rm_env, rm, options["gamma"], horizon=options["horizon"]
        )
        v, pol = utils.display_grid_optimals(
            optim_vals, optim_pol, rm_env.env.desc.shape, len(rm.get_states()), options["horizon"]
        )
    else:
        optim_vals, n_iter, optim_pol = solver.value_iteration(rm_env, rm, options["gamma"])
        v, pol = utils.display_grid_optimals(
            optim_vals, optim_pol, rm_env.env.desc.shape, len(rm.get_states()), horizon=None
        )
    print(v)
    for i in range(pol.shape[0]):
        print(i, pol[i], "\n")
    # print(pol)
    print(n_iter)


def run_q_algo(rm_files, map_name, obj_name, options, out_dir, finite=False):
    rm_env = FrozenLakeRMEnv(
        rm_files, map_name=map_name, obj_name=obj_name, slip=0.5, seed=options["seed"],
        all_acts=options["all_acts"]
    )
    rm_env = RewardMachineWrapper(rm_env, options["use_crm"], options["use_rs"], options["gamma"], 1)

    if finite:
        ql = QTLearning(rm_env, **options)
    else:
        ql = QLearning(rm_env, **options)
    return ql.learn()

def infinite_horizon_experiments(task_num):
    rm_files = [f"./envs/rm_t{task_num}_frozen_lake.txt"]
    map_name = "5x5"
    obj_name = f"objects_t{task_num}"
    out_dir = "results"

    policy_info = {}
    for use_crm in [False, True]:
        alg_name = "CRM" if use_crm else "qlearning"
        options = {
            "seed": seed,
            "lr": 0.1,
            "gamma": 1,
            "epsilon": 0.2,
            "n_episodes": 1000,
            # Only gets used in QLearning
            "n_rollout_steps": 1000,
            # Only gets used in QTlearning
            "horizon": 10,
            "use_crm": use_crm,
            "use_rs": False,
            "print_freq": 10000,
            "eval_freq": 30,
            "num_eval_eps": 30,
            "all_acts": True,
        }

        policy_info[alg_name] = run_q_algo(
            rm_files, map_name, obj_name, options, out_dir, finite=False
        )

    plotting.plot_rewards(policy_info, "experiences", out_dir, f"Task{task_num}")
    plotting.plot_rewards(policy_info, "updates", out_dir, f"Task{task_num}")
    print(policy_info)
    # return
    # qs = {}
    # for k in ql.q:
    #     qs[f"{k}"] = ql.q[k]
    # import json
    # with open(f"{out_dir}/qs.json", "w") as f:
    #     json.dump(qs, f, indent=4)

    # rollout_model(rm_env, ql, num_eps=1, horizon=options["horizon"])


if __name__ == "__main__":
    start = time.time()
    seed = 35
    # run_value_iteration(finite=True)
    # run_q_algo(finite=False)
    infinite_horizon_experiments(3)
    # run_always_down()
    # run_a2c()
    print("Time taken:", time.time() - start)
