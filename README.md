# NEURO(botics) simple job MANAGER

Isn't it fun to have a nice GPU in your computer and to experiment left and right? You just write some python scripts
and then launch them on your machine, wait, repeat. Life is simple and beautiful.

But then inevitably it happens. 

You want to launch more scripts, longer scripts, test different parameters... 
So you have to go beg the SLURM gods to assist you.
Evil bash scripts start popping up everywhere, requesting resources, launching jobs....
Wouldn't it be nice to just abstract that pain away and remain in python land?

## Prerequisites

- Python >=3.5 
- PyTorch >=1.6.0
- psutil
- pynvml

Most of these utilities are only needed if you want to run `gpu_check.py`.

To set up a compatible conda environment:
```shell
$  conda create -n <env-name> -c conda-forge -c pytorch python=3.9 psutil pynvml pytorch cudatoolkit=10.2
```
You may want to check [here](https://pytorch.org/get-started/locally/) to confirm the pytorch installation procedure is
correct for your GPU and NVIDIA driver.

## [launcher](launcher)
Allows you to turn
```python
python train.py --lr=0.01
```
into
```bash
#!/bin/bash
#SBATCH --time=2-00:00:00
#SBATCH --account=myproject
#SBATCH --partition=big-gpu
#SBATCH --gres=gpu:p100:1
#SBATCH --mem=8000

conda activate deep
python train.py --lr=0.01
```
It has the following syntax
```
launcher {--runs} CONFIG SCRIPT FLAGS
```
where support/device information needs to be provided by ```config.json``` with the following structure
```
{
  NAME:
    DEVICE 
    ENV
    RESOURCES
}
```
where NAME is used to select the specs, DEVICE is either "gpu" or "cpu" ENV specifies how to set up virtual environments if needed and RESOURCES specifies the option to pass to SLURM
e.g.
```json
{
  "remote-gpu": {
    "env": "conda activate deep",
    "device": "gpu",
    "resources": {
      "time": "2-00:00:00",
      "account": "lfrati",
      "partition": "big-gpu",
      "cpus-per-task": 1,
      "gres": "gpu:v100:1",
      "mem": "8000"
    }
  },
  "remote-cpu": {
    "env": "conda activate deep",
    "device": "cpu",
    "resources": {
      "time": "1-00:00:00",
      "partition": "bluemoon",
      "cpus-per-task": 1,
      "mem": "8000"
    }
  }
}
```
