@echo off
python train.py --timesteps 5000000 --env VariableWindLevel0-v16 --note "learning rate linear schedule, init_value=1e-4"
python train.py --timesteps 5000000 --env VariableWindLevel1-v16 --note "learning rate linear schedule, init_value=1e-4"
python train.py --timesteps 5000000 --env VariableWindLevel2-v16 --note "learning rate linear schedule, init_value=1e-4"
python train.py --timesteps 3000000 --env VariableWindLevel0-v16 --psf --note "learning rate linear schedule, init_value=1e-4"
python train.py --timesteps 3000000 --env VariableWindLevel1-v16 --psf --note "learning rate linear schedule, init_value=1e-4"
python train.py --timesteps 3000000 --env VariableWindLevel2-v16 --psf --note "learning rate linear schedule, init_value=1e-4"
python train.py --timesteps 3000000 --env VariableWindLevel3-v16 --psf --note "learning rate linear schedule, init_value=1e-4"